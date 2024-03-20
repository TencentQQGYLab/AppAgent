# Import necessary libraries
import argparse
import ast
import datetime
import json
import os
import re
import sys
import time

# Import custom modules
import prompts
from config import load_config
from and_controller import list_all_devices, AndroidController, traverse_tree
from model import ask_gpt4v, parse_explore_rsp, parse_reflect_rsp
from utils import print_with_color, draw_bbox_multi, encode_image

# Set up argument parser
arg_desc = "AppAgent - Autonomous Exploration"
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=arg_desc)
parser.add_argument("--app")
parser.add_argument("--root_dir", default="./")
args = vars(parser.parse_args())

# Load configurations
configs = load_config()

# Get app name and root directory from arguments
app = args["app"]
root_dir = args["root_dir"]

# If app name is not provided, ask user for input
if not app:
    print_with_color("What is the name of the target app?", "blue")
    app = input()
    app = app.replace(" ", "")

# Set up working directories
work_dir = os.path.join(root_dir, "apps")
if not os.path.exists(work_dir):
    os.mkdir(work_dir)
work_dir = os.path.join(work_dir, app)
if not os.path.exists(work_dir):
    os.mkdir(work_dir)
demo_dir = os.path.join(work_dir, "demos")
if not os.path.exists(demo_dir):
    os.mkdir(demo_dir)
demo_timestamp = int(time.time())
task_name = datetime.datetime.fromtimestamp(demo_timestamp).strftime("self_explore_%Y-%m-%d_%H-%M-%S")
task_dir = os.path.join(demo_dir, task_name)
os.mkdir(task_dir)
docs_dir = os.path.join(work_dir, "auto_docs")
if not os.path.exists(docs_dir):
    os.mkdir(docs_dir)
explore_log_path = os.path.join(task_dir, f"log_explore_{task_name}.txt")
reflect_log_path = os.path.join(task_dir, f"log_reflect_{task_name}.txt")

# Get list of connected Android devices
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

# Ask user for task description
print_with_color("Please enter the description of the task you want me to complete in a few sentences:", "blue")
task_desc = input()

# Initialize variables for exploration loop
round_count = 0
doc_count = 0
useless_list = set()
last_act = "None"
task_complete = False

# Start exploration loop
while round_count < configs["MAX_ROUNDS"]:
    # Code for each round of exploration
    # This includes taking screenshots, getting XML, identifying clickable and focusable elements, 
    # asking GPT-4 for next action, executing the action, reflecting on the action, and generating documentation

# Print final status of exploration
if task_complete:
    print_with_color(f"Autonomous exploration completed successfully. {doc_count} docs generated.", "yellow")
elif round_count == configs["MAX_ROUNDS"]:
    print_with_color(f"Autonomous exploration finished due to reaching max rounds. {doc_count} docs generated.",
                     "yellow")
else:
    print_with_color(f"Autonomous exploration finished unexpectedly. {doc_count} docs generated.", "red")