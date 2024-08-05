import argparse
import datetime
import os
import time

from scripts.utils import print_with_color

arg_desc = "AppAgent - exploration phase"
parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=arg_desc)
parser.add_argument("--app")
parser.add_argument("--root_dir", default="./")
parser.add_argument("--url")  
parser.add_argument("--password", type=str, required=None, help="Figma prototype password (optional)")

args = vars(parser.parse_args())

app = args["app"]
root_dir = args["root_dir"]
url = args["url"]  
password = args["password"]

print_with_color("Welcome to the exploration phase of AppAgent!\nThe exploration phase aims at generating "
                 "documentations for UI elements through either autonomous exploration or human demonstration. "
                 "Both options are task-oriented, which means you need to give a task description. During "
                 "autonomous exploration, the agent will try to complete the task by interacting with possible "
                 "elements on the UI within limited rounds. Documentations will be generated during the process of "
                 "interacting with the correct elements to proceed with the task. Human demonstration relies on "
                 "the user to show the agent how to complete the given task, and the agent will generate "
                 "documentations for the elements interacted during the human demo. To start, please enter the "
                 "main interface of the app on your phone.", "yellow")
print_with_color("Choose from the following modes:\n1. autonomous exploration (Android)\n2. human demonstration (Android)\n"
                 "3. autonomous exploration (Figma ProtoType)\n", "blue")
user_input = ""
while user_input not in ["1", "2", "3"]:
    user_input = input()

if not app and user_input in ["1", "2"]:
    print_with_color("What is the name of the target app?", "blue")
    app = input()
    app = app.replace(" ", "")

if user_input == "1":
    os.system(f"python scripts/self_explorer.py --app {app} --root_dir {root_dir}")
elif user_input == "2":
    demo_timestamp = int(time.time())
    demo_name = datetime.datetime.fromtimestamp(demo_timestamp).strftime(f"demo_{app}_%Y-%m-%d_%H-%M-%S")
    os.system(f"python scripts/step_recorder.py --app {app} --demo {demo_name} --root_dir {root_dir}")
    os.system(f"python scripts/document_generation.py --app {app} --demo {demo_name} --root_dir {root_dir}")
elif user_input == "3":
    print_with_color("Choose the exploration mode for Figma ProtoType:\n1. Standalone\n2. With Flask server", "blue")
    figma_mode = ""
    while figma_mode not in ["1", "2"]:
        figma_mode = input()
    
    if figma_mode == "1":

        print_with_color("What is the name of the target app?", "blue")
        app = input()
        app = app.replace(" ", "")

        print_with_color("What is the Figma ProtoType URL?", "blue")
        url = input()
        url = url.strip()
        # If password is not provided, prompt the user for it
        if password is None:
            print_with_color("If the Figma prototype is password-protected, please enter the password. If not, just press Enter:", "blue")
            password = input()
        
        if password:
            os.system(f'python scripts/self_explorer_figma.py --app {app} --url "{url}" --root_dir {root_dir} --password "{password}"')  
        else:
            os.system(f'python scripts/self_explorer_figma.py --app {app} --url "{url}" --root_dir {root_dir}')
    elif figma_mode == "2":
        os.system(f"python scripts/self_explorer_server.py")
    
    