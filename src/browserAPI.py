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

            self.driver.set_window_size(1920, 1080)
            return {
                "status": "success",
                "message": "Browser started"
            }

        except Exception as e:
            return {
                "status": "error",
                "error_message": f"Failed to start browser: {e}"
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
            return {
                "status": "success",
                "message": f"Navigated to {url}"
            }

        except Exception as e:
            return {
                "status": "error",
                "error_message": f"Navigation failed: {e}"
            }
    
    def _get_page_content(self):
        """
        Extract structured page content, but ONLY include those interactive elements
        that lie within the current visible area (viewport) of the browser.
        Returns a dictionary with page information in a simplified format.
        """
        if not self.driver:
            return {"error": "Browser not started yet."}
        
        # Read JS from a separate file
        script_path = os.path.join(os.path.dirname(__file__), "get_visible_elements.js")
        with open(script_path, "r", encoding="utf-8") as f:
            js_script = f.read()
        
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
        
        return {
            "url": page_content["url"],
            "title": page_content["title"],
            "elements": formatted_elements,
            "element_count": len(page_content["interactiveElements"])
        }

    def click_at_coordinates(self, x, y):
        """
        Click at screen coordinates (x, y). Tries to:
        1. Locate the DOM element at (x, y) and click it precisely.
        2. If that fails, falls back to offset-based clicking.
        """
        if not self.driver:
            return {
                "status": "error",
                "error_message": "Browser not started"
            }

        try:
            element = self.driver.execute_script(
                "return document.elementFromPoint(arguments[0], arguments[1]);", x, y
            )

            actions = ActionChains(self.driver)
            if element:
                actions.move_to_element_with_offset(element, 1, 1).click().perform()
            else:
                actions.move_by_offset(x, y).click().perform()

            return { "status": "success" }

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
            element = self.driver.execute_script(
                "return document.elementFromPoint(arguments[0], arguments[1]);", x, y
            )

            actions = ActionChains(self.driver)
            if element:
                actions.move_to_element_with_offset(element, 1, 1).click().send_keys(text).perform()
            else:
                actions.move_by_offset(x, y).click().send_keys(text).perform()

            return { "status": "success" }

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

            return {
                "status": "success",
                "message": f"Scrolled smoothly by ({x}, {y}) pixels"
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
                "message": "Browser closed"
            }

        except Exception as e:
            return {
                "status": "error",
                "error_message": f"Failed to close browser: {e}"
            }


# Continue shopping (at x:478, y:474)
# class='a-span12'>  (at x:496, y:391)
# Conditions of Use (at x:531, y:521)
if __name__ == "__main__":
    browser_api = BrowserAPI()  # or BrowserAPI(driver_path="/path/to/chromedriver")
    
    # 1) Start the browser
    print(browser_api.start_browser())

    # 2) Go to a website
    print(browser_api.go_to_website("https://www.amazon.com/"))
    time.sleep(3)

    print(browser_api._get_page_content())
    time.sleep(1)

    captcha = input("Enter captcha: ")

    print(browser_api.input_text_at_coordinates(496, 391, captcha))
    time.sleep(3)

    print(browser_api.click_at_coordinates(478, 474))
    # browser_api.scroll_page()
    # time.sleep(5)
    # print(browser_api.get_page_content())
    # time.sleep(3)
    # print("clicking")
    # print(browser_api.click_at_coordinates(531, 521))
    time.sleep(100)

    browser_api.close_browser()
