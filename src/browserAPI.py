from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
import time
import os
import random
import math

class BrowserAPI:
    def __init__(self, driver_path=None):
        """Initialize with an optional path to your ChromeDriver."""
        self.driver_path = driver_path
        self.driver = None

    def start_browser(self):
        """Launch the browser (non-headless)."""
        if self.driver:
            return {
                "status": "error",
                "error_message": "Browser already started"
            }
        
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--log-level=3")

            if self.driver_path:
                service = Service(self.driver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                self.driver = webdriver.Chrome(options=options)

            self.driver.set_window_size(1080, 1080)

            return {
                "status": "success",
                "message": "Browser started",
                "content": "No content yet, visit an URL to get content"
            }

        except Exception as e:
            return {
                "status": "error",
                "error_message": f"Failed to start browser: {e}"
            }

    def _get_page_content(self):
        """
        Extract structured page content, but ONLY include those interactive elements
        that lie within the current visible area (viewport) of the browser.
        Returns a dictionary with page information in a simplified format.
        """
        if not self.driver:
            return {"error": "Browser not started yet."}
        
        # Read JS from a separate file & Execute
        script_path = os.path.join(os.path.dirname(__file__), "get_visible_elements.js")
        with open(script_path, "r", encoding="utf-8") as f:
            js_script = f.read()
        
        page_content = self.driver.execute_script(js_script)
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
        
        return {
            "url": page_content["url"],
            "title": page_content["title"],
            "elements": formatted_elements,
            "element_count": len(page_content["interactiveElements"])
        }
    
    def refresh_content(self):
        """
        Re-extract the latest page content without reloading the page.
        Useful for checking for dynamic changes on the current page.
        """
        if not self.driver:
            return {
                "status": "error",
                "error_message": "Browser not started"
            }

        try:
            time.sleep(2)
            content = self._get_page_content()

            return {
                "status": "success",
                "message": "Page content refreshed successfully",
                "content": content
            }

        except Exception as e:
            return {
                "status": "error",
                "error_message": f"Content refresh failed: {e}"
            }

    def go_to_website(self, url):
        """Navigate to a specified URL."""
        if not self.driver:
            return {
                "status": "error",
                "error_message": "Browser not started"
            }

        try:
            self.driver.get(url)
            time.sleep(5)
            content = self._get_page_content()

            return {
                "status": "success",
                "message": f"Navigated to {url}",
                "content": content
            }

        except Exception as e:
            return {
                "status": "error",
                "error_message": f"Navigation failed: {e}"
            }

    def click_at_coordinates(self, x, y):
        """
        Click at screen coordinates (x, y). 
        1. Tries to find a clickable DOM element at that point and click it.
        2. Falls back to offset-based clicking if no element is found.
        """
        if not self.driver:
            return {
                "status": "error",
                "error_message": "Browser not started"
            }

        try:
            # Try to get clickable element from coordinates
            element = self.driver.execute_script("""
                const elem = document.elementFromPoint(arguments[0], arguments[1]);
                if (!elem) return null;

                if (['a', 'button', 'input', 'label'].includes(elem.tagName.toLowerCase())) {
                    return elem;
                }

                const clickable = elem.querySelector('a, button, input, label');
                return clickable || elem;
            """, x, y)

            actions = ActionChains(self.driver)

            if element:
                try:
                    self.driver.execute_script("""
                        const testElem = document.elementFromPoint(arguments[0], arguments[1]);
                        if (testElem) {
                            testElem.style.border = '2px solid red';
                            testElem.setAttribute('data-click-target', 'true');
                        }
                    """, x, y)

                    actions.move_to_element_with_offset(element, 1, 1).click().perform()
                except Exception as click_error:
                    print(f"Click on element failed, falling back to offset: {click_error}")
                    actions.move_by_offset(x, y).click().perform()
            else:
                print("No element returned. Clicking by offset fallback.")
                actions.move_by_offset(x, y).click().perform()

            print("-----------")
            time.sleep(5)
            content = self._get_page_content()

            return {
                "status": "success",
                "content": content
            }

        except Exception as e:
            return {
                "status": "error",
                "error_message": f"Click failed at ({x}, {y}): {e}"
            }

    def input_text_at_coordinates(self, x, y, text):
        """
        Type text into the input field located at screen coordinates (x, y). Tries to:
        1. Locate the DOM element at (x, y) and type into it precisely.
        2. If that fails, falls back to offset-based interaction.
        """
        if not self.driver:
            return {
                "status": "error",
                "error_message": "Browser not started"
            }

        try:
            #temp offset
            x += 15
            
            element = self.driver.execute_script(
                "return document.elementFromPoint(arguments[0], arguments[1]);", x, y
            )

            actions = ActionChains(self.driver)
            if element:
                actions.move_to_element_with_offset(element, 1, 1).click().send_keys(text).perform()
            else:
                actions.move_by_offset(x, y).click().send_keys(text).perform()
            
            time.sleep(5)
            content = self._get_page_content()

            return { 
                "status": "success",
                "content": content
            }

        except Exception as e:
            return {
                "status": "error",
                "error_message": f"Text input failed at ({x}, {y}): {e}"
            }

    def scroll_page(self, x=0, y=500):
        """
        Smoothly scroll the page by the specified amount.
        Positive y scrolls down, negative y scrolls up.
        Positive x scrolls right, negative x scrolls left.
        Default scrolls down 500 pixels.
        """
        if not self.driver:
            return {
                "status": "error",
                "error_message": "Browser not started"
            }

        try:
            self.driver.execute_script("""
                window.scrollBy({
                    top: arguments[1],
                    left: arguments[0],
                    behavior: 'smooth'
                });
            """, x, y)

            time.sleep(5)
            content = self._get_page_content()

            return {
                "status": "success",
                "message": f"Scrolled smoothly by ({x}, {y}) pixels",
                "content": content
            }

        except Exception as e:
            return {
                "status": "error",
                "error_message": f"Scroll failed: {e}"
            }

    def close_browser(self):
        """
        Close the browser if it's open.
        """
        if not self.driver:
            return {
                "status": "error",
                "error_message": "Browser not started or already closed"
            }

        try:
            self.driver.quit()
            self.driver = None
            return {
                "status": "success",
                "message": "Browser closed",
                "content": "No content as browser closed"
            }

        except Exception as e:
            return {
                "status": "error",
                "error_message": f"Failed to close browser: {e}"
            }


def show_menu():
    print("""
Choose an action:
1. Start Browser
2. Go to Website
3. Get Page Content
4. Input Something at x,y
5. Click at Coordinates
6. Close Browser
0. Exit
""")

if __name__ == "__main__":
    browser_api = BrowserAPI()  # or BrowserAPI(driver_path="/path/to/chromedriver")
    browser_started = False

    while True:
        show_menu()
        choice = input("Enter your choice: ")

        if choice == "1":
            print(browser_api.start_browser())
            browser_started = True

        elif choice == "2":
            if not browser_started:
                print("Please start the browser first.")
                continue
            url = input("Enter URL to visit: ")
            print(browser_api.go_to_website(url))

        elif choice == "3":
            if not browser_started:
                print("Please start the browser first.")
                continue
            print(browser_api._get_page_content())

        elif choice == "4":
            if not browser_started:
                print("Please start the browser first.")
                continue
            captcha = input("Enter text: ")
            x = int(input("Enter x coordinate: "))
            y = int(input("Enter y coordinate: "))
            print(browser_api.input_text_at_coordinates(x, y, captcha))

        elif choice == "5":
            if not browser_started:
                print("Please start the browser first.")
                continue
            x = int(input("Enter x coordinate: "))
            y = int(input("Enter y coordinate: "))
            print(browser_api.click_at_coordinates(x, y))

        elif choice == "6":
            if not browser_started:
                print("Browser not started.")
            else:
                browser_api.close_browser()
                browser_started = False

        elif choice == "0":
            if browser_started:
                browser_api.close_browser()
            print("Exiting...")
            break

        else:
            print("Invalid choice. Please try again.")

