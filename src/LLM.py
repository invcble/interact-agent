from flask import Flask, request, jsonify
from openai import OpenAI
import json
import os
from browserAPI import BrowserAPI  # Assuming browserAPI.py contains the updated BrowserAPI class
from dotenv import load_dotenv
import threading
from typing import Dict, Any, Optional, List

load_dotenv()

app = Flask(__name__)

class BrowserLLM:
    def __init__(self, api_key=None, driver_path=None):
        """Initialize the BrowserLLM with OpenAI API key and optional ChromeDriver path."""
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key must be provided or set as OPENAI_API_KEY environment variable")

        self.client = OpenAI(api_key=self.api_key)
        self.browser = BrowserAPI(driver_path=driver_path)
        self.model = "gpt-4o"
        self.temperature = 0
        self.messages = []
        self.browser_started = False
        self.MAX_TURNS = 10  # Default number of interactions before stopping

        # --- System Prompt ---
        self.messages.append({
            "role": "system",
            "content": (
                "You are a browser automation assistant. Your job is to control a browser "
                "based on user instructions by deciding the next single action to take. "
                "You have the following tools available:\n\n"
                "- `start_browser`: Launch a new browser window.\n"
                "- `go_to_website`: Navigate to a specific URL.\n"
                "- `click_at_coordinates`: Click at specific coordinates (x, y) on the page.\n"
                "- `input_text_at_coordinates`: Input text at specific coordinates (x, y) into an input field.\n"
                "- `scroll_page`: Scroll the page by a specified amount of pixels.\n"
                "- `refresh_content`: Get the current page content without performing any other action.\n"
                "- `close_browser`: Close the browser.\n\n"
                "Guidelines:\n"
                "1. Always start by launching the browser if it's not already running (`start_browser`).\n"
                "2. After navigating, clicking, typing, or scrolling, you will receive feedback including the status of the action and the **updated page content** (URL, title, visible interactive elements with their coordinates and highlight index like '[index] <tag...> text (at x:..., y:...)').\n"
                "3. When the user asks to click or type on something (e.g., 'click the login button', 'type 'hello' into the search bar'), examine the **most recent page content** provided in the previous step's result to find the target element and its coordinates (x, y).\n"
                "4. Use the coordinates from the page content to call `click_at_coordinates` or `input_text_at_coordinates`.\n"
                "5. If the target element is not visible, consider using `scroll_page` (usually scrolling down, e.g., y=500 or y=1000) and then check the new page content in the result.\n"
                "6. Only perform **one action** at a time. Decide the next single step based on the user request and the current page state.\n"
                "7. Explain clearly which action you are taking and why, referencing the element or coordinates if applicable.\n"
                "8. If the browser isn't started, your first action must be `start_browser`.\n"
                "9. Your responses should indicate the action you are taking, but the actual execution result will come in the next turn as function output.\n"
                "10. **CAPTCHA Handling:** If you detect any form of CAPTCHA (e.g., elements with text like 'Try different image', 'captchacharacters', 'I'm not a robot') in the page content, **STOP** immediately. Do not attempt to interact with the CAPTCHA. Inform the user you've encountered a CAPTCHA and ask them to solve it manually and let you know when they are done.\n"
                "11. **Resuming After User Intervention:** After you have stopped for user intervention (like solving a CAPTCHA) and the user confirms they have completed the required action (e.g., 'done', 'go ahead', 'ok continue'), your **very next step must be** to call the `refresh_content` tool. This ensures you have the latest page state before proceeding with the original task.\n"
                "12. **Verification Before Final Actions:** Do **not** mark your task as complete or indicate success until you have **verified** that the desired outcome or change has occurred. Always use `refresh_content` to confirm the state of the page before declaring that a goal has been achieved or the task is done.\n"
                "13. **Pop-Up / Modal Interaction Handling:** If an action (e.g., Add to cart, Confirm, Continue) appears to be within a modal or pop-up (identified by elements like `a-popover-start`, close buttons, or modal-like containers), assume the interaction must be confirmed **within the pop-up**. After clicking the action button inside the modal, always follow up with `refresh_content` to verify the modal has closed **and** the action was successfully applied (e.g., item added to cart). Do **not** mark the task as complete until the modal has closed and the result is confirmed in the updated page content."
                "14. **Login Authentication:** When attempting to log in, always use **password-based login** only. Do **not** proceed with OTP, biometric, or alternative login methods. Select password and option, and THEN INPUT PASSWORD in the PASSWORD INPUT FIELD."
                "15. **Don’t Loop on the Same Element – Move Forward:** If you’ve already interacted with an element (e.g., `password`), don’t repeat it—check the element list and proceed to the next required step (e.g., `pd-input`). Repeating an action usually means you’ve missed another needed input or interaction."
            )
        })

        # --- Tool Definitions ---
        self.tools = [
            {
                "type": "function",
                "name": "start_browser",
                "description": "Launch a new Chrome browser window. Should be the first step if the browser isn't open.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "type": "function",
                "name": "go_to_website",
                "description": "Navigate the browser to a specific URL.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "The full URL to navigate to (including http:// or https://)"
                        }
                    },
                    "required": ["url"]
                }
            },
            {
                "type": "function",
                "name": "click_at_coordinates",
                "description": "Click at specific coordinates (x, y) on the page. Find coordinates from the latest page content.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "x": {
                            "type": "number",
                            "description": "X coordinate (horizontal position from left) obtained from page content"
                        },
                        "y": {
                            "type": "number",
                            "description": "Y coordinate (vertical position from top) obtained from page content"
                        }
                    },
                    "required": ["x", "y"]
                }
            },
            {
                "type": "function",
                "name": "input_text_at_coordinates",
                "description": "Input text into an element at specific coordinates (x, y) on the page. Find coordinates from the latest page content.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "x": {
                            "type": "number",
                            "description": "X coordinate (horizontal position from left) of the input element, obtained from page content"
                        },
                        "y": {
                            "type": "number",
                            "description": "Y coordinate (vertical position from top) of the input element, obtained from page content"
                        },
                        "text": {
                            "type": "string",
                            "description": "The text to input"
                        }
                    },
                    "required": ["x", "y", "text"]
                }
            },
            {
                "type": "function",
                "name": "scroll_page",
                "description": "Scroll the page vertically or horizontally by a specified number of pixels.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "x": {
                            "type": "number",
                            "description": "Horizontal scroll amount in pixels (positive scrolls right, negative scrolls left). Default is 0.",
                            "default": 0
                        },
                        "y": {
                            "type": "number",
                            "description": "Vertical scroll amount in pixels (positive scrolls down, negative scrolls up). Default is 500 (scroll down).",
                            "default": 500
                        }
                    },
                    "required": []
                }
            },
            {
                "type": "function",
                "name": "refresh_content",
                "description": "Retrieve the current visible interactive elements and page state without performing any navigation or interaction. Use this after user intervention (like solving a CAPTCHA) before resuming.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "type": "function",
                "name": "close_browser",
                "description": "Close the browser window and end the session.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        ]

    def clear_old_page_content(self):
        """Clear old page content to reduce token usage, keeping only the two most recent ones."""
        page_content_indices = []
        
        # First, identify all messages containing page content
        for index, msg in enumerate(self.messages):
            if (isinstance(msg, dict) and 
                msg.get("type") == "function_call_output" and 
                isinstance(msg.get("output"), str) and 
                "<page_content>" in msg["output"] and 
                "</page_content>" in msg["output"]):
                page_content_indices.append(index)
        
        # If there are more than two such messages, clear all but the last two
        if len(page_content_indices) > 2:
            # Get indices of messages to clear (all except the last two)
            indices_to_clear = page_content_indices[:-2]
            
            # Clear the content in those messages
            for index in indices_to_clear:
                # Replace only the content between <page_content> tags
                original_output = self.messages[index]["output"]
                start_tag_pos = original_output.find("<page_content>")
                end_tag_pos = original_output.find("</page_content>")
                
                if start_tag_pos != -1 and end_tag_pos != -1:
                    # Preserve the tags but replace content between them
                    new_output = (
                        original_output[:start_tag_pos + len("<page_content>")] + 
                        "Cleared to reduce tokens" + 
                        original_output[end_tag_pos:]
                    )
                    self.messages[index]["output"] = new_output
            
            print(f"INFO: Cleared content from {len(indices_to_clear)} older page_content messages.")

    def call_function(self, name, args):
        """Execute the appropriate browser function based on the name and arguments."""
        try:
            # Branch based on function name
            if name == "start_browser":
                result = self.browser.start_browser()
                if result.get("status") == "success":
                    self.browser_started = True
                    
            elif not self.browser_started:
                return {"status": "error", "error_message": "Browser not started. Please call start_browser first."}
                
            elif name == "go_to_website":
                url = args.get("url")
                if not url or not (url.startswith("http://") or url.startswith("https://")):
                    return {"status": "error", "error_message": "Invalid or missing URL. Please provide a full URL starting with http:// or https://."}
                result = self.browser.go_to_website(url)
                
            elif name == "click_at_coordinates":
                x, y = args.get("x"), args.get("y")
                if x is None or y is None:
                    return {"status": "error", "error_message": "Missing x or y coordinate for click."}
                result = self.browser.click_at_coordinates(float(x), float(y))
                
            elif name == "input_text_at_coordinates":
                x, y = args.get("x"), args.get("y")
                text = args.get("text", "")
                if x is None or y is None:
                    return {"status": "error", "error_message": "Missing x or y coordinate for input."}
                result = self.browser.input_text_at_coordinates(float(x), float(y), text)
                
            elif name == "scroll_page":
                x, y = args.get("x", 0), args.get("y", 500)
                result = self.browser.scroll_page(x=int(x), y=int(y))
                
            elif name == "refresh_content":
                result = self.browser.refresh_content()
                
            elif name == "close_browser":
                if not self.browser_started:
                    return {"status": "success", "message": "Browser already closed.", "content": "No content as browser closed"}
                result = self.browser.close_browser()
                if result.get("status") == "success":
                    self.browser_started = False
                    
            else:
                result = {"status": "error", "error_message": f"Unknown function: {name}"}

            return result

        except Exception as e:
            print(f"Error calling function {name} with args {args}: {e}")
            return {"status": "error", "error_message": f"Internal error executing {name}: {str(e)}"}

    def set_max_turns(self, max_turns: int):
        """Set maximum number of turns for interaction."""
        if max_turns < 1:
            raise ValueError("max_turns must be at least 1")
        self.MAX_TURNS = max_turns
        return {"status": "success", "message": f"MAX_TURNS set to {max_turns}"}

    def process_user_input(self, user_input: str) -> Dict:
        """Process user input, let the LLM decide the next action, execute it, and return detailed results."""
        self.messages.append({"role": "user", "content": user_input})
        final_response_text = None
        responses_history = []
        actions_history = []

        for turn in range(self.MAX_TURNS):
            print(f"\n--- Turn {turn + 1}/{self.MAX_TURNS} ---")
            
            # Clear old page content before each LLM call to reduce tokens
            self.clear_old_page_content()
            
            try:
                # Call the LLM with current messages
                response = self.client.responses.create(
                    model=self.model,
                    input=self.messages,
                    temperature=self.temperature,
                    tools=self.tools,
                    tool_choice="auto"
                )
            except Exception as e:
                error_msg = f"Error calling OpenAI API: {e}"
                print(error_msg)
                self.messages.append({"role": "assistant", "content": error_msg})
                self._dump_messages()
                return {
                    "status": "error", 
                    "message": error_msg,
                    "final_response": error_msg,
                    "history": responses_history,
                    "actions": actions_history
                }

            # Extract text content and tool calls from response
            tool_calls = []
            assistant_message_content = ""

            if hasattr(response, 'output') and isinstance(response.output, list):
                for output_part in response.output:
                    if hasattr(output_part, 'type'):
                        if output_part.type == "function_call":
                            tool_calls.append(output_part)
                        elif output_part.type == "text":
                            assistant_message_content += getattr(output_part, 'text', '')
                    elif isinstance(output_part, str):
                        assistant_message_content += output_part

                # Add assistant explanation message if present
                if assistant_message_content:
                    last_msg = self.messages[-1] if self.messages else {}
                    if not (last_msg.get("role") == "assistant" and last_msg.get("content") == assistant_message_content):
                        self.messages.append({"role": "assistant", "content": assistant_message_content})
                        print(f"LLM thought/explanation: {assistant_message_content}")
                        responses_history.append({
                            "turn": turn + 1, 
                            "type": "thinking", 
                            "content": assistant_message_content
                        })

            # Handle tool calls if any
            if tool_calls:
                # Add tool call intentions to messages
                self.messages.extend(tool_calls)

                for tool_call in tool_calls:
                    function_name = tool_call.name
                    try:
                        function_args = json.loads(tool_call.arguments) if tool_call.arguments else {}
                    except (json.JSONDecodeError, TypeError) as e:
                        print(f"Error decoding arguments for {function_name}: {tool_call.arguments}. Error: {e}")
                        function_result = {"status": "error", "error_message": f"Invalid arguments format from LLM: {tool_call.arguments}"}
                        result_content = f"Error: Invalid arguments format from LLM for {function_name}."
                    else:
                        print(f"LLM requests call: {function_name}({function_args})")
                        # Record the action being taken
                        actions_history.append({
                            "turn": turn + 1,
                            "function": function_name,
                            "arguments": function_args
                        })
                        
                        function_result = self.call_function(function_name, function_args)
                        print(f"Function result: {function_result}")

                        # Format the function result for the LLM
                        if function_result.get("status") == "success":
                            try:
                                page_content_str = json.dumps(function_result.get("content", "No content available"))
                            except TypeError:
                                page_content_str = str(function_result.get("content", "No content available"))
                            result_content = f"Status: Success. Message: {function_result.get('message', 'Action completed.')}\n<page_content>\n{page_content_str}\n</page_content>"
                        else:
                            result_content = f"Status: Error. Error Message: {function_result.get('error_message', 'Unknown error occurred.')}"

                    # Add function result to messages
                    function_output = {
                        "type": "function_call_output",
                        "call_id": tool_call.call_id,
                        "output": result_content
                    }
                    self.messages.append(function_output)
                    
                    # Record the result in history
                    responses_history.append({
                        "turn": turn + 1,
                        "type": "function_result",
                        "function": function_name,
                        "status": function_result.get("status", "unknown"),
                        "message": function_result.get("message", function_result.get("error_message", "No message"))
                    })
            else:
                # No tool calls, just a text response
                final_response_text = getattr(response, 'output_text', assistant_message_content)
                
                # Add final response to messages if not empty and not duplicate
                last_msg = self.messages[-1] if self.messages else {}
                if final_response_text and not (last_msg.get("role") == "assistant" and last_msg.get("content") == final_response_text):
                    self.messages.append({"role": "assistant", "content": final_response_text})
                
                if final_response_text:
                    print(f"LLM final response: {final_response_text}")
                    responses_history.append({
                        "turn": turn + 1,
                        "type": "final_response",
                        "content": final_response_text
                    })
                    self._dump_messages()
                    return {
                        "status": "success",
                        "message": "Task completed successfully",
                        "final_response": final_response_text,
                        "history": responses_history,
                        "actions": actions_history
                    }
                else:
                    print("LLM provided no text response or tool calls this turn.")

        # Max turns reached without completion
        final_message = "Maximum interaction turns reached. The task might be incomplete."
        if final_response_text and self.messages[-1].get("role") == "assistant":
            # Don't append the max turns message if the last turn already provided a final response
            pass
        elif final_response_text:
            self.messages.append({"role": "assistant", "content": final_response_text})
            final_message = final_response_text + "\n(Maximum interaction turns reached)"
            self.messages.append({"role": "assistant", "content": "(Maximum interaction turns reached)"})
        else:
            self.messages.append({"role": "assistant", "content": final_message})

        self._dump_messages()
        responses_history.append({
            "turn": self.MAX_TURNS,
            "type": "max_turns_reached",
            "content": final_message
        })
        return {
            "status": "max_turns_reached",
            "message": "Maximum interaction turns reached",
            "final_response": final_message,
            "history": responses_history,
            "actions": actions_history
        }

    def reset_session(self):
        """Reset the session, clearing messages but preserving configuration."""
        # Keep the first system message only
        if self.messages and self.messages[0].get("role") == "system":
            system_message = self.messages[0]
            self.messages = [system_message]
        else:
            self.messages = []
        
        # Close browser if it's open
        if self.browser_started:
            close_result = self.call_function("close_browser", {})
            self.browser_started = False
            return {"status": "success", "message": "Session reset and browser closed.", "close_result": close_result}
        return {"status": "success", "message": "Session reset."}

    def _dump_messages(self):
        """Safely dump messages history to a JSON file for debugging."""
        try:
            serializable_messages = []
            for msg in self.messages:
                if isinstance(msg, dict):
                    serializable_messages.append(msg)
                elif hasattr(msg, "model_dump"):
                    serializable_messages.append(msg.model_dump())
                elif hasattr(msg, "__dict__"):
                    try:
                        # Attempt to serialize vars, exclude unserializable if needed
                        serializable_dict = {}
                        for k, v in vars(msg).items():
                            try:
                                json.dumps(v)  # Test serializability
                                serializable_dict[k] = v
                            except (TypeError, OverflowError):
                                serializable_dict[k] = f"<unserializable: {type(v).__name__}>"
                        serializable_messages.append(serializable_dict)
                    except TypeError:
                        serializable_messages.append(str(msg))
                else:
                    serializable_messages.append(str(msg))

            with open("messages_dump.json", "w", encoding="utf-8") as f:
                json.dump(serializable_messages, f, indent=2, default=str)
        except Exception as e:
            print(f"Error dumping messages: {e}")

# Global dictionary to store BrowserLLM instances by session_id
browser_instances = {}

# Lock for thread-safe operations on the instances dictionary
instances_lock = threading.Lock()

@app.route('/api/browser/interact', methods=['POST'])
def interact():
    """
    API endpoint for browser interaction.
    
    Request body:
    {
        "session_id": "unique_session_identifier",
        "command": "user natural language command",
        "max_turns": 10,  # Optional, default is 10
        "api_key": "openai_api_key",  # Optional
        "driver_path": "path_to_chromedriver"  # Optional
    }
    
    Response:
    {
        "status": "success" | "error" | "max_turns_reached",
        "message": "Human-readable status message",
        "final_response": "Final LLM response text",
        "history": [...],  # List of responses from the conversation
        "actions": [...]   # List of actions taken by the browser
    }
    """
    data = request.json
    
    if not data:
        return jsonify({"status": "error", "message": "Request body is required"}), 400
    
    session_id = data.get('session_id')
    if not session_id:
        return jsonify({"status": "error", "message": "session_id is required"}), 400
    
    command = data.get('command')
    if not command:
        return jsonify({"status": "error", "message": "command is required"}), 400
    
    api_key = data.get('api_key', os.environ.get("OPENAI_API_KEY"))
    driver_path = data.get('driver_path')
    max_turns = data.get('max_turns', 10)
    
    # Validate max_turns
    try:
        max_turns = int(max_turns)
        if max_turns < 1:
            return jsonify({"status": "error", "message": "max_turns must be at least 1"}), 400
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "max_turns must be a valid integer"}), 400
    
    # Get or create a browser instance for this session
    with instances_lock:
        browser_llm = browser_instances.get(session_id)
        if not browser_llm:
            try:
                browser_llm = BrowserLLM(api_key=api_key, driver_path=driver_path)
                browser_instances[session_id] = browser_llm
            except Exception as e:
                return jsonify({
                    "status": "error", 
                    "message": f"Failed to initialize browser: {str(e)}"
                }), 500
    
    # Set max turns
    browser_llm.set_max_turns(max_turns)
    
    # Process the user command
    try:
        result = browser_llm.process_user_input(command)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error processing command: {str(e)}",
            "final_response": f"An error occurred: {str(e)}",
            "history": [],
            "actions": []
        }), 500

