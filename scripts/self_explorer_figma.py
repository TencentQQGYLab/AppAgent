import argparse
import datetime
import time
import re
import json
import os
import requests
import sys
import ast

from config import load_config
from utils import print_with_color, draw_bbox_multi
from urllib.parse import unquote
from figma_controller import (
    SeleniumController,
    UIElement,
    find_node_by_id,
    append_to_log,
)

import prompts
from model import (
    parse_explore_rsp,
    parse_reflect_rsp,
    OpenAIModel,
    QwenModel,
    AzureModel,
)

configs = load_config()

if configs["MODEL"] == "OpenAI":
    mllm = OpenAIModel(
        base_url=configs["OPENAI_API_BASE"],
        api_key=configs["OPENAI_API_KEY"],
        model=configs["OPENAI_API_MODEL"],
        temperature=configs["TEMPERATURE"],
        max_tokens=configs["MAX_TOKENS"],
    )
elif configs["MODEL"] == "Qwen":
    mllm = QwenModel(api_key=configs["DASHSCOPE_API_KEY"], model=configs["QWEN_MODEL"])
elif configs["MODEL"] == "Azure":
    mllm = AzureModel(
        base_url=configs["OPENAI_API_BASE"],
        api_key=configs["OPENAI_API_KEY"],
        model=configs["OPENAI_API_MODEL"],
        temperature=configs["TEMPERATURE"],
        max_tokens=configs["MAX_TOKENS"],
    )
else:
    print_with_color(f"ERROR: Unsupported model type {configs['MODEL']}!", "red")
    sys.exit()


def get_figma_file_data(file_key, token, root_dir):
    data_path = os.path.join(root_dir, f"{file_key}.json")
    if os.path.exists(data_path):
        with open(data_path, "r") as f:
            return json.load(f)
    else:
        response = requests.get(
            f"https://api.figma.com/v1/files/{file_key}",
            headers={"X-Figma-Token": token},
        )
        if response.status_code == 200:
            file = response.json()
            with open(data_path, "w") as f:
                json.dump(file, f)
            return file
        else:
            print_with_color(
                f"ERROR: Failed to get file data from Figma API. Status code: {response.status_code}",
                "red",
            )
            sys.exit(1)


def init_exploration(app, url, password, root_dir):
    try:
        # Set variable values
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
        task_name = datetime.datetime.fromtimestamp(demo_timestamp).strftime(
            "self_explore_%Y-%m-%d_%H-%M-%S"
        )
        task_dir = os.path.join(demo_dir, task_name)
        os.mkdir(task_dir)
        docs_dir = os.path.join(work_dir, "auto_docs")
        if not os.path.exists(docs_dir):
            os.mkdir(docs_dir)
        explore_log_path = os.path.join(task_dir, f"log_explore_{task_name}.txt")
        reflect_log_path = os.path.join(task_dir, f"log_reflect_{task_name}.txt")
        report_log_path = os.path.join(task_dir, f"log_report_{task_name}.md")

        # Get Figma file data
        token = configs["FIGMA_ACCESS_TOKEN"]
        file_key = re.search(r"/(file|proto)/(.*?)/", url).group(2)
        starting_point_node_id_match = re.search(
            r"starting-point-node-id=(.*?)(?:&|$)", url
        )
        if starting_point_node_id_match is None:
            print_with_color(
                "ERROR: Failed to extract starting-point-node-id from the URL", "red"
            )
            sys.exit(1)

        starting_point_node_id = unquote(starting_point_node_id_match.group(1))
        file = get_figma_file_data(file_key, token, root_dir)

        starting_point_node = find_node_by_id(
            starting_point_node_id, file["document"]["children"]
        )

        if starting_point_node is None:
            print_with_color("ERROR: Failed to find the starting point node!", "red")
            sys.exit(1)

        width = int(starting_point_node["absoluteBoundingBox"]["width"])
        height = int(starting_point_node["absoluteBoundingBox"]["height"])

        print_with_color(f"Screen resolution: {width}x{height}", "yellow")

        # Create a SeleniumController object
        selenium_controller = SeleniumController(url, password)

        # Open Chrome browser and navigate to the URL
        selenium_controller.execute_selenium()

        # Get the size of the <canvas> element
        canvas_width, canvas_height = selenium_controller.get_canvas_size()

        # Calculate the position of the device image
        x, y = selenium_controller.calculate_position(
            width, height, canvas_width, canvas_height
        )

        # Print the adjusted width, height, x, and y values
        print_with_color(f"Bounding box: {x, y, width, height}", "yellow")

        return {
            "app": app,
            "task_name": task_name,
            "task_dir": task_dir,
            "docs_dir": docs_dir,
            "explore_log_path": explore_log_path,
            "reflect_log_path": reflect_log_path,
            "report_log_path": report_log_path,
            "file": file,
            "selenium_controller": selenium_controller,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
        }
    except Exception as e:
        error_message = f"Error during initialization: {str(e)}"
        print_with_color(error_message, "red")
        return {"status": "error", "message": error_message}


