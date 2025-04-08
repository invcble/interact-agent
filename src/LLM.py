from openai import OpenAI
import json
import os
from browserAPI import BrowserAPI
from dotenv import load_dotenv
import time
load_dotenv()

class BrowserLLM:
    def __init__(self, api_key=None, driver_path=None):
        """Initialize the BrowserLLM with OpenAI API key and optional ChromeDriver path."""

        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key must be provided or set as OPENAI_API_KEY environment variable")
        
        self.client = OpenAI(api_key=self.api_key)
        self.browser = BrowserAPI(driver_path)
        self.model = "gpt-4o"
        self.temperature = 0
        self.messages = []

        self.messages.append({
            "role": "system",
            "content": (
                "You are a browser automation assistant. Your job is to control a browser "
                "based on user instructions. You can perform actions like opening websites, "
                "clicking elements, scrolling, and typing text. Use the following tools:\n\n"
                "- `get_page_content`: Retrieve all visible elements on the page, including their coordinates.\n"
                "- `click_at_coordinates`: Click at specific coordinates (x, y) on the page.\n"
                "- `input_text_at_coordinates`: Input text at specific coordinates (x, y) into an input field.\n"
                "- `scroll_page`: Scroll the page by a specified amount of pixels.\n\n"
                "Guidelines:\n"
                "1. When user asks to click/type on something, use `get_page_content` tool to understand what is visible on the page, then use coordinates from the result to decide where to click or type..\n"
                "2. Provide clear feedback about actions taken or errors encountered.\n\n"
                "Your responses should always explain what action you are taking and why."
            )
        })
        
        self.tools = [
            {
                "type": "function",
                "name": "start_browser",
                "description": "Start and open a new browser window",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "type": "function",
                "name": "go_to_website",
                "description": "Navigate to a specific URL in the browser",
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
                "name": "get_page_content",
                "description": "REQUIRED FIRST STEP FOR ANY ACTION. Get interactive elements and their coordinates. Always call this before clicking or typing.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "type": "function",
                "name": "click_at_coordinates",
                "description": "Click at specific coordinates on the page",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "x": {
                            "type": "number",
                            "description": "X coordinate (horizontal position from left)"
                        },
                        "y": {
                            "type": "number",
                            "description": "Y coordinate (vertical position from top)"
                        }
                    },
                    "required": ["x", "y"]
                }
            },
            {
                "type": "function",
                "name": "input_text_at_coordinates",
                "description": "Input text at specific coordinates on the page (must be an input element)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "x": {
                            "type": "number",
                            "description": "X coordinate (horizontal position from left)"
                        },
                        "y": {
                            "type": "number",
                            "description": "Y coordinate (vertical position from top)"
                        },
                        "text": {
                            "type": "string",
                            "description": "Text to input at the specified coordinates"
                        }
                    },
                    "required": ["x", "y", "text"]
                }
            },
            {
                "type": "function",
                "name": "scroll_page",
                "description": "Scroll the page by a specified amount of pixels",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "x": {
                            "type": "number",
                            "description": "Horizontal scroll amount in pixels (positive scrolls right, negative scrolls left)",
                            "default": 0
                        },
                        "y": {
                            "type": "number",
                            "description": "Vertical scroll amount in pixels (positive scrolls down, negative scrolls up)",
                            "default": 500
                        }
                    },
                    "required": []
                }
            },
            {
                "type": "function",
                "name": "close_browser",
                "description": "Close the browser and end the session",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        ]
    
    def call_function(self, name, args):
        """Execute the appropriate browser function based on the name and arguments."""

        if name == "start_browser":
            self.browser.start_browser()
            return "Browser started successfully"
        
        elif name == "go_to_website":
            url = args.get("url")
            self.browser.go_to_website(url)
            return f"Navigated to {url}"
        
        elif name == "close_browser":
            self.browser.close_browser()
            return "Browser closed successfully"
        
        elif name == "get_page_content":
            content = self.browser.get_page_content()

            # Format the content for a simplified version for the LLM
            formatted_elements = []

            for elem in content["elements"]:
                elem_desc = f"[{elem['highlightIndex']}] <{elem['tagName']}"
                
                # Add type if different from tag name
                if elem['type'] != elem['tagName']:
                    elem_desc += f" role='{elem['type']}'"
                
                for attr in ['id', 'name', 'class']:
                    if attr in elem['attributes']:
                        elem_desc += f" {attr}='{elem['attributes'][attr]}'"
                
                elem_desc += f"> {elem['text']} (at x:{elem['coordinates']['x']}, y:{elem['coordinates']['y']})"
                formatted_elements.append(elem_desc)
            
            return {
                "url": content["url"],
                "title": content["title"],
                "elements": formatted_elements,
                "element_count": len(content["elements"])
            }
        
        elif name == "click_at_coordinates":
            x = args.get("x")
            y = args.get("y")
            return self.browser.click_at_coordinates(x, y)

        elif name == "input_text_at_coordinates":
            x = args.get("x")
            y = args.get("y")
            text = args.get("text")
            return self.browser.input_text_at_coordinates(x, y, text)

        elif name == "scroll_page":
            x = args.get("x", 0)
            y = args.get("y", 500)
            result = self.browser.scroll_page(x, y)
            
            content_result = self.browser.get_page_content()
            
            return {
                "scroll_result": result,
                "page_content": content_result
            }
        
        else:
            return f"Unknown function: {name}"
    
    def process_user_input(self, user_input):
        """Process user input with forced tool chaining"""

        self.messages.append({"role": "user", "content": user_input})       
        final_response = None

        # Forcing iteration for get_page_content tool call to keep vision updated 
        max_iterations = 2
        for _ in range(max_iterations):
            tool_choice = "required" if _ > 0 else "auto"
            
            response = self.client.responses.create(
                model=self.model,
                input=self.messages,
                temperature=self.temperature,
                tools=self.tools,
                tool_choice=tool_choice
            )
            
            tool_calls = [tc for tc in response.output if tc.type == "function_call"]
            if not tool_calls:
                final_response = response.output_text
                break
                
            for tool_call in tool_calls:

                # Execute function
                args = json.loads(tool_call.arguments)
                print(f"calling tool -----------------{tool_call.name}-----------------")
                result = self.call_function(tool_call.name, args)
                print(f"tool called -----------> {result}\n")
                
                # Cleared old vision to reduce token count
                for msg in self.messages:
                    if isinstance(msg, dict) and msg.get("type") == "function_call_output":
                        output = msg.get("output", "")
                        if isinstance(output, str) and "<vision>" in output and "</vision>" in output:
                            msg["output"] = "<vision> Cleared to reduce tokens </vision>"

                # Append to message history
                self.messages.append(tool_call)

                if tool_call.name == "get_page_content":
                    special_output = f"<vision> {result} </vision>"
                    
                else:
                    special_output = str(result)

                self.messages.append({
                    "type": "function_call_output",
                    "call_id": tool_call.call_id,
                    "output": special_output
                })

        if final_response:
            self.messages.append({"role": "assistant", "content": final_response})
            # return final_response
        
        # Safely dump messages to JSON
        try:
            # Serialize each message safely
            serializable_messages = []
            for msg in self.messages:
                if isinstance(msg, dict):
                    serializable_messages.append(msg)
                elif hasattr(msg, "model_dump"):
                    serializable_messages.append(msg.model_dump())
                else:
                    serializable_messages.append(str(msg))

            with open("messages_dump.json", "w", encoding="utf-8") as f:
                json.dump(serializable_messages, f, indent=2)
        except Exception as e:
            print(f"Error dumping messages: {e}")

        return final_response if final_response else "Maximum iterations reached"


# Example usage
if __name__ == "__main__":
    browser_llm = BrowserLLM()
    
    print("Browser Control Assistant (type 'exit' to quit)")
    print("-" * 50)
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ['exit', 'quit', 'bye']:
            break
        
        response = browser_llm.process_user_input(user_input)
        print(f"\nAssistant: {response}")
