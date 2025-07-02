"""
Base Agent class that provides common functionality for all specialized agents
"""
import os
import time
from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any

from scripts.and_controller import AndroidController
from scripts.model import BaseModel
from scripts.utils import print_with_color, draw_bbox_multi


class BaseAgent(ABC):
    """Base class for all specialized agents"""
    
    def __init__(self, 
                 controller: AndroidController,
                 model: BaseModel,
                 config: Dict[str, Any],
                 work_dir: str):
        self.controller = controller
        self.model = model
        self.config = config
        self.work_dir = work_dir
        self.round_count = 0
        self.max_rounds = config.get("MAX_ROUNDS", 20)
        self.request_interval = config.get("REQUEST_INTERVAL", 10)
        
    @abstractmethod
    def get_task_prompt(self, task_desc: str, last_act: str, **kwargs) -> str:
        """Generate task-specific prompt"""
        pass
    
    @abstractmethod
    def parse_response(self, response: str) -> List[Any]:
        """Parse model response for specific task type"""
        pass
    
    @abstractmethod
    def execute_action(self, action: List[Any]) -> bool:
        """Execute the parsed action"""
        pass
    
    @abstractmethod
    def check_task_completion(self, screenshot_path: str, xml_path: str) -> bool:
        """Check if the specific task is completed"""
        pass
    
    def get_screenshot_and_xml(self, prefix: str, max_retries: int = 3) -> Tuple[str, str]:
        """Get screenshot and XML from device with retry mechanism"""
        for attempt in range(max_retries):
            if attempt > 0:
                print_with_color(f"Retrying... (attempt {attempt + 1}/{max_retries})", "yellow")
                time.sleep(2)  # Wait before retry
            
            screenshot_path = self.controller.get_screenshot(prefix, self.work_dir)
            xml_path = self.controller.get_xml(prefix, self.work_dir)
            
            # If both succeed, return them
            if screenshot_path != "ERROR" and xml_path != "ERROR":
                return screenshot_path, xml_path
            
            # If only one failed, try to get it again
            if screenshot_path == "ERROR" and xml_path != "ERROR":
                print_with_color("Retrying screenshot capture...", "yellow")
                screenshot_path = self.controller.get_screenshot(prefix + f"_retry{attempt}", self.work_dir)
            
            if xml_path == "ERROR" and screenshot_path != "ERROR":
                print_with_color("Retrying XML capture...", "yellow")
                xml_path = self.controller.get_xml(prefix + f"_retry{attempt}", self.work_dir)
            
            # Check again after retry
            if screenshot_path != "ERROR" and xml_path != "ERROR":
                return screenshot_path, xml_path
        
        # If we get here, all retries failed
        print_with_color(f"Failed to get screenshot or XML after {max_retries} attempts", "red")
        return screenshot_path, xml_path
    
    def wait_interval(self):
        """Wait between requests"""
        time.sleep(self.request_interval)
    
    def run_task(self, task_desc: str) -> bool:
        """Main task execution loop"""
        last_act = "None"
        task_complete = False
        
        while self.round_count < self.max_rounds and not task_complete:
            self.round_count += 1
            print_with_color(f"Round {self.round_count}", "yellow")
            
            # Get current state
            screenshot_path, xml_path = self.get_screenshot_and_xml(f"round_{self.round_count}")
            if screenshot_path == "ERROR" or xml_path == "ERROR":
                print_with_color("ERROR: Failed to get screenshot or XML", "red")
                
                # Provide diagnostic information
                if screenshot_path == "ERROR" and xml_path == "ERROR":
                    print_with_color("Both screenshot and XML capture failed.", "red")
                elif screenshot_path == "ERROR":
                    print_with_color("Screenshot capture failed, but XML was successful.", "red")
                else:
                    print_with_color("XML capture failed, but screenshot was successful.", "red")
                
                print_with_color("Possible solutions:", "yellow")
                print_with_color("  1. Check device connection and authorization", "white")
                print_with_color("  2. Ensure sufficient storage space on device", "white")
                print_with_color("  3. Check if USB debugging is enabled", "white")
                print_with_color("  4. Run the diagnose.py script for detailed diagnosis", "white")
                print_with_color("  5. Try different device paths in config.yaml", "white")
                
                break
            
            # Check if task is already completed
            if self.check_task_completion(screenshot_path, xml_path):
                print_with_color("Task completed!", "green")
                task_complete = True
                break
            
            # Generate prompt and get model response
            prompt = self.get_task_prompt(task_desc, last_act, 
                                        screenshot_path=screenshot_path, 
                                        xml_path=xml_path)
            
            print_with_color("Getting model response...", "yellow")
            status, response = self.model.get_model_response(prompt, [screenshot_path])
            
            if not status:
                print_with_color(f"ERROR: Model request failed: {response}", "red")
                break
            
            # Parse and execute action
            action = self.parse_response(response)
            if action[0] == "ERROR":
                print_with_color("ERROR: Failed to parse response", "red")
                break
            
            if action[0] == "FINISH":
                task_complete = True
                break
            
            success = self.execute_action(action)
            if not success:
                print_with_color("ERROR: Action execution failed", "red")
                break
            
            # Update last action
            if len(action) > 1:
                last_act = action[-1] if isinstance(action[-1], str) else str(action)
            
            self.wait_interval()
        
        return task_complete