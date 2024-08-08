import sys
import re
import cv2
import time
import os
import uuid
import shutil
from PIL import Image
from io import BytesIO

import numpy as np
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


def find_canvas_id(node_id, nodes, canvas_id=None):
    for node in nodes:
        if node["type"] == "CANVAS":
            canvas_id = node["id"]
        if node["id"] == node_id:
            return canvas_id
        if "children" in node:
            found_canvas_id = find_canvas_id(node_id, node["children"], canvas_id)
            if found_canvas_id:
                return found_canvas_id


def find_node_by_id(node_id, nodes):
    for node in nodes:
        if node["id"] == node_id:
            return node
        if "children" in node:
            found_node = find_node_by_id(node_id, node["children"])
            if found_node:
                return found_node
    return None


def list_all_devices(node_id, nodes):
    device_list = []
    canvas_id = find_canvas_id(node_id, nodes)

    for node in nodes:
        if node["id"] == canvas_id:
            device_list.append(node.get("prototypeDevice", "N/A"))

            return device_list

        if "children" in node:
            list_all_devices(canvas_id, node["children"])


def draw_bbox_multi(img_path, output_path, predictions, dark_mode=False):
    imgcv = cv2.imread(img_path)
    count = 1
    for prediction in predictions:
        try:
            left = int(prediction["x"] - prediction["width"] / 2)
            top = int(prediction["y"] - prediction["height"] / 2)
            right = int(prediction["x"] + prediction["width"] / 2)
            bottom = int(prediction["y"] + prediction["height"] / 2)
            label = str(count)
            text_color = (10, 10, 10) if dark_mode else (255, 250, 250)
            bg_color = (255, 250, 250) if dark_mode else (10, 10, 10)
            imgcv = cv2.rectangle(imgcv, (left, top), (right, bottom), bg_color, 2)
            imgcv = cv2.putText(
                imgcv,
                label,
                (left, top - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                text_color,
                2,
            )
        except Exception as e:
            print(f"ERROR: An exception occurs while labeling the image\n{e}")
        count += 1
    cv2.imwrite(output_path, imgcv)
    return imgcv


def append_to_log(text: str, log_file: str, break_line: bool = True):
    with open(log_file, "a") as f:
        f.write(text + ("\n" if break_line else ""))

def move_to_static(file_path, static_dir):
    unique_id = str(uuid.uuid4())
    file_extension = os.path.splitext(file_path)[1]
    new_filename = f"{unique_id}{file_extension}"
    new_path = os.path.join(static_dir, new_filename)
    shutil.copy(file_path, new_path)
    return new_path




class SeleniumController:
    def __init__(self, url, password):
        self.url = url
        self.password = password
        self.driver = None

    def execute_selenium(self):
        options = Options()
        options.add_argument("user-data-dir=./User_Data")
        options.add_argument("disable-blink-features=AutomationControlled")
        options.add_argument("--start-maximized")
        options.add_experimental_option("detach", True)

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)

        self.driver.get(self.url)

        # Create a wait object with a timeout
        wait = WebDriverWait(self.driver, 10)  # Wait for up to 10 seconds

        # Check if the password form is present
        try:
            # Use explicit wait to wait for the password form to appear
            password_form = wait.until(EC.presence_of_element_located((By.ID, "link-password-form")))
        except:
            # If the password form is not present, return
            return

        # If the password form is present, input the password
        password_input = password_form.find_element(By.NAME, "password")
        password_input.send_keys(self.password)

        # Click the continue button
        continue_button = password_form.find_element(
            By.XPATH, "//button[@type='submit']"
        )
        continue_button.click()

        # Use explicit wait for a condition after submitting the password
        # Example: Wait until a specific element is loaded after login
        # wait.until(EC.presence_of_element_located((By.ID, "some_element_after_login")))

        # Check if the password form is still present
        try:
            password_form = wait.until(EC.presence_of_element_located((By.ID, "link-password-form")))
            print("ERROR: The provided password is incorrect.")
            sys.exit(1)
        except:
            # If the password form is not present, continue
            pass


    def get_canvas_size(self):
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "canvas"))
        )

        canvas = self.driver.find_element(By.TAG_NAME, "canvas")
        style = canvas.get_attribute("style")
        print(f"Canvas style: {style}")  # 스타일 속성 출력

        width_match = re.search(r"width: (\d+(?:\.\d+)?)px", style)
        height_match = re.search(r"height: (\d+(?:\.\d+)?)px", style)

        if width_match is None or height_match is None:
            raise ValueError("Cannot find width or height in the style attribute")

        width = width_match.group(1)
        height = height_match.group(1)

        return int(float(width)), int(float(height))

    def calculate_position(
        self, device_width, device_height, canvas_width, canvas_height
    ):
        # Calculate the position of the device image in the center of the canvas
        x = (canvas_width - device_width) / 2
        y = (canvas_height - device_height) / 2

        return x, y

    def zoom_out_until_canvas_fits(self, device_width, device_height):
        canvas_width, canvas_height = self.get_canvas_size()
        while canvas_width < device_width + 64 or canvas_height < device_height + 64:
            self.driver.execute_script("document.body.style.zoom='80%'")
            canvas_width, canvas_height = self.get_canvas_size()

            # Refresh the browser after zooming out
            self.driver.refresh()

        # Return the final canvas size
        return canvas_width, canvas_height

    def take_screenshot(self, x, y, width, height, save_path):
        # Take a screenshot of the <canvas> element
        canvas = self.driver.find_element(By.TAG_NAME, "canvas")
        screenshot = canvas.screenshot_as_png

        # Convert the screenshot to an Image object
        img = Image.open(BytesIO(screenshot))

        # Crop the image to the specified area
        cropped_img = img.crop((x, y, x + width, y + height))

        # Save the cropped image
        cropped_img.save(save_path)

    def take_canvas_screenshot(self, screenshot_path, tl, br, output_path):
        # Load the existing screenshot
        img = Image.open(screenshot_path)

        # Convert the image to an OpenCV image (numpy array)
        imgcv = np.array(img)
        imgcv = imgcv[:, :, ::-1].copy()

        # Draw the bounding box
        cv2.rectangle(
            imgcv, (int(tl[0]), int(tl[1])), (int(br[0]), int(br[1])), (0, 255, 0), 2
        )

        # Save the image
        cv2.imwrite(output_path, imgcv)


    def draw_circle(self, x, y, img_path, r=10, thickness=2):
        img = cv2.imread(img_path)
        cv2.circle(img, (int(x), int(y)), r, (0, 0, 255), thickness)
        cv2.imwrite(img_path, img)
    
    def draw_arrow(self, x, y, direction, dist, image_path, arrow_color=(0, 255, 0), thickness=2):
        img = cv2.imread(image_path)
        
        # Calculate the arrow length based on the screen width and dist
        screen_width = img.shape[1]
        unit_dist = int(screen_width / 10)
        if dist == "long":
            arrow_length = 3 * unit_dist
        elif dist == "medium":
            arrow_length = 2 * unit_dist
        else:
            arrow_length = unit_dist
        
        # Define the arrow directions
        if direction == "up":
            end_point = (x, y - arrow_length)
        elif direction == "down":
            end_point = (x, y + arrow_length)
        elif direction == "left":
            end_point = (x - arrow_length, y)
        elif direction == "right":
            end_point = (x + arrow_length, y)
        else:
            raise ValueError(f"Invalid direction: {direction}")
        
        # Draw the arrow
        cv2.arrowedLine(img, (x, y), end_point, arrow_color, thickness)
        
        # Save the modified image
        cv2.imwrite(image_path, img)

    def get_current_node_id(self):
        # Get the current URL
        current_url = self.driver.current_url

        # Extract the node ID from the URL
        node_id_match = re.search(r"node-id=(.*?)(?:&|$)", current_url)
        if node_id_match is None:
            print("ERROR: Failed to extract node-id from the URL", "red")
            sys.exit(1)
        node_id = node_id_match.group(1)

        # Replace "-" in the node ID with ":"
        node_id = node_id.replace("-", ":")

        return node_id

    def back(self):
        self.driver.back()

    def tap(self, x, y):
        # Create an ActionChains object
        actions = webdriver.ActionChains(self.driver)

        # Move to the position and click
        actions.move_by_offset(x, y).click().perform()

        # Reset the pointer position to the original position
        actions.move_by_offset(-x, -y).perform()

    def text(self, input_str):
        # Create an ActionChains object
        actions = webdriver.ActionChains(self.driver)

        # Send the keys
        actions.send_keys(input_str).perform()

    def long_press(self, x, y, duration=1000):

        # Create an ActionChains object
        actions = webdriver.ActionChains(self.driver)

        # Move to the position and click and hold
        actions.move_by_offset(x, y).click_and_hold().perform()

        # Wait for the specified duration and release
        time.sleep(duration / 1000)
        actions.release().perform()

        # Reset the pointer position to the original position
        actions.move_by_offset(-x, -y).perform()

    def swipe(self, x, y, direction, dist="medium", quick=False):

        # Calculate the offset based on the direction and distance
        offset = {
            "up": (0, -2 * self.height / 10),
            "down": (0, 2 * self.height / 10),
            "left": (-1 * self.width / 10, 0),
            "right": (self.width / 10, 0),
        }.get(direction, (0, 0))

        # Adjust the offset based on the distance
        if dist == "long":
            offset = (offset[0] * 3, offset[1] * 3)
        elif dist == "medium":
            offset = (offset[0] * 2, offset[1] * 2)

        # Create an ActionChains object
        actions = webdriver.ActionChains(self.driver)

        # Move to the start position, click and hold, move by the offset, and release
        actions.move_by_offset(x, y).click_and_hold().move_by_offset(
            *offset
        ).release().perform()

    def draw_bounding_box(self, img_path, tl, br, output_path):
        img = cv2.imread(img_path)
        cv2.rectangle(img, tl, br, (0, 255, 0), 2)
        cv2.imwrite(output_path, img)

    def get_canvas_bounds(self):
        canvas = self.driver.find_element(By.TAG_NAME, "canvas")
        location = canvas.location
        size = canvas.size
        tl = (location["x"], location["y"])
        br = (location["x"] + size["width"], location["y"] + size["height"])
        return tl, br


