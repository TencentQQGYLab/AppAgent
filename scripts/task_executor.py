import argparse
import ast
import datetime
import json
import os
import re
import sys
import time

import prompts
from config import load_config
from and_controller import list_all_devices, AndroidController, traverse_tree
from model import ask_gpt4v, parse_explore_rsp
from utils import print_with_color, draw_bbox_multi, encode_image

arg_desc = "AppAgent Executor"
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=arg_desc)
parser.add_argument("--app")
parser.add_argument("--root_dir", default="./")
args = vars(parser.parse_args())

configs = load_config()

app = args["app"]
root_dir = args["root_dir"]

if not app:
    print_with_color("What is the name of the app you want me to operate?", "blue")
    app = input()
    app = app.replace(" ", "")

app_dir = os.path.join(os.path.join(root_dir, "apps"), app)
work_dir = os.path.join(root_dir, "tasks")
if not os.path.exists(work_dir):
    os.mkdir(work_dir)
auto_docs_dir = os.path.join(app_dir, "auto_docs")
demo_docs_dir = os.path.join(app_dir, "demo_docs")
task_timestamp = int(time.time())
dir_name = datetime.datetime.fromtimestamp(task_timestamp).strftime(f"task_{app}_%Y-%m-%d_%H-%M-%S")
task_dir = os.path.join(work_dir, dir_name)
os.mkdir(task_dir)
log_path = os.path.join(task_dir, f"log_{app}_{dir_name}.txt")

no_doc = False
if not os.path.exists(auto_docs_dir) and not os.path.exists(demo_docs_dir):
    print_with_color(f"No documentations found for the app {app}. Do you want to proceed with no docs? Enter y or n",
                     "red")
    user_input = ""
    while user_input != "y" and user_input != "n":
        user_input = input().lower()
    if user_input == "y":
        no_doc = True
    else:
        sys.exit()
elif os.path.exists(auto_docs_dir) and os.path.exists(demo_docs_dir):
    print_with_color(f"The app {app} has documentations generated from both autonomous exploration and human "
                     f"demonstration. Which one do you want to use? Type 1 or 2.\n1. Autonomous exploration\n2. Human "
                     f"Demonstration",
                     "blue")
    user_input = ""
    while user_input != "1" and user_input != "2":
        user_input = input()
    if user_input == "1":
        docs_dir = auto_docs_dir
    else:
        docs_dir = demo_docs_dir
elif os.path.exists(auto_docs_dir):
    print_with_color(f"Documentations generated from autonomous exploration were found for the app {app}. The doc base "
                     f"is selected automatically.", "yellow")
    docs_dir = auto_docs_dir
else:
    print_with_color(f"Documentations generated from human demonstration were found for the app {app}. The doc base is "
                     f"selected automatically.", "yellow")
    docs_dir = demo_docs_dir

device_list = list_all_devices()
if not device_list:
    print_with_color("ERROR: No device found!", "red")
    sys.exit()
print_with_color(f"List of devices attached:\n{str(device_list)}", "yellow")
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

print_with_color("Please enter the description of the task you want me to complete in a few sentences:", "blue")
task_desc = input()

round_count = 0
last_act = "None"
task_complete = False
while round_count < configs["MAX_ROUNDS"]:
    round_count += 1
    print_with_color(f"Round {round_count}", "yellow")
    screenshot_path = controller.get_screenshot(f"{dir_name}_{round_count}", task_dir)
    xml_path = controller.get_xml(f"{dir_name}_{round_count}", task_dir)
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
    labeled_img = draw_bbox_multi(screenshot_path, os.path.join(task_dir, f"{dir_name}_{round_count}_labeled.png"),
                                  elem_list, dark_mode=configs["DARK_MODE"])
    if no_doc:
        prompt = prompts.self_explore_task_template
    else:
        ui_doc = ""
        for i, elem in enumerate(elem_list):
            doc_path = os.path.join(docs_dir, f"{elem.uid}.txt")
            if not os.path.exists(doc_path):
                continue
            ui_doc += f"Documentation of UI element labeled with the numeric tag '{i + 1}':\n"
            doc_content = ast.literal_eval(open(doc_path, "r").read())
            if doc_content["tap"]:
                ui_doc += f"This UI element is clickable. {doc_content['tap']}\n\n"
            if doc_content["text"]:
                ui_doc += f"This UI element can receive text input. The text input is used for the following " \
                          f"purposes: {doc_content['text']}\n\n"
            if doc_content["long_press"]:
                ui_doc += f"This UI element is long clickable. {doc_content['long_press']}\n\n"
            if doc_content["v_swipe"]:
                ui_doc += f"This element can be swiped directly without tapping. You can swipe vertically on this " \
                          f"UI element. {doc_content['v_swipe']}\n\n"
            if doc_content["h_swipe"]:
                ui_doc += f"This element can be swiped directly without tapping. You can swipe horizontally on this " \
                          f"UI element. {doc_content['h_swipe']}\n\n"
        print_with_color(f"Documentations retrieved for the current interface:\n{ui_doc}", "magenta")
        prompt = re.sub(r"<ui_document>", ui_doc, prompts.task_template)
    prompt = re.sub(r"<task_description>", task_desc, prompt)
    prompt = re.sub(r"<last_act>", last_act, prompt)
    base64_img = encode_image(os.path.join(task_dir, f"{dir_name}_{round_count}_labeled.png"))
    content = [
        {
            "type": "text",
            "text": prompt
        },
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_img}"
            }
        }
    ]
    print_with_color("Thinking about what to do in the next step...", "yellow")
    rsp = ask_gpt4v(content)

    if "error" not in rsp:
        with open(log_path, "a") as logfile:
            log_item = {"step": round_count, "prompt": prompt, "image": f"{dir_name}_{round_count}_labeled.png",
                        "response": rsp}
            logfile.write(json.dumps(log_item) + "\n")
        res = parse_explore_rsp(rsp)
        act_name = res[0]
        if act_name == "FINISH":
            task_complete = True
            break
        if act_name == "ERROR":
            break
        last_act = res[-1]
        res = res[:-1]
        if act_name == "tap":
            _, area = res
            tl, br = elem_list[area - 1].bbox
            ret = controller.tap(tl, br)
            if ret == "ERROR":
                print_with_color("ERROR: tap execution failed", "red")
                break
        elif act_name == "text":
            _, input_str = res
            ret = controller.text(input_str)
            if ret == "ERROR":
                print_with_color("ERROR: text execution failed", "red")
                break
        elif act_name == "long_press":
            _, area = res
            tl, br = elem_list[area - 1].bbox
            ret = controller.long_press(tl, br)
            if ret == "ERROR":
                print_with_color("ERROR: long press execution failed", "red")
                break
        elif act_name == "swipe":
            _, area, swipe_dir, dist = res
            tl, br = elem_list[area - 1].bbox
            ret = controller.swipe(tl, br, swipe_dir, dist)
            if ret == "ERROR":
                print_with_color("ERROR: long press execution failed", "red")
                break
        time.sleep(configs["REQUEST_INTERVAL"])
    else:
        print_with_color(rsp["error"]["message"], "red")
        break

if task_complete:
    print_with_color("Task completed successfully", "yellow")
elif round_count == configs["MAX_ROUNDS"]:
    print_with_color("Task finished due to reaching max rounds", "yellow")
else:
    print_with_color("Task finished unexpectedly", "red")
