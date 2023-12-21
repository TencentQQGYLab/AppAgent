import argparse
import datetime

import cv2
import os
import shutil
import sys
import time

from and_controller import list_all_devices, AndroidController, traverse_tree
from config import load_config
from utils import print_with_color, draw_bbox_multi

arg_desc = "AppAgent - Human Demonstration"
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=arg_desc)
parser.add_argument("--app")
parser.add_argument("--demo")
parser.add_argument("--root_dir", default="./")
args = vars(parser.parse_args())

app = args["app"]
demo_name = args["demo"]
root_dir = args["root_dir"]

configs = load_config()

if not app:
    print_with_color("What is the name of the app you are going to demo?", "blue")
    app = input()
    app = app.replace(" ", "")
if not demo_name:
    demo_timestamp = int(time.time())
    demo_name = datetime.datetime.fromtimestamp(demo_timestamp).strftime(f"demo_{app}_%Y-%m-%d_%H-%M-%S")

work_dir = os.path.join(root_dir, "apps")
if not os.path.exists(work_dir):
    os.mkdir(work_dir)
work_dir = os.path.join(work_dir, app)
if not os.path.exists(work_dir):
    os.mkdir(work_dir)
demo_dir = os.path.join(work_dir, "demos")
if not os.path.exists(demo_dir):
    os.mkdir(demo_dir)
task_dir = os.path.join(demo_dir, demo_name)
if os.path.exists(task_dir):
    shutil.rmtree(task_dir)
os.mkdir(task_dir)
raw_ss_dir = os.path.join(task_dir, "raw_screenshots")
os.mkdir(raw_ss_dir)
xml_dir = os.path.join(task_dir, "xml")
os.mkdir(xml_dir)
labeled_ss_dir = os.path.join(task_dir, "labeled_screenshots")
os.mkdir(labeled_ss_dir)
record_path = os.path.join(task_dir, "record.txt")
record_file = open(record_path, "w")
task_desc_path = os.path.join(task_dir, "task_desc.txt")

device_list = list_all_devices()
if not device_list:
    print_with_color("ERROR: No device found!", "red")
    sys.exit()
print_with_color("List of devices attached:\n" + str(device_list), "yellow")
if len(device_list) == 1:
    device = device_list[0]
    print_with_color(f"Device selected: {device}", "yellow")
else:
    print_with_color("Please choose the Android device to start demo by entering its ID:", "blue")
    device = input()
controller = AndroidController(device)
width, height = controller.get_device_size()
if not width and not height:
    print_with_color("ERROR: Invalid device size!", "red")
    sys.exit()
print_with_color(f"Screen resolution of {device}: {width}x{height}", "yellow")

print_with_color("Please state the goal of your following demo actions clearly, e.g. send a message to John", "blue")
task_desc = input()
with open(task_desc_path, "w") as f:
    f.write(task_desc)

print_with_color("All interactive elements on the screen are labeled with red and blue numeric tags. Elements "
                 "labeled with red tags are clickable elements; elements labeled with blue tags are scrollable "
                 "elements.", "blue")

step = 0
while True:
    step += 1
    screenshot_path = controller.get_screenshot(f"{demo_name}_{step}", raw_ss_dir)
    xml_path = controller.get_xml(f"{demo_name}_{step}", xml_dir)
    if screenshot_path == "ERROR" or xml_path == "ERROR":
        break
    clickable_list = []
    focusable_list = []
    traverse_tree(xml_path, clickable_list, "clickable", True)
    traverse_tree(xml_path, focusable_list, "focusable", True)
    elem_list = clickable_list.copy()
    for elem in focusable_list:
        bbox = elem.bbox
        center = (bbox[0][0] + bbox[1][0]) // 2, (bbox[0][1] + bbox[1][1]) // 2
        close = False
        for e in clickable_list:
            bbox = e.bbox
            center_ = (bbox[0][0] + bbox[1][0]) // 2, (bbox[0][1] + bbox[1][1]) // 2
            dist = (abs(center[0] - center_[0]) ** 2 + abs(center[1] - center_[1]) ** 2) ** 0.5
            if dist <= configs["MIN_DIST"]:
                close = True
                break
        if not close:
            elem_list.append(elem)
    labeled_img = draw_bbox_multi(screenshot_path, os.path.join(labeled_ss_dir, f"{demo_name}_{step}.png"), elem_list,
                                  True)
    cv2.imshow("image", labeled_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    user_input = "xxx"
    print_with_color("Choose one of the following actions you want to perform on the current screen:\ntap, text, long "
                     "press, swipe, stop", "blue")
    while user_input.lower() != "tap" and user_input.lower() != "text" and user_input.lower() != "long press" \
            and user_input.lower() != "swipe" and user_input.lower() != "stop":
        user_input = input()
    if user_input.lower() == "tap":
        print_with_color(f"Which element do you want to tap? Choose a numeric tag from 1 to {len(elem_list)}:", "blue")
        user_input = "xxx"
        while not user_input.isnumeric() or int(user_input) > len(elem_list) or int(user_input) < 1:
            user_input = input()
        tap_area = elem_list[int(user_input) - 1].bbox
        controller.tap(tap_area[0], tap_area[1])
        record_file.write(f"tap({int(user_input)}):::{elem_list[int(user_input) - 1].uid}\n")
    elif user_input.lower() == "text":
        print_with_color(f"Which element do you want to input the text string? Choose a numeric tag from 1 to "
                         f"{len(elem_list)}:", "blue")
        input_area = "xxx"
        while not input_area.isnumeric() or int(input_area) > len(elem_list) or int(input_area) < 1:
            input_area = input()
        print_with_color("Enter your input text below:", "blue")
        user_input = ""
        while not user_input:
            user_input = input()
        controller.text(user_input)
        record_file.write(f"text({input_area}:sep:\"{user_input}\"):::{elem_list[int(input_area) - 1].uid}\n")
    elif user_input.lower() == "long press":
        print_with_color(f"Which element do you want to long press? Choose a numeric tag from 1 to {len(elem_list)}:",
                         "blue")
        user_input = "xxx"
        while not user_input.isnumeric() or int(user_input) > len(elem_list) or int(user_input) < 1:
            user_input = input()
        tap_area = elem_list[int(user_input) - 1].bbox
        controller.long_press(tap_area[0], tap_area[1])
        record_file.write(f"long_press({int(user_input)}):::{elem_list[int(user_input) - 1].uid}\n")
    elif user_input.lower() == "swipe":
        print_with_color(f"What is the direction of your swipe? Choose one from the following options:\nup, down, left,"
                         f" right", "blue")
        user_input = ""
        while user_input != "up" and user_input != "down" and user_input != "left" and user_input != "right":
            user_input = input()
        swipe_dir = user_input
        print_with_color(f"Which element do you want to swipe? Choose a numeric tag from 1 to {len(elem_list)}:")
        while not user_input.isnumeric() or int(user_input) > len(elem_list) or int(user_input) < 1:
            user_input = input()
        swipe_area = elem_list[int(user_input) - 1].bbox
        controller.swipe(swipe_area[0], swipe_area[1], swipe_dir)
        record_file.write(f"swipe({int(user_input)}:sep:{swipe_dir}):::{elem_list[int(user_input) - 1].uid}\n")
    elif user_input.lower() == "stop":
        record_file.write("stop\n")
        record_file.close()
        break
    else:
        break
    time.sleep(3)

print_with_color(f"Demonstration phase completed. {step} steps were recorded.", "yellow")
