import os
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

from config import load_config

configs = load_config()

class WebElement:
    def __init__(self, uid, location, size, attrib):
        self.uid = uid
        self.location = location
        self.size = size
        self.attrib = attrib

def launch_browser(url):
    
    # initialize the browser
    webdriver.ChromeOptions()


    options = Options()
    # user_data_dir = r"/Users/jude.park/Library/Application Support/Google/Chrome"
    # options.add_argument(f"user-data-dir={user_data_dir}")
    options.add_experimental_option("detach", True)  # Keep the browser open
    options.add_argument("--start-maximized")  # Start maximized

    driver = webdriver.Chrome(options=options)
    driver.get(url)
    return driver


def get_id_from_element(element):
    elem_id = element.tag_name
    if element.get_attribute("id"):
        elem_id = element.get_attribute("id").replace(":", ".").replace("/", "_")
    elif element.get_attribute("class"):
        elem_id = element.get_attribute("class").replace(" ", "_").replace(":", ".").replace("/", "_")
    elif element.get_attribute("name"):
        elem_id = element.get_attribute("name").replace(" ", "_").replace(":", ".").replace("/", "_")
    return elem_id

def traverse_tree(html, elem_list, attrib):
    soup = BeautifulSoup(html, 'html.parser')
    for elem in soup.find_all(True):
        if elem.has_attr(attrib):
            location = {"x": elem.location["x"], "y": elem.location["y"]}
            size = {"width": elem.size["width"], "height": elem.size["height"]}
            elem_id = get_id_from_element(elem)
            close = False
            for e in elem_list:
                center = (e.location["x"] + e.size["width"] // 2, e.location["y"] + e.size["height"] // 2)
                center_ = (location["x"] + size["width"] // 2, location["y"] + size["height"] // 2)
                dist = (abs(center[0] - center_[0]) ** 2 + abs(center[1] - center_[1]) ** 2) ** 0.5
                if dist <= configs["MIN_DIST"]:
                    close = True
                    break
            if not close:
                elem_list.append(WebElement(elem_id, location, size, attrib))

class WebController:
    def __init__(self):
        self.driver = webdriver.Chrome()  # Use Chrome as an example. You can use other browsers like Safari.
        self.screenshot_dir = configs["WEB_SCREENSHOT_DIR"]
        self.html_dir = configs["WEB_HTML_DIR"]
        self.width, self.height = self.get_canvas_size(self.driver)

    def get_canvas_size(self, driver):
        canvas = driver.find_element(By.TAG_NAME, "canvas")
        width = canvas.get_attribute("width")
        height = canvas.get_attribute("height")
        return width, height

    def navigate_to(self, url):
        self.driver.get(url)

    def get_screenshot(self, prefix):
        screenshot_path = os.path.join(self.screenshot_dir, prefix + ".png")
        self.driver.save_screenshot(screenshot_path)
        return screenshot_path

    def get_html(self, prefix):
        html_path = os.path.join(self.html_dir, prefix + ".html")
        with open(html_path, "w") as f:
            f.write(self.driver.page_source)
        return html_path

    def back(self):
        self.driver.back()

    def click(self, element):
        element.click()

    def input_text(self, element, text):
        element.send_keys(text)

    def long_press(self, element):
        ActionChains(self.driver).click_and_hold(element).perform()

    def scroll(self, direction):
        if direction == "up":
            self.driver.find_element_by_tag_name('body').send_keys(Keys.PAGE_UP)
        elif direction == "down":
            self.driver.find_element_by_tag_name('body').send_keys(Keys.PAGE_DOWN)
        else:
            print("Invalid direction. Only 'up' and 'down' are supported.")