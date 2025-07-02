#!/usr/bin/env python3
"""
OmniParser integration for advanced UI element detection
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
import json
import os
import tempfile

try:
    import torch
    import torch.nn as nn
    from torchvision import transforms
    from PIL import Image
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("PyTorch not available for OmniParser")

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("YOLO not available for OmniParser")

from .utils import print_with_color
from .and_controller import AndroidElement


class UIElement:
    """Detected UI element from OmniParser"""
    def __init__(self, bbox: Tuple[int, int, int, int], label: str, confidence: float, element_type: str = "visual"):
        self.bbox = bbox  # (x1, y1, x2, y2)
        self.label = label
        self.confidence = confidence
        self.element_type = element_type
        self.center = ((bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2)


class OmniParser:
    """
    OmniParser for detecting UI elements that XML parsing might miss
    This is a simplified implementation that can be extended with actual OmniParser models
    """
    
    def __init__(self):
        self.initialized = False
        self.yolo_model = None
        self.device = "cpu"
        self._initialize()
    
    def _initialize(self):
        """Initialize OmniParser components"""
        print_with_color("正在初始化 OmniParser...", "blue")
        
        if TORCH_AVAILABLE:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            print_with_color(f"使用设备: {self.device}", "green")
        
        # Initialize YOLO for general object detection (can detect UI elements)
        if YOLO_AVAILABLE:
            try:
                # Use YOLOv8 nano model for UI element detection
                # In a real implementation, you would use a model trained specifically for UI elements
                self.yolo_model = YOLO('yolov8n.pt')  # This will download the model if not present
                print_with_color("✅ YOLO模型加载成功", "green")
                self.initialized = True
            except Exception as e:
                print_with_color(f"❌ YOLO模型加载失败: {e}", "red")
        
        if not self.initialized:
            print_with_color("⚠️ OmniParser初始化失败，将使用fallback方法", "yellow")
    
    def detect_ui_elements(self, image_path: str, confidence_threshold: float = 0.3) -> List[UIElement]:
        """
        Detect UI elements in the screenshot using computer vision
        """
        print_with_color(f"使用 OmniParser 检测UI元素: {image_path}", "blue")
        
        elements = []
        
        # Method 1: YOLO-based detection
        if self.yolo_model is not None:
            yolo_elements = self._detect_with_yolo(image_path, confidence_threshold)
            elements.extend(yolo_elements)
        
        # Method 2: Traditional computer vision methods
        cv_elements = self._detect_with_cv(image_path, confidence_threshold)
        elements.extend(cv_elements)
        
        # Method 3: Text region detection
        text_elements = self._detect_text_regions(image_path)
        elements.extend(text_elements)
        
        # Remove duplicates and filter by confidence
        filtered_elements = self._filter_and_deduplicate(elements, confidence_threshold)
        
        print_with_color(f"OmniParser检测到 {len(filtered_elements)} 个元素", "green")
        return filtered_elements
    
    def _detect_with_yolo(self, image_path: str, confidence_threshold: float) -> List[UIElement]:
        """Use YOLO for UI element detection"""
        elements = []
        
        try:
            results = self.yolo_model(image_path, conf=confidence_threshold)
            
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for i, box in enumerate(boxes):
                        # Get bounding box coordinates
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = box.conf[0].cpu().numpy()
                        class_id = int(box.cls[0].cpu().numpy())
                        
                        # Map class to UI element type
                        class_name = self.yolo_model.names[class_id]
                        
                        # Filter for potential UI elements
                        ui_classes = ['person', 'car', 'truck', 'bus', 'motorcycle', 'bicycle']  # These might appear in CAPTCHAs
                        if class_name in ui_classes or confidence > 0.5:
                            element = UIElement(
                                bbox=(int(x1), int(y1), int(x2), int(y2)),
                                label=f"yolo_{class_name}",
                                confidence=float(confidence),
                                element_type="yolo_detection"
                            )
                            elements.append(element)
        
        except Exception as e:
            print_with_color(f"YOLO检测错误: {e}", "red")
        
        return elements
    
    def _detect_with_cv(self, image_path: str, confidence_threshold: float) -> List[UIElement]:
        """Use traditional computer vision methods to detect UI elements"""
        elements = []
        
        try:
            img = cv2.imread(image_path)
            if img is None:
                return elements
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Method 1: Contour detection for buttons and boxes
            contour_elements = self._detect_contours(gray, img.shape)
            elements.extend(contour_elements)
            
            # Method 2: Edge detection for input fields
            edge_elements = self._detect_edges(gray, img.shape)
            elements.extend(edge_elements)
            
            # Method 3: Template matching for common UI patterns
            template_elements = self._detect_templates(gray, img.shape)
            elements.extend(template_elements)
        
        except Exception as e:
            print_with_color(f"CV检测错误: {e}", "red")
        
        return elements
    
    def _detect_contours(self, gray_img: np.ndarray, img_shape: Tuple) -> List[UIElement]:
        """Detect rectangular UI elements using contour detection"""
        elements = []
        
        # Apply threshold to get binary image
        _, binary = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        height, width = img_shape[:2]
        min_area = (width * height) * 0.0001  # Minimum 0.01% of image area
        max_area = (width * height) * 0.3     # Maximum 30% of image area
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if min_area < area < max_area:
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                
                # Filter by aspect ratio (reasonable UI elements)
                aspect_ratio = w / h if h > 0 else 0
                if 0.1 < aspect_ratio < 10:  # Not too thin or too wide
                    confidence = min(1.0, area / (width * height * 0.1))  # Simple confidence based on size
                    
                    element = UIElement(
                        bbox=(x, y, x + w, y + h),
                        label="contour_rect",
                        confidence=confidence,
                        element_type="contour"
                    )
                    elements.append(element)
        
        return elements
    
    def _detect_edges(self, gray_img: np.ndarray, img_shape: Tuple) -> List[UIElement]:
        """Detect UI elements using edge detection"""
        elements = []
        
        # Apply Canny edge detection
        edges = cv2.Canny(gray_img, 50, 150)
        
        # Dilate to connect nearby edges
        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=2)
        
        # Find contours in edge image
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        height, width = img_shape[:2]
        min_area = (width * height) * 0.0005
        max_area = (width * height) * 0.2
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if min_area < area < max_area:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0
                
                if 0.2 < aspect_ratio < 5:  # Reasonable aspect ratio for UI elements
                    confidence = min(0.8, area / (width * height * 0.05))
                    
                    element = UIElement(
                        bbox=(x, y, x + w, y + h),
                        label="edge_rect",
                        confidence=confidence,
                        element_type="edge"
                    )
                    elements.append(element)
        
        return elements
    
    def _detect_templates(self, gray_img: np.ndarray, img_shape: Tuple) -> List[UIElement]:
        """Detect UI elements using template matching patterns"""
        elements = []
        
        # Create simple templates for common UI patterns
        height, width = img_shape[:2]
        
        # Template for button-like rectangles
        button_template = np.ones((30, 80), dtype=np.uint8) * 128
        cv2.rectangle(button_template, (2, 2), (77, 27), 255, 2)
        
        # Template matching
        try:
            res = cv2.matchTemplate(gray_img, button_template, cv2.TM_CCOEFF_NORMED)
            locations = np.where(res >= 0.6)
            
            for pt in zip(*locations[::-1]):
                x, y = pt
                w, h = button_template.shape[1], button_template.shape[0]
                confidence = float(res[y, x])
                
                element = UIElement(
                    bbox=(x, y, x + w, y + h),
                    label="template_button",
                    confidence=confidence,
                    element_type="template"
                )
                elements.append(element)
        
        except Exception as e:
            print_with_color(f"模板匹配错误: {e}", "yellow")
        
        return elements
    
    def _detect_text_regions(self, image_path: str) -> List[UIElement]:
        """Detect text regions that might be clickable"""
        elements = []
        
        try:
            img = cv2.imread(image_path)
            if img is None:
                return elements
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Use MSER (Maximally Stable Extremal Regions) to detect text regions
            mser = cv2.MSER_create()
            regions, _ = mser.detectRegions(gray)
            
            for region in regions:
                if len(region) > 10:  # Filter small regions
                    x, y, w, h = cv2.boundingRect(region)
                    area = w * h
                    
                    # Filter by size and aspect ratio
                    if 100 < area < 5000 and 0.1 < w/h < 10:
                        confidence = min(0.7, area / 2000)  # Simple confidence based on size
                        
                        element = UIElement(
                            bbox=(x, y, x + w, y + h),
                            label="text_region",
                            confidence=confidence,
                            element_type="text_region"
                        )
                        elements.append(element)
        
        except Exception as e:
            print_with_color(f"文本区域检测错误: {e}", "yellow")
        
        return elements
    
    def _filter_and_deduplicate(self, elements: List[UIElement], confidence_threshold: float) -> List[UIElement]:
        """Filter elements by confidence and remove duplicates"""
        # Filter by confidence
        filtered = [elem for elem in elements if elem.confidence >= confidence_threshold]
        
        # Remove duplicates (elements with overlapping bounding boxes)
        deduplicated = []
        
        for elem in filtered:
            is_duplicate = False
            for existing in deduplicated:
                # Calculate IoU (Intersection over Union)
                iou = self._calculate_iou(elem.bbox, existing.bbox)
                if iou > 0.5:  # If overlap is > 50%, consider it duplicate
                    # Keep the one with higher confidence
                    if elem.confidence > existing.confidence:
                        deduplicated.remove(existing)
                    else:
                        is_duplicate = True
                    break
            
            if not is_duplicate:
                deduplicated.append(elem)
        
        return sorted(deduplicated, key=lambda x: x.confidence, reverse=True)
    
    def _calculate_iou(self, bbox1: Tuple[int, int, int, int], bbox2: Tuple[int, int, int, int]) -> float:
        """Calculate Intersection over Union of two bounding boxes"""
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # Calculate intersection
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i <= x1_i or y2_i <= y1_i:
            return 0.0
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        
        # Calculate union
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def convert_to_android_elements(self, ui_elements: List[UIElement]) -> List[AndroidElement]:
        """Convert UIElement objects to AndroidElement objects for compatibility"""
        android_elements = []
        
        for i, ui_elem in enumerate(ui_elements):
            elem_id = f"omni_{ui_elem.element_type}_{i}_{ui_elem.label}"
            bbox = ((ui_elem.bbox[0], ui_elem.bbox[1]), (ui_elem.bbox[2], ui_elem.bbox[3]))
            
            android_elem = AndroidElement(
                uid=elem_id,
                bbox=bbox,
                attrib=f"omni_{ui_elem.element_type}"
            )
            android_elements.append(android_elem)
        
        return android_elements
