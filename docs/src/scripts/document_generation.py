import argparse
import ast
import json
import os
import re
import sys
import time

import prompts
from config import load_config
from model import ask_gpt4v
from utils import print_with_color, encode_image

arg_desc = "AppAgent - Human Demonstration"
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=arg_desc)
parser.add_argument("--app", required=True)
parser.add_argument("--demo", required=True)
parser.add_argument("--root_dir", default="./")
args = vars(parser.parse_args())

configs = load_config()

root_dir = args["root_dir"]
work_dir = os.path.join(root_dir, "apps")
if not os.path.exists(work_dir):
    os.mkdir(work_dir)
app = args["app"]
work_dir = os.path.join(work_dir, app)
demo_dir = os.path.join(work_dir, "demos")
demo_name = args["demo"]
task_dir = os.path.join(demo_dir, demo_name)
xml_dir = os.path.join(task_dir, "xml")
labeled_ss_dir = os.path.join(task_dir, "labeled_screenshots")
record_path = os.path.join(task_dir, "record.txt")
task_desc_path = os.path.join(task_dir, "task_desc.txt")
if not os.path.exists(task_dir) or not os.path.exists(xml_dir) or not os.path.exists(labeled_ss_dir) \
        or not os.path.exists(record_path) or not os.path.exists(task_desc_path):
    sys.exit()
log_path = os.path.join(task_dir, f"log_{app}_{demo_name}.txt")

docs_dir = os.path.join(work_dir, "demo_docs")
if not os.path.exists(docs_dir):
    os.mkdir(docs_dir)

print_with_color(f"Starting to generate documentations for the app {app} based on the demo {demo_name}", "yellow")
doc_count = 0
with open(record_path, "r") as infile:
    step = len(infile.readlines()) - 1
    infile.seek(0)
    for i in range(1, step + 1):
        img_before = encode_image(os.path.join(labeled_ss_dir, f"{demo_name}_{i}.png"))
        img_after = encode_image(os.path.join(labeled_ss_dir, f"{demo_name}_{i + 1}.png"))
        rec = infile.readline().strip()
        action, resource_id = rec.split(":::")
        action_type = action.split("(")[0]
        action_param = re.findall(r"\((.*?)\)", action)[0]
        if action_type == "tap":
            prompt_template = prompts.tap_doc_template
            prompt = re.sub(r"<ui_element>", action_param, prompt_template)
        elif action_type == "text":
            input_area, input_text = action_param.split(":sep:")
            prompt_template = prompts.text_doc_template
            prompt = re.sub(r"<ui_element>", input_area, prompt_template)
        elif action_type == "long_press":
            prompt_template = prompts.long_press_doc_template
            prompt = re.sub(r"<ui_element>", action_param, prompt_template)
        elif action_type == "swipe":
            swipe_area, swipe_dir = action_param.split(":sep:")
            if swipe_dir == "up" or swipe_dir == "down":
                action_type = "v_swipe"
            elif swipe_dir == "left" or swipe_dir == "right":
                action_type = "h_swipe"
            prompt_template = prompts.swipe_doc_template
            prompt = re.sub(r"<swipe_dir>", swipe_dir, prompt_template)
            prompt = re.sub(r"<ui_element>", swipe_area, prompt)
        else:
            break
        task_desc = open(task_desc_path, "r").read()
        prompt = re.sub(r"<task_desc>", task_desc, prompt)

        doc_name = resource_id + ".txt"
        doc_path = os.path.join(docs_dir, doc_name)

        if os.path.exists(doc_path):
            doc_content = ast.literal_eval(open(doc_path).read())
            if doc_content[action_type]:
                if configs["DOC_REFINE"]:
                    suffix = re.sub(r"<old_doc>", doc_content[action_type], prompts.refine_doc_suffix)
                    prompt += suffix
                    print_with_color(f"Documentation for the element {resource_id} already exists. The doc will be "
                                     f"refined based on the latest demo.", "yellow")
                else:
                    print_with_color(f"Documentation for the element {resource_id} already exists. Turn on DOC_REFINE "
                                     f"in the config file if needed.", "yellow")
                    continue
        else:
            doc_content = {
                "tap": "",
                "text": "",
                "v_swipe": "",
                "h_swipe": "",
                "long_press": ""
            }

        print_with_color(f"Waiting for GPT-4V to generate documentation for the element {resource_id}", "yellow")
        content = [
            {
                "type": "text",
                "text": prompt
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{img_before}"
                }
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{img_after}"
                }
            }
        ]

        rsp = ask_gpt4v(content)
        if "error" not in rsp:
            msg = rsp["choices"][0]["message"]["content"]
            doc_content[action_type] = msg
            with open(log_path, "a") as logfile:
                log_item = {"step": i, "prompt": prompt, "image_before": f"{demo_name}_{i}.png",
                            "image_after": f"{demo_name}_{i + 1}.png", "response": rsp}
                logfile.write(json.dumps(log_item) + "\n")
            with open(doc_path, "w") as outfile:
                outfile.write(str(doc_content))
            doc_count += 1
            print_with_color(f"Documentation generated and saved to {doc_path}", "yellow")
        else:
            print_with_color(rsp["error"]["message"], "red")
        time.sleep(configs["REQUEST_INTERVAL"])

print_with_color(f"Documentation generation phase completed. {doc_count} docs generated.", "yellow")