@app.route('/api/browser/reset', methods=['POST'])
def reset_session():
    """
    Reset a browser session.
    
    Request body:
    {
        "session_id": "unique_session_identifier"
    }
    
    Response:
    {
        "status": "success" | "error",
        "message": "Human-readable status message"
    }
    """
    data = request.json
    
    if not data:
        return jsonify({"status": "error", "message": "Request body is required"}), 400
    
    session_id = data.get('session_id')
    if not session_id:
        return jsonify({"status": "error", "message": "session_id is required"}), 400
    
    with instances_lock:
        browser_llm = browser_instances.get(session_id)
        if not browser_llm:
            return jsonify({"status": "error", "message": "Session not found"}), 404
        
        try:
            result = browser_llm.reset_session()
            return jsonify(result)
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Error resetting session: {str(e)}"
            }), 500

@app.route('/api/browser/close', methods=['POST'])
def close_browser():
    """
    Close the browser for a session.
    
    Request body:
    {
        "session_id": "unique_session_identifier"
    }
    
    Response:
    {
        "status": "success" | "error",
        "message": "Human-readable status message"
    }
    """
    data = request.json
    
    if not data:
        return jsonify({"status": "error", "message": "Request body is required"}), 400
    
    session_id = data.get('session_id')
    if not session_id:
        return jsonify({"status": "error", "message": "session_id is required"}), 400
    
    with instances_lock:
        browser_llm = browser_instances.get(session_id)
        if not browser_llm:
            return jsonify({"status": "error", "message": "Session not found"}), 404
        
        try:
            if browser_llm.browser_started:
                result = browser_llm.call_function("close_browser", {})
                return jsonify({
                    "status": result.get("status", "error"),
                    "message": result.get("message", result.get("error_message", "Unknown error"))
                })
            else:
                return jsonify({"status": "success", "message": "Browser already closed"})
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Error closing browser: {str(e)}"
            }), 500

