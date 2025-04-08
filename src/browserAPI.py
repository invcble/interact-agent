from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
import time


class BrowserAPI:
    def __init__(self, driver_path=None):
        """Initialize with an optional path to your ChromeDriver."""
        self.driver_path = driver_path
        self.driver = None

    def start_browser(self):
        """Launch the browser (not headless)."""
        if self.driver_path:
            service = Service(self.driver_path)
            self.driver = webdriver.Chrome(service=service)
        else:
            self.driver = webdriver.Chrome()

        self.driver.set_window_size(1920, 1080)
        print("Browser started.")

    def go_to_website(self, url):
        """Navigate to a specified URL."""
        if not self.driver:
            print("Error: Browser not started yet.")
            return
        self.driver.get(url)
        print(f"Navigated to {url}")
    
    def get_page_content(self):
        """
        Extract structured page content, but ONLY include those interactive elements
        that lie within the current visible area (viewport) of the browser.
        Returns a dictionary with page information in a simplified format.
        """
        if not self.driver:
            return {"error": "Browser not started yet."}
        
        # JavaScript to extract interactive elements within the viewport
        js_script = """
        function getVisibleElementsInViewport() {
            const interactiveElements = [];
            let highlightIndex = 1;
            
            // Get viewport dimensions
            const viewportWidth = window.innerWidth;
            const viewportHeight = window.innerHeight;
            
            // Potentially interactive elements
            const elements = document.querySelectorAll(
            'a, button, input, select, textarea, [role="button"], [tabindex="0"]'
            );
            
            // Helper function to check if the element rect is within the viewport
            function isInViewport(rect) {
                return (
                rect.width > 0 && 
                rect.height > 0 &&
                rect.bottom >= 0 &&
                rect.right >= 0 &&
                rect.top <= viewportHeight &&
                rect.left <= viewportWidth
                );
            }

            elements.forEach(element => {
                const rect = element.getBoundingClientRect();
                if (isInViewport(rect)) {
                    // Get element attributes
                    const attributes = {};
                    for (const attr of element.attributes) {
                        attributes[attr.name] = attr.value;
                    }
                    
                    // Get element text content
                    let textContent = element.textContent.trim();
                    // For <input>, use its 'value' attribute if present
                    if (element.tagName.toLowerCase() === 'input' && element.value) {
                        textContent = element.value;
                    }
                    
                    // Determine element type
                    let elementType = element.tagName.toLowerCase();
                    if (element.getAttribute('role')) {
                        elementType = element.getAttribute('role');
                    }
                    
                    interactiveElements.push({
                        highlightIndex: highlightIndex++,
                        tagName: element.tagName.toLowerCase(),
                        type: elementType,
                        text: textContent,
                        attributes: attributes,
                        coordinates: {
                            x: Math.round(rect.left),
                            y: Math.round(rect.top),
                            width: Math.round(rect.width),
                            height: Math.round(rect.height)
                        },
                        isVisible: true
                    });
                }
            });
            
            return {
                url: window.location.href,
                title: document.title,
                interactiveElements: interactiveElements
            };
        }
        
        return getVisibleElementsInViewport();
        """
        
        # Execute the JavaScript and get the result
        page_content = self.driver.execute_script(js_script)
        
        # Format the content in a simpler textual form
        formatted_elements = []
        
        for elem in page_content["interactiveElements"]:
            elem_desc = f"[{elem['highlightIndex']}] <{elem['tagName']}"
            
            # Add 'role' if different from tag name
            if elem['type'] != elem['tagName']:
                elem_desc += f" role='{elem['type']}'"
            
            for attr in ['id', 'name', 'class']:
                if attr in elem['attributes']:
                    elem_desc += f" {attr}='{elem['attributes'][attr]}'"
            
            elem_desc += (
                f"> {elem['text']} "
                f"(at x:{elem['coordinates']['x']}, y:{elem['coordinates']['y']})"
            )
            formatted_elements.append(elem_desc)
        
        # Return the simplified content
        result = {
            "url": page_content["url"],
            "title": page_content["title"],
            "elements": formatted_elements,
            "element_count": len(page_content["interactiveElements"])
        }
        
        return result


    
    def click_at_coordinates(self, x, y):
        """Click at specific coordinates on the page."""
        if not self.driver:
            return "Error: Browser not started yet."
        
        try:
            # Using JavaScript to click at specific coordinates
            js_script = f"""
            var element = document.elementFromPoint({x}, {y});
            if(element) {{
                element.click();
                return true;
            }} else {{
                return false;
            }}
            """
            result = self.driver.execute_script(js_script)
            
            if result:
                return f"Successfully clicked at coordinates ({x}, {y})"
            else:
                return f"No element found at coordinates ({x}, {y})"
        except Exception as e:
            return f"Error clicking at coordinates ({x}, {y}): {str(e)}"

    def input_text_at_coordinates(self, x, y, text):
        """Input text at specific coordinates on the page."""
        if not self.driver:
            return "Error: Browser not started yet."
        
        try:
            # Using JavaScript to find element at coordinates and input text
            js_script = f"""
            var element = document.elementFromPoint({x}, {y});
            if(element && (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA' || element.isContentEditable)) {{
                element.focus();
                element.value = '{text}';
                var event = new Event('input', {{ bubbles: true }});
                element.dispatchEvent(event);
                return true;
            }} else {{
                return false;
            }}
            """
            result = self.driver.execute_script(js_script)
            
            if result:
                return f"Successfully input text at coordinates ({x}, {y})"
            else:
                return f"No input element found at coordinates ({x}, {y})"
        except Exception as e:
            return f"Error inputting text at coordinates ({x}, {y}): {str(e)}"

    def scroll_page(self, x=0, y=500):
        """
        Scroll the page by the specified amount.
        Positive y scrolls down, negative y scrolls up.
        Positive x scrolls right, negative x scrolls left.
        Default scrolls down 500 pixels.
        """
        if not self.driver:
            return "Error: Browser not started yet."
        
        try:
            # Using JavaScript to scroll
            self.driver.execute_script(f"window.scrollBy({x}, {y});")
            return f"Successfully scrolled by ({x}, {y}) pixels"
        except Exception as e:
            return f"Error scrolling page: {str(e)}"



    def close_browser(self):
        """Close the browser."""
        if not self.driver:
            print("Error: Browser not started or already closed.")
            return
        self.driver.quit()
        self.driver = None
        print("Browser closed.")


if __name__ == "__main__":
    browser_api = BrowserAPI()  # or BrowserAPI(driver_path="/path/to/chromedriver")
    
    # 1) Start the browser
    browser_api.start_browser()

    # 2) Go to a website
    browser_api.go_to_website("https://store.steampowered.com/")
    time.sleep(10)  # Just to see it in action for a moment

    print(browser_api.get_page_content())
    # 3) Close the browser
    time.sleep(10)
    browser_api.scroll_page()
    time.sleep(5)
    print(browser_api.get_page_content())
    time.sleep(100)
    browser_api.close_browser()
