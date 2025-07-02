"""
Specialized Agent for handling various types of CAPTCHAs
"""
import re
import json
from typing import List, Any, Optional
from enum import Enum

from agents.base_agent import BaseAgent
from scripts.and_controller import traverse_tree, enhanced_traverse_tree, optimize_element_list, analyze_element_distribution
from scripts.utils import print_with_color, draw_bbox_multi
from scripts.captcha_detector import CaptchaDetector
from scripts.ocr_engine import OCREngine
from scripts.omni_parser import OmniParser
from prompts.captcha_prompts import (
    CAPTCHA_DETECTION_PROMPT,
    IMAGE_CAPTCHA_PROMPT,
    SLIDER_CAPTCHA_PROMPT,
    CLICK_CAPTCHA_PROMPT,
    ROTATION_CAPTCHA_PROMPT
)


class CaptchaType(Enum):
    """Types of CAPTCHAs"""
    IMAGE = "image"          # Text in image
    SLIDER = "slider"        # Slide to complete
    CLICK = "click"          # Click on specific objects
    ROTATION = "rotation"    # Rotate image
    UNKNOWN = "unknown"


class CaptchaAgent(BaseAgent):
    """Agent specialized in solving various CAPTCHA types"""
    
    def __init__(self, controller, model, config, work_dir):
        super().__init__(controller, model, config, work_dir)
        self.captcha_type = None
        self.captcha_elements = []
        
        # Initialize enhanced detection components
        self.captcha_detector = CaptchaDetector()
        self.ocr_engine = OCREngine()
        self.omni_parser = OmniParser()
        
        print_with_color("🔧 增强验证码代理已初始化", "green")
        
    def detect_captcha_type(self, screenshot_path: str, xml_path: str) -> CaptchaType:
        """Detect the type of CAPTCHA present on the screen using enhanced detection"""
        print_with_color("使用增强检测系统分析验证码类型...", "blue")
        
        # Use the enhanced captcha detector
        detection_results = self.captcha_detector.detect_captcha_elements(
            screenshot_path, xml_path, self.work_dir
        )
        
        # Analyze results to determine CAPTCHA type
        captcha_analysis = detection_results['captcha_analysis']
        
        if captcha_analysis['captcha_type'] != 'unknown':
            captcha_type_map = {
                'text': CaptchaType.IMAGE,
                'image': CaptchaType.IMAGE,
                'slider': CaptchaType.SLIDER,
                'click': CaptchaType.CLICK,
                'rotation': CaptchaType.ROTATION
            }
            detected_type = captcha_type_map.get(captcha_analysis['captcha_type'], CaptchaType.UNKNOWN)
            print_with_color(f"🎯 自动检测到验证码类型: {detected_type.value}", "green")
            return detected_type
        
        # Fallback to LLM-based detection if automatic detection fails
        print_with_color("自动检测失败，使用LLM进行验证码类型识别...", "yellow")
        
        # Use the combined elements for LLM analysis
        elem_list = detection_results['combined_elements']
        labeled_screenshot = self._create_labeled_screenshot(screenshot_path, elem_list)
        
        prompt = CAPTCHA_DETECTION_PROMPT
        status, response = self.model.get_model_response(prompt, [labeled_screenshot])
        
        if status:
            captcha_type = self._parse_captcha_type(response)
            print_with_color(f"🤖 LLM检测到验证码类型: {captcha_type.value}", "cyan")
            return captcha_type
        
        return CaptchaType.UNKNOWN
    
    def get_task_prompt(self, task_desc: str, last_act: str, **kwargs) -> str:
        """Generate CAPTCHA-specific prompt based on detected type using enhanced detection"""
        screenshot_path = kwargs.get('screenshot_path')
        xml_path = kwargs.get('xml_path')
        
        # Detect CAPTCHA type if not already detected
        if not self.captcha_type:
            self.captcha_type = self.detect_captcha_type(screenshot_path, xml_path)
            print_with_color(f"检测到的验证码类型: {self.captcha_type.value}", "cyan")
        
        # Use enhanced detection to get comprehensive element list
        print_with_color("使用增强检测获取验证码元素...", "blue")
        detection_results = self.captcha_detector.detect_captcha_elements(
            screenshot_path, xml_path, self.work_dir
        )
        
        # Use the combined elements which include XML, OmniParser, and OCR results
        self.captcha_elements = detection_results['combined_elements']
        
        print_with_color(f"✅ 检测到 {len(self.captcha_elements)} 个可交互元素", "green")
        
        # Add OCR information to the context
        ocr_info = ""
        if detection_results['ocr_results']:
            ocr_texts = [ocr.text for ocr in detection_results['ocr_results'] if ocr.text]
            if ocr_texts:
                ocr_info = f"\n\n🔤 OCR识别到的文本内容: {', '.join(ocr_texts)}"
                print_with_color(f"OCR识别结果: {ocr_texts}", "yellow")

        # Select appropriate prompt template
        if self.captcha_type == CaptchaType.IMAGE:
            prompt_template = IMAGE_CAPTCHA_PROMPT
        elif self.captcha_type == CaptchaType.SLIDER:
            prompt_template = SLIDER_CAPTCHA_PROMPT
        elif self.captcha_type == CaptchaType.CLICK:
            prompt_template = CLICK_CAPTCHA_PROMPT
        elif self.captcha_type == CaptchaType.ROTATION:
            prompt_template = ROTATION_CAPTCHA_PROMPT
        else:
            # Fallback to a general approach
            prompt_template = IMAGE_CAPTCHA_PROMPT
        
        # Replace placeholders
        prompt = prompt_template.replace("<task_description>", task_desc)
        prompt = prompt.replace("<last_act>", last_act)
        prompt += ocr_info  # Add OCR information to the prompt
        
        return prompt
    
    def parse_response(self, response: str) -> List[Any]:
        """Parse CAPTCHA-specific response"""
        try:
            # Extract action from response
            action_match = re.search(r"Action: (.*?)$", response, re.MULTILINE)
            if not action_match:
                return ["ERROR", "No action found in response"]
            
            action = action_match.group(1).strip()
            
            # Parse observation and thought for context
            observation = re.findall(r"Observation: (.*?)$", response, re.MULTILINE)
            thought = re.findall(r"Thought: (.*?)$", response, re.MULTILINE)
            
            if observation:
                print_with_color(f"Observation: {observation[0]}", "magenta")
            if thought:
                print_with_color(f"Thought: {thought[0]}", "magenta")
            
            print_with_color(f"Action: {action}", "yellow")
            
            # Check for completion
            if "FINISH" in action or "COMPLETED" in action:
                return ["FINISH"]
            
            # Parse different action types
            if action.startswith("tap("):
                match = re.search(r"tap\((\d+)\)", action)
                if match:
                    area = int(match.group(1))
                    return ["tap", area, action]
            
            elif action.startswith("text("):
                match = re.search(r'text\("(.+?)"\)', action)
                if match:
                    text_input = match.group(1)
                    return ["text", text_input, action]
            
            elif action.startswith("swipe("):
                match = re.search(r'swipe\((\d+),\s*"(\w+)",\s*"(\w+)"\)', action)
                if match:
                    area = int(match.group(1))
                    direction = match.group(2)
                    distance = match.group(3)
                    return ["swipe", area, direction, distance, action]
            
            elif action.startswith("drag("):
                # Custom drag action for slider CAPTCHAs
                # Support both formats: drag(1, 2) and drag(from_element: 1, to_element: 2)
                match = re.search(r'drag\((?:from_element:\s*)?(\d+),\s*(?:to_element:\s*)?(\d+)\)', action)
                if match:
                    from_area = int(match.group(1))
                    to_area = int(match.group(2))
                    print_with_color(f"Parsed drag action: from {from_area} to {to_area}", "cyan")
                    return ["drag", from_area, to_area, action]
                else:
                    print_with_color(f"Failed to parse drag action: {action}", "red")
            
            return ["ERROR", f"Unknown action: {action}"]
            
        except Exception as e:
            print_with_color(f"ERROR parsing response: {e}", "red")
            print_with_color(f"Full response was: {response}", "red")
            return ["ERROR", str(e)]
    
    def execute_action(self, action: List[Any]) -> bool:
        """Execute CAPTCHA-specific actions"""
        try:
            action_type = action[0]
            print_with_color(f"Executing action: {action_type}", "cyan")
            
            if action_type == "tap":
                area_idx = action[1] - 1
                if 0 <= area_idx < len(self.captcha_elements):
                    elem = self.captcha_elements[area_idx]
                    x = (elem.bbox[0][0] + elem.bbox[1][0]) // 2
                    y = (elem.bbox[0][1] + elem.bbox[1][1]) // 2
                    print_with_color(f"Tapping at ({x}, {y})", "cyan")
                    result = self.controller.tap(x, y)
                    return result != "ERROR"
                else:
                    print_with_color(f"ERROR: Element index {action[1]} out of range (max: {len(self.captcha_elements)})", "red")
            
            elif action_type == "text":
                text_input = action[1]
                result = self.controller.text(text_input)
                return result != "ERROR"
            
            elif action_type == "swipe":
                area_idx = action[1] - 1
                direction = action[2]
                distance = action[3]
                
                if 0 <= area_idx < len(self.captcha_elements):
                    elem = self.captcha_elements[area_idx]
                    x = (elem.bbox[0][0] + elem.bbox[1][0]) // 2
                    y = (elem.bbox[0][1] + elem.bbox[1][1]) // 2
                    result = self.controller.swipe(x, y, direction, distance)
                    return result != "ERROR"
            
            elif action_type == "drag":
                # Implement drag for slider CAPTCHAs
                from_idx = action[1] - 1
                to_idx = action[2] - 1
                
                print_with_color(f"Number of elements: {len(self.captcha_elements)}", "cyan")
                
                if (0 <= from_idx < len(self.captcha_elements) and 
                    0 <= to_idx < len(self.captcha_elements)):
                    from_elem = self.captcha_elements[from_idx]
                    to_elem = self.captcha_elements[to_idx]
                    
                    start_x = (from_elem.bbox[0][0] + from_elem.bbox[1][0]) // 2
                    start_y = (from_elem.bbox[0][1] + from_elem.bbox[1][1]) // 2
                    end_x = (to_elem.bbox[0][0] + to_elem.bbox[1][0]) // 2
                    end_y = (to_elem.bbox[0][1] + to_elem.bbox[1][1]) // 2
                    
                    print_with_color(f"Dragging from ({start_x}, {start_y}) to ({end_x}, {end_y})", "cyan")
                    result = self.controller.swipe_precise((start_x, start_y), (end_x, end_y), 1000)
                    return result != "ERROR"
                else:
                    print_with_color(f"ERROR: Drag indices out of range. From: {from_idx+1}, To: {to_idx+1}, Max: {len(self.captcha_elements)}", "red")
            
            return False
            
        except Exception as e:
            print_with_color(f"ERROR executing action: {e}", "red")
            return False
    
    def check_task_completion(self, screenshot_path: str, xml_path: str) -> bool:
        """Check if CAPTCHA has been successfully solved"""
        # Simple check: look for common success indicators
        # This can be enhanced with more sophisticated detection
        
        prompt = """Look at this screenshot and determine if a CAPTCHA has been successfully solved.
        Signs of success include:
        - The CAPTCHA is no longer visible
        - A success message is shown
        - The page has navigated to the next step
        - A checkmark or success indicator is visible
        
        Respond with only "SUCCESS" if the CAPTCHA appears to be solved, or "NOT_COMPLETE" if it's still present."""
        
        status, response = self.model.get_model_response(prompt, [screenshot_path])
        
        if status and "SUCCESS" in response:
            return True
        
        return False
    
    def _merge_elements(self, clickable_list, focusable_list):
        """Merge clickable and focusable elements"""
        elem_list = clickable_list.copy()
        
        for elem in focusable_list:
            bbox = elem.bbox
            center = (bbox[0][0] + bbox[1][0]) // 2, (bbox[0][1] + bbox[1][1]) // 2
            close = False
            
            for e in clickable_list:
                bbox_e = e.bbox
                center_e = (bbox_e[0][0] + bbox_e[1][0]) // 2, (bbox_e[0][1] + bbox_e[1][1]) // 2
                dist = ((center[0] - center_e[0]) ** 2 + (center[1] - center_e[1]) ** 2) ** 0.5
                
                if dist <= self.config.get("MIN_DIST", 30):
                    close = True
                    break
            
            if not close:
                elem_list.append(elem)
        
        return elem_list
    
    def _create_labeled_screenshot(self, screenshot_path, elem_list):
        """Create labeled screenshot with numbered elements"""
        import os
        
        output_path = os.path.join(
            self.work_dir, 
            f"labeled_{os.path.basename(screenshot_path)}"
        )
        
        draw_bbox_multi(
            screenshot_path, 
            output_path, 
            elem_list,
            dark_mode=self.config.get("DARK_MODE", False)
        )
        
        return output_path
    
    def _parse_captcha_type(self, response: str) -> CaptchaType:
        """Parse CAPTCHA type from detection response"""
        response_lower = response.lower()
        
        if "slider" in response_lower or "slide" in response_lower:
            return CaptchaType.SLIDER
        elif "click" in response_lower or "select" in response_lower:
            return CaptchaType.CLICK
        elif "rotate" in response_lower or "rotation" in response_lower:
            return CaptchaType.ROTATION
        elif "image" in response_lower or "text" in response_lower or "character" in response_lower:
            return CaptchaType.IMAGE
        else:
            return CaptchaType.UNKNOWN