@app.route('/api/browser/cleanup', methods=['POST'])
def cleanup_sessions():
    """
    Clean up old or inactive sessions.
    
    Request body:
    {
        "session_ids": ["id1", "id2", ...] # Optional list of specific sessions to clean up
    }
    
    Response:
    {
        "status": "success" | "error",
        "message": "Human-readable status message",
        "cleaned_sessions": ["id1", "id2", ...]
    }
    """
    data = request.json or {}
    session_ids = data.get('session_ids', [])
    
    cleaned_sessions = []
    with instances_lock:
        # If specific sessions provided
        if session_ids:
            for session_id in session_ids:
                browser_llm = browser_instances.get(session_id)
                if browser_llm:
                    if browser_llm.browser_started:
                        browser_llm.call_function("close_browser", {})
                    del browser_instances[session_id]
                    cleaned_sessions.append(session_id)
        # Otherwise clean up all sessions
        else:
            for session_id, browser_llm in list(browser_instances.items()):
                if browser_llm.browser_started:
                    browser_llm.call_function("close_browser", {})
                del browser_instances[session_id]
                cleaned_sessions.append(session_id)
    
    return jsonify({
        "status": "success",
        "message": f"Cleaned up {len(cleaned_sessions)} sessions",
        "cleaned_sessions": cleaned_sessions
    })

@app.route('/api/browser/status', methods=['GET'])
def get_status():
    """
    Get status of all active browser sessions.
    
    Response:
    {
        "status": "success",
        "active_sessions": {
            "session_id1": {
                "browser_started": true,
                "messages_count": 10
            },
            ...
        }
    }
    """
    active_sessions = {}
    with instances_lock:
        for session_id, browser_llm in browser_instances.items():
            active_sessions[session_id] = {
                "browser_started": browser_llm.browser_started,
                "messages_count": len(browser_llm.messages)
            }
    
    return jsonify({
        "status": "success",
        "active_sessions": active_sessions
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