def run_exploration(init_data, task_desc, persona_desc, stop_event=None, server=False):
    try:
        app = init_data["app"]
        task_name = init_data["task_name"]
        task_dir = init_data["task_dir"]
        docs_dir = init_data["docs_dir"]
        explore_log_path = init_data["explore_log_path"]
        reflect_log_path = init_data["reflect_log_path"]
        report_log_path = init_data["report_log_path"]
        file = init_data["file"]
        selenium_controller = init_data["selenium_controller"]
        x, y, width, height = (
            init_data["x"],
            init_data["y"],
            init_data["width"],
            init_data["height"],
        )

        # Get the task description from the user
        if not task_desc:
            print_with_color(
                "Please enter the description of the task you want me to complete in a few sentences:",
                "blue",
            )
            task_desc = input()
        else:
            print_with_color(
                f"Task description provided: {task_desc}",
                "yellow",
            )

        if not persona_desc and server is False:
            print_with_color(
                "(Optional) Please enter the description of the user persona you'd like me to emulate : ",
                "blue",
            )
            persona_desc = input()

        round_count = 0
        doc_count = 0
        useless_list = set()
        last_act = "None"
        task_complete = False

        # Write the report markdown file
        append_to_log(f"# User Testing Report for {app}", report_log_path)
        append_to_log(task_name, report_log_path)
        append_to_log(f"## Task Description", report_log_path)
        append_to_log(task_desc, report_log_path)

        # If the user entered a persona description, replace the placeholder with the description
        if persona_desc:
            persona_desc = f"as a person who is {persona_desc}"
            append_to_log(f"## Persona Description", report_log_path)
            append_to_log(persona_desc, report_log_path)

        prompt = re.sub(
            r"<persona_description>",
            persona_desc,
            prompts.self_explore_task_with_persona_template,
        )

        while round_count < configs["MAX_ROUNDS"]:
            if stop_event and stop_event.is_set():
                print_with_color("Exploration stopped by user request", "yellow")
                break

            round_count += 1
            print_with_color(
                f"Round {round_count}",
                "yellow",
                log_file=report_log_path,
                heading_level=2,
            )

            # Take a screenshot
            screenshot_before = os.path.join(task_dir, f"{round_count}_before.png")
            selenium_controller.take_screenshot(x, y, width, height, screenshot_before)

            screenshot_before_url = f"{round_count}_before.png"

            append_to_log(
                f"![Before action]({screenshot_before_url})",
                report_log_path,
                break_line=False,
            )

            # find Current node id from the URL and get its node data
            current_node_id = selenium_controller.get_current_node_id()
            node_data = find_node_by_id(current_node_id, file["document"]["children"])

            # Save the node data to the task directory
            node_data_path = os.path.join(task_dir, f"{round_count}.json")
            with open(node_data_path, "w") as f:
                json.dump(node_data, f)

            # Create a list of UI elements
            elem_list = []
            for elem in UIElement.process_node_data(node_data):
                if elem.uid in useless_list:
                    continue
                elem_list.append(elem)

            # Draw bounding boxes on the image
            output_path = os.path.join(task_dir, f"{round_count}_before_labeled.png")
            draw_bbox_multi(
                screenshot_before,
                output_path,
                elem_list,
                width,
                height,
                dark_mode=configs["DARK_MODE"],
            )

            output_url = f"{round_count}_before_labeled.png"

            append_to_log(
                f"![Before action labeled]({output_url})",
                report_log_path,
            )

            prompt = re.sub(
                r"<task_description>",
                task_desc,
                prompts.self_explore_task_with_persona_template,
            )
            prompt = re.sub(r"<last_act>", last_act, prompt)
            base64_img_before = os.path.join(
                task_dir, f"{round_count}_before_labeled.png"
            )
            print_with_color("Thinking about what to do in the next step...", "yellow")
            status, rsp = mllm.get_model_response(prompt, [base64_img_before])

            if status:
                with open(explore_log_path, "a") as logfile:
                    log_item = {
                        "step": round_count,
                        "prompt": prompt,
                        "image": f"{round_count}_before_labeled.png",
                        "response": rsp,
                    }
                    logfile.write(json.dumps(log_item) + "\n")

                res = parse_explore_rsp(rsp, log_file=report_log_path)
                act_name = res[0]
                last_act = res[-1]
                res = res[:-1]
                if act_name == "FINISH":
                    task_complete = True
                    break
                if act_name in ["tap", "long_press", "swipe"]:
                    _, area = res
                    tl, br = elem_list[area - 1].bbox

                    # Calculate the center of the element
                    center_x = (tl[0] + br[0]) / 2
                    center_y = (tl[1] + br[1]) / 2

                    # Add the x and y values to the center coordinates
                    center_x += x
                    center_y += y

                    # Draw a bounding box on the canvas image and save it
                    screenshot_before_actioned = os.path.join(
                        task_dir, f"{round_count}_before_labeled_action.png"
                    )
                    selenium_controller.take_canvas_screenshot(
                        screenshot_before, tl, br, screenshot_before_actioned
                    )

                    if act_name == "tap":
                        selenium_controller.draw_circle(
                            center_x, center_y, screenshot_before_actioned
                        )
                        ret = selenium_controller.tap(center_x, center_y)
                        if ret == "ERROR":
                            print_with_color("ERROR: tap execution failed", "red")
                            break
                    elif act_name == "long_press":
                        selenium_controller.draw_circle(
                            center_x, center_y, screenshot_before_actioned
                        )
                        ret = selenium_controller.long_press(center_x, center_y)
                        if ret == "ERROR":
                            print_with_color(
                                "ERROR: long press execution failed", "red"
                            )
                            break
                    elif act_name == "swipe":
                        _, swipe_dir, dist = res
                        selenium_controller.draw_arrow(
                            center_x,
                            center_y,
                            swipe_dir,
                            dist,
                            screenshot_before_actioned,
                        )
                        ret = selenium_controller.swipe(
                            center_x, center_y, swipe_dir, dist
                        )
                        if ret == "ERROR":
                            print_with_color("ERROR: swipe execution failed", "red")
                            break

                    # Add the actioned image to the report markdown file
                    screenshot_before_actioned_url = (
                        f"{round_count}_before_labeled_action.png"
                    )

                    append_to_log(
                        f"![Before action labeled actioned]({screenshot_before_actioned_url})",
                        report_log_path,
                    )
                else:
                    break
                time.sleep(configs["REQUEST_INTERVAL"])
            else:
                print_with_color(rsp, "red")
                break

            # Take a screenshot
            screenshot_after = os.path.join(task_dir, f"{round_count}_after.png")
            selenium_controller.take_screenshot(x, y, width, height, screenshot_after)

            draw_bbox_multi(
                screenshot_after,
                os.path.join(task_dir, f"{round_count}_after_labeled.png"),
                elem_list,
                width,
                height,
                dark_mode=configs["DARK_MODE"],
            )

            base64_img_after = os.path.join(
                task_dir, f"{round_count}_after_labeled.png"
            )

            if act_name == "tap":
                prompt = re.sub(
                    r"<action>",
                    "tapping",
                    prompts.self_explore_reflect_with_persona_template,
                )
            elif act_name == "text":
                continue
            elif act_name == "long_press":
                prompt = re.sub(
                    r"<action>",
                    "long pressing",
                    prompts.self_explore_reflect_with_persona_template,
                )
            elif act_name == "swipe":
                swipe_dir = res[2]
                if swipe_dir == "up" or swipe_dir == "down":
                    act_name = "v_swipe"
                elif swipe_dir == "left" or swipe_dir == "right":
                    act_name = "h_swipe"
                prompt = re.sub(
                    r"<action>",
                    "swiping",
                    prompts.self_explore_reflect_with_persona_template,
                )
            else:
                print_with_color("ERROR: Undefined act!", "red")
                break
            prompt = re.sub(r"<ui_element>", str(area), prompt)
            prompt = re.sub(r"<task_desc>", task_desc, prompt)
            prompt = re.sub(r"<last_act>", last_act, prompt)

            print_with_color("Reflecting on my previous action...", "yellow")
            status, rsp = mllm.get_model_response(
                prompt, [base64_img_before, base64_img_after]
            )

            if status:
                resource_id = elem_list[int(area) - 1].uid
                with open(reflect_log_path, "a") as logfile:
                    log_item = {
                        "step": round_count,
                        "prompt": prompt,
                        "image_before": f"{round_count}_before_labeled.png",
                        "image_after": f"{round_count}_after.png",
                        "response": rsp,
                    }
                    logfile.write(json.dumps(log_item) + "\n")
                res = parse_reflect_rsp(rsp, log_file=report_log_path)
                decision = res[0]
                if decision == "ERROR":
                    break
                if decision == "INEFFECTIVE":
                    useless_list.add(resource_id)
                    last_act = "None"
                elif (
                    decision == "BACK"
                    or decision == "CONTINUE"
                    or decision == "SUCCESS"
                ):
                    if decision == "BACK" or decision == "CONTINUE":
                        useless_list.add(resource_id)
                        last_act = "None"
                        if decision == "BACK":
                            ret = selenium_controller.back()
                            if ret == "ERROR":
                                print_with_color("ERROR: back execution failed", "red")
                                break
                    doc = res[-1]
                    doc_name = resource_id + ".txt"
                    doc_path = os.path.join(docs_dir, doc_name)
                    if os.path.exists(doc_path):
                        doc_content = ast.literal_eval(open(doc_path).read())
                        if doc_content[act_name]:
                            print_with_color(
                                f"Documentation for the element {resource_id} already exists.",
                                "yellow",
                            )
                            continue
                    else:
                        doc_content = {
                            "tap": "",
                            "text": "",
                            "v_swipe": "",
                            "h_swipe": "",
                            "long_press": "",
                        }
                    doc_content[act_name] = doc
                    with open(doc_path, "w") as outfile:
                        outfile.write(str(doc_content))
                    doc_count += 1
                    print_with_color(
                        f"Documentation generated and saved to {doc_path}", "yellow"
                    )
                else:
                    print_with_color(f"ERROR: Undefined decision! {decision}", "red")
                    break
            else:
                print_with_color(rsp["error"]["message"], "red")
                break

            time.sleep(configs["REQUEST_INTERVAL"])

        if task_complete:
            print_with_color(
                f"Autonomous exploration completed successfully. {doc_count} docs generated.",
                "yellow",
            )
        elif round_count == configs["MAX_ROUNDS"]:
            print_with_color(
                f"Autonomous exploration finished due to reaching max rounds. {doc_count} docs generated.",
                "yellow",
            )
        else:
            print_with_color(
                f"Autonomous exploration finished unexpectedly. {doc_count} docs generated.",
                "red",
            )

        # Check if the file exists and delete it
        if os.path.exists("data.json"):
            os.remove("data.json")
        else:
            print("The file does not exist")

        result = {
            "status": "success" if task_complete else "incomplete",
            "task_complete": task_complete,
            "rounds": round_count,
            "docs_generated": doc_count,
        }

        return result

    except Exception as e:
        error_message = f"Error during exploration: {str(e)}"
        print_with_color(error_message, "red")
        return {"status": "error", "message": error_message}


if __name__ == "__main__":
    arg_desc = "AppAgent - Autonomous Exploration for Figma"
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter, description=arg_desc
    )
    parser.add_argument("--app")
    parser.add_argument("--root_dir", default="./")
    parser.add_argument("--url")
    parser.add_argument(
        "--password", type=str, required=None, help="Figma prototype password"
    )
    parser.add_argument("--task_desc")
    parser.add_argument(
        "--persona_desc", default=None, help="Description of the user persona"
    )
    args = vars(parser.parse_args())

    app = args["app"].replace(" ", "") if args["app"] else None
    root_dir = args["root_dir"]
    url = args["url"]
    password = args["password"]
    task_desc = args["task_desc"].strip('"') if args["task_desc"] else None
    persona_desc = args["persona_desc"].strip('"') if args["persona_desc"] else None

    if not app:
        print_with_color("What is the name of the target app?", "blue")
        app = input()
        app = app.replace(" ", "")

    init_data = init_exploration(app, url, password, root_dir)
    if "status" in init_data and init_data["status"] == "error":
        print_with_color(f"Initialization failed: {init_data['message']}", "red")
    else:
        result = run_exploration(init_data, task_desc, persona_desc)
        print_with_color(f"Exploration result: {result}", "yellow")