class UIElement:
    def __init__(self, uid, bbox):
        self.uid = uid
        self.bbox = bbox

    @classmethod
    def create_elem_list(self, predictions):
        elem_list = []
        for prediction in predictions:
            # Create a UI element
            elem = UIElement(
                uid=prediction["detection_id"],
                bbox=[
                    [
                        int(prediction["x"] - prediction["width"] / 2),
                        int(prediction["y"] - prediction["height"] / 2),
                    ],
                    [
                        int(prediction["x"] + prediction["width"] / 2),
                        int(prediction["y"] + prediction["height"] / 2),
                    ],
                ],
            )
            # Add the UI element to the list
            elem_list.append(elem)
        return elem_list

    def process_node_data(node_data):
        # Initialize the list of UIElements
        elem_list = []

        # Get the bounding box of the root node
        root_bbox = node_data["absoluteBoundingBox"]

        def convert_node_to_UIElement(node):
            # Create a UIElement from a node
            bbox = [
                (
                    int(node["absoluteBoundingBox"]["x"] - root_bbox["x"]),
                    int(node["absoluteBoundingBox"]["y"] - root_bbox["y"]),
                ),  # Top-left corner
                (
                    int(
                        node["absoluteBoundingBox"]["x"]
                        - root_bbox["x"]
                        + node["absoluteBoundingBox"]["width"]
                    ),  # Bottom-right corner
                    int(
                        node["absoluteBoundingBox"]["y"]
                        - root_bbox["y"]
                        + node["absoluteBoundingBox"]["height"]
                    ),
                ),
            ]
            return UIElement(node["id"], bbox)

        # Traverse the node data
        nodes_to_process = [node_data]
        while nodes_to_process:
            node = nodes_to_process.pop()

            # Check if the node is visible
            if node.get("visible", True) != False:
                # If the node is of type FRAME, INSTANCE, GROUP, or COMPONENT, convert it to a UIElement
                if node["type"] in ["FRAME", "INSTANCE", "COMPONENT", "GROUP"]:
                    elem = convert_node_to_UIElement(node)
                    elem_list.append(elem)

                # If the node has children, add them to the list of nodes to process
                if "children" in node:
                    nodes_to_process.extend(node["children"])

        return elem_list
