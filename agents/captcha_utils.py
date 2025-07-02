"""
Utility functions for CAPTCHA handling
"""
import cv2
import numpy as np
from typing import Tuple, List, Optional
import base64


class CaptchaEnhancer:
    """Image enhancement for better CAPTCHA recognition"""
    
    @staticmethod
    def enhance_captcha_image(image_path: str, output_path: str) -> str:
        """Enhance CAPTCHA image for better OCR recognition"""
        try:
            # Read image
            img = cv2.imread(image_path)
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply threshold to get binary image
            _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
            
            # Denoise
            denoised = cv2.medianBlur(binary, 3)
            
            # Increase contrast
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)
            
            # Save enhanced image
            cv2.imwrite(output_path, enhanced)
            return output_path
            
        except Exception as e:
            print(f"Error enhancing image: {e}")
            return image_path
    
    @staticmethod
    def extract_captcha_region(screenshot_path: str, bbox: Tuple[Tuple[int, int], Tuple[int, int]]) -> Optional[str]:
        """Extract CAPTCHA region from screenshot"""
        try:
            img = cv2.imread(screenshot_path)
            
            # Extract region
            (x1, y1), (x2, y2) = bbox
            captcha_region = img[y1:y2, x1:x2]
            
            # Save extracted region
            output_path = screenshot_path.replace('.png', '_captcha.png')
            cv2.imwrite(output_path, captcha_region)
            
            return output_path
            
        except Exception as e:
            print(f"Error extracting CAPTCHA region: {e}")
            return None


class SliderCaptchaSolver:
    """Specialized solver for slider CAPTCHAs"""
    
    @staticmethod
    def find_slider_gap(image_path: str) -> Optional[Tuple[int, int]]:
        """Find the gap position in slider CAPTCHA"""
        try:
            img = cv2.imread(image_path)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Edge detection
            edges = cv2.Canny(gray, 50, 150)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Look for gap-like shapes
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Gap usually has specific aspect ratio
                if 0.8 < w/h < 1.2 and w > 30:
                    return (x + w//2, y + h//2)
            
            return None
            
        except Exception as e:
            print(f"Error finding slider gap: {e}")
            return None
    
    @staticmethod
    def calculate_slider_distance(slider_pos: Tuple[int, int], gap_pos: Tuple[int, int]) -> int:
        """Calculate required slider movement distance"""
        return gap_pos[0] - slider_pos[0]


class ClickCaptchaSolver:
    """Specialized solver for click CAPTCHAs"""
    
    @staticmethod
    def detect_objects_in_grid(image_path: str, target_object: str) -> List[int]:
        """Detect target objects in CAPTCHA grid (placeholder for actual implementation)"""
        # This would require integration with object detection model
        # For now, return empty list
        return []
    
    @staticmethod
    def match_template(image_path: str, template_path: str, threshold: float = 0.8) -> List[Tuple[int, int]]:
        """Find template matches in image"""
        try:
            img = cv2.imread(image_path)
            template = cv2.imread(template_path)
            
            # Convert to grayscale
            img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            
            # Template matching
            result = cv2.matchTemplate(img_gray, template_gray, cv2.TM_CCOEFF_NORMED)
            
            # Find locations above threshold
            locations = np.where(result >= threshold)
            matches = []
            
            for pt in zip(*locations[::-1]):
                matches.append((pt[0], pt[1]))
            
            return matches
            
        except Exception as e:
            print(f"Error in template matching: {e}")
            return []


class CaptchaPatterns:
    """Common CAPTCHA patterns and solutions"""
    
    # Common CAPTCHA instructions and their keywords
    CLICK_PATTERNS = {
        "traffic_light": ["traffic light", "signal", "traffic signal"],
        "crosswalk": ["crosswalk", "pedestrian crossing", "zebra crossing"],
        "bicycle": ["bicycle", "bike", "cycle"],
        "car": ["car", "vehicle", "automobile"],
        "bus": ["bus", "public transport"],
        "motorcycle": ["motorcycle", "motorbike"],
        "fire_hydrant": ["fire hydrant", "hydrant"],
        "stairs": ["stairs", "staircase", "steps"],
        "bridge": ["bridge", "overpass"],
        "boat": ["boat", "ship", "vessel"]
    }
    
    @classmethod
    def identify_target_object(cls, instruction: str) -> Optional[str]:
        """Identify what object to look for based on instruction"""
        instruction_lower = instruction.lower()
        
        for obj_type, keywords in cls.CLICK_PATTERNS.items():
            for keyword in keywords:
                if keyword in instruction_lower:
                    return obj_type
        
        return None
    
    @staticmethod
    def get_rotation_angle(image_path: str) -> int:
        """Estimate required rotation angle for image"""
        # This would require image analysis to determine correct orientation
        # For now, return 0
        return 0