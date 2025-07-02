"""
Main runner for specialized agents
"""
import argparse
import os
import sys
import datetime
import time

from scripts.config import load_config
from scripts.and_controller import list_all_devices, AndroidController
from scripts.model import OpenAIModel, QwenModel
from scripts.utils import print_with_color
from agents.captcha_agent import CaptchaAgent
# Future imports:
# from agents.payment_agent import PaymentAgent
# from agents.quiz_agent import QuizAgent


def select_agent_type():
    """Let user select which type of agent to use"""
    print_with_color("=" * 50, "cyan")
    print_with_color("AppAgent - Specialized Agent Runner", "cyan")
    print_with_color("=" * 50, "cyan")
    
    print_with_color("\nSelect the type of agent you want to use:", "blue")
    print_with_color("1. CAPTCHA Agent - Handles various types of CAPTCHAs", "yellow")
    print_with_color("2. Payment Agent - Handles payment processes (Coming soon)", "gray")
    print_with_color("3. Quiz Agent - Handles quiz and questionnaire (Coming soon)", "gray")
    print_with_color("4. General Agent - Original AppAgent for general tasks", "yellow")
    
    while True:
        choice = input("\nEnter your choice (1-4): ").strip()
        if choice in ["1", "2", "3", "4"]:
            return choice
        print_with_color("Invalid choice. Please enter 1-4.", "red")


def initialize_model(configs):
    """Initialize the language model based on config"""
    if configs["MODEL"] == "OpenAI":
        return OpenAIModel(
            base_url=configs["OPENAI_API_BASE"],
            api_key=configs["OPENAI_API_KEY"],
            model=configs["OPENAI_API_MODEL"],
            temperature=configs["TEMPERATURE"],
            max_tokens=configs["MAX_TOKENS"]
        )
    elif configs["MODEL"] == "Qwen":
        return QwenModel(
            api_key=configs["DASHSCOPE_API_KEY"],
            model=configs["QWEN_MODEL"]
        )
    else:
        print_with_color(f"ERROR: Unsupported model type {configs['MODEL']}!", "red")
        sys.exit()


def setup_device():
    """Setup Android device connection"""
    device_list = list_all_devices()
    if not device_list:
        print_with_color("ERROR: No device found!", "red")
        sys.exit()
    
    print_with_color(f"\nList of devices attached:\n{str(device_list)}", "yellow")
    
    if len(device_list) == 1:
        device = device_list[0]
        print_with_color(f"Device selected: {device}", "yellow")
    else:
        print_with_color("Please choose the Android device by entering its ID:", "blue")
        device = input().strip()
    
    controller = AndroidController(device)
    width, height = controller.get_device_size()
    
    if not width or not height:
        print_with_color("ERROR: Invalid device size!", "red")
        sys.exit()
    
    print_with_color(f"Screen resolution of {device}: {width}x{height}", "yellow")
    return controller


def run_captcha_agent(controller, model, configs, work_dir):
    """Run the CAPTCHA agent"""
    print_with_color("\n=== CAPTCHA Agent ===", "cyan")
    print_with_color("This agent specializes in solving various types of CAPTCHAs.", "yellow")
    print_with_color("Supported types: Image text, Slider, Click selection, Rotation", "yellow")
    
    print_with_color("\nPlease navigate to the screen with the CAPTCHA.", "blue")
    input("Press Enter when ready...")
    
    # Create work directory
    task_dir = os.path.join(work_dir, f"captcha_{int(time.time())}")
    os.makedirs(task_dir, exist_ok=True)
    
    # Initialize agent
    agent = CaptchaAgent(controller, model, configs, task_dir)
    
    # Run the agent
    task_desc = "Solve the CAPTCHA on the screen"
    success = agent.run_task(task_desc)
    
    if success:
        print_with_color("\n✓ CAPTCHA solved successfully!", "green")
    else:
        print_with_color("\n✗ Failed to solve CAPTCHA", "red")
    
    return success


def run_general_agent(app_name):
    """Run the original general AppAgent"""
    print_with_color("\nRunning general AppAgent...", "yellow")
    # This calls the original run.py functionality
    os.system(f"python run.py --app {app_name}")


def main():
    parser = argparse.ArgumentParser(description="AppAgent - Specialized Agent Runner")
    parser.add_argument("--app", help="App name (optional)")
    parser.add_argument("--agent", help="Agent type: captcha, payment, quiz, general")
    parser.add_argument("--root_dir", default="./", help="Root directory")
    args = parser.parse_args()
    
    # Load configurations
    configs = load_config()
    
    # Select agent type
    if args.agent:
        agent_map = {"captcha": "1", "payment": "2", "quiz": "3", "general": "4"}
        agent_choice = agent_map.get(args.agent.lower(), "4")
    else:
        agent_choice = select_agent_type()
    
    # Handle general agent separately
    if agent_choice == "4":
        app_name = args.app or input("\nEnter app name: ").strip()
        run_general_agent(app_name)
        return
    
    # Setup device and model for specialized agents
    controller = setup_device()
    model = initialize_model(configs)
    
    # Create work directory
    work_dir = os.path.join(args.root_dir, "agent_tasks")
    os.makedirs(work_dir, exist_ok=True)
    
    # Run selected agent
    if agent_choice == "1":
        run_captcha_agent(controller, model, configs, work_dir)
    elif agent_choice == "2":
        print_with_color("\nPayment Agent is coming soon!", "yellow")
        # run_payment_agent(controller, model, configs, work_dir)
    elif agent_choice == "3":
        print_with_color("\nQuiz Agent is coming soon!", "yellow")
        # run_quiz_agent(controller, model, configs, work_dir)
    
    print_with_color("\nAgent task completed.", "cyan")


if __name__ == "__main__":
    main()