#!/usr/bin/env python3
"""
Enhanced CAPTCHA detector combining XML parsing, OmniParser, and OCR
"""

import os
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
import json

from .and_controller import AndroidElement, traverse_tree, enhanced_traverse_tree, optimize_element_list
from .ocr_engine import OCREngine, OCRResult
from .omni_parser import OmniParser, UIElement
from .utils import print_with_color, draw_bbox_multi


class CaptchaDetector:
    """Enhanced CAPTCHA detection system"""
    
    def __init__(self):
        self.ocr_engine = OCREngine()
        self.omni_parser = OmniParser()
        self.detection_cache = {}
    
    def detect_captcha_elements(self, screenshot_path: str, xml_path: str, output_dir: str = None) -> Dict:
        """
        Comprehensive CAPTCHA element detection using multiple methods
        """
        print_with_color("=== 开始增强验证码检测 ===", "blue")
        
        if output_dir is None:
            output_dir = os.path.dirname(screenshot_path)
        
        results = {
            'screenshot_path': screenshot_path,
            'xml_path': xml_path,
            'xml_elements': [],
            'omni_elements': [],
            'ocr_results': [],
            'combined_elements': [],
            'captcha_analysis': {},
            'labeled_images': {}
        }
        
        # Step 1: Traditional XML-based detection
        print_with_color("1. 执行XML元素检测...", "yellow")
        xml_elements = self._detect_xml_elements(xml_path)
        results['xml_elements'] = xml_elements
        print_with_color(f"   XML检测到 {len(xml_elements)} 个元素", "white")
        
        # Step 2: OmniParser detection
        print_with_color("2. 执行OmniParser视觉检测...", "yellow")
        omni_elements = self._detect_visual_elements(screenshot_path)
        results['omni_elements'] = omni_elements
        print_with_color(f"   OmniParser检测到 {len(omni_elements)} 个元素", "white")
        
        # Step 3: OCR text detection
        print_with_color("3. 执行OCR文本识别...", "yellow")
        ocr_results = self._detect_text_elements(screenshot_path)
        results['ocr_results'] = ocr_results
        print_with_color(f"   OCR检测到 {len(ocr_results)} 个文本区域", "white")
        
        # Step 4: Analyze potential CAPTCHA regions
        print_with_color("4. 分析验证码区域...", "yellow")
        captcha_analysis = self._analyze_captcha_regions(screenshot_path, xml_elements, omni_elements, ocr_results)
        results['captcha_analysis'] = captcha_analysis
        
        # Step 5: Combine and optimize all elements
        print_with_color("5. 合并和优化元素列表...", "yellow")
        combined_elements = self._combine_all_elements(xml_elements, omni_elements, ocr_results, screenshot_path)
        results['combined_elements'] = combined_elements
        print_with_color(f"   最终合并得到 {len(combined_elements)} 个元素", "green")
        
        # Step 6: Generate labeled images
        print_with_color("6. 生成标注图片...", "yellow")
        labeled_images = self._create_labeled_images(screenshot_path, results, output_dir)
        results['labeled_images'] = labeled_images
        
        # Step 7: Generate detection report
        self._generate_detection_report(results, output_dir)
        
        print_with_color("=== 增强验证码检测完成 ===", "green")
        return results
    
    def _detect_xml_elements(self, xml_path: str) -> List[AndroidElement]:
        """Detect elements using traditional XML parsing"""
        all_elements = []
        
        # Enhanced detection
        enhanced_elements = []
        enhanced_traverse_tree(xml_path, enhanced_elements, True, include_all_elements=True)
        all_elements.extend(enhanced_elements)
        
        # Traditional detection
        clickable_list = []
        focusable_list = []
        traverse_tree(xml_path, clickable_list, "clickable", True)
        traverse_tree(xml_path, focusable_list, "focusable", True)
        all_elements.extend(clickable_list)
        all_elements.extend(focusable_list)
        
        # Optimize and deduplicate
        optimized_elements = optimize_element_list(all_elements)
        return optimized_elements
    
    def _detect_visual_elements(self, screenshot_path: str) -> List[AndroidElement]:
        """Detect elements using OmniParser"""
        ui_elements = self.omni_parser.detect_ui_elements(screenshot_path, confidence_threshold=0.2)
        android_elements = self.omni_parser.convert_to_android_elements(ui_elements)
        return android_elements
    
    def _detect_text_elements(self, screenshot_path: str) -> List[OCRResult]:
        """Detect text using OCR"""
        # First, try to extract text from the whole image
        main_ocr = self.ocr_engine.recognize_captcha(screenshot_path)
        
        # Then, extract all text regions
        text_regions = self.ocr_engine.extract_text_regions(screenshot_path)
        
        # Combine results
        all_ocr_results = text_regions.copy()
        
        # Add main OCR result if it's not already included
        if main_ocr['text'] and main_ocr['bbox']:
            main_result = OCRResult(main_ocr['text'], main_ocr['confidence'], main_ocr['bbox'])
            all_ocr_results.append(main_result)
        
        return all_ocr_results
    
    def _analyze_captcha_regions(self, screenshot_path: str, xml_elements: List[AndroidElement], 
                                omni_elements: List[AndroidElement], ocr_results: List[OCRResult]) -> Dict:
        """Analyze potential CAPTCHA regions in the screenshot"""
        analysis = {
            'has_captcha_image': False,
            'has_input_field': False,
            'has_submit_button': False,
            'captcha_type': 'unknown',
            'captcha_regions': [],
            'input_fields': [],
            'buttons': [],
            'text_content': []
        }
        
        img = cv2.imread(screenshot_path)
        if img is None:
            return analysis
        
        height, width = img.shape[:2]
        
        # Analyze OCR results for CAPTCHA text
        for ocr_result in ocr_results:
            if ocr_result.text and len(ocr_result.text) >= 3:
                analysis['text_content'].append({
                    'text': ocr_result.text,
                    'bbox': ocr_result.bbox,
                    'confidence': ocr_result.confidence
                })
                
                # Check if this looks like a CAPTCHA
                if self._is_captcha_text(ocr_result.text):
                    analysis['has_captcha_image'] = True
                    analysis['captcha_regions'].append(ocr_result.bbox)
        
        # Analyze XML elements for UI components
        for elem in xml_elements:
            elem_class = getattr(elem, 'class', '') if hasattr(elem, 'class') else ''
            elem_type = elem.attrib
            
            # Check for input fields
            if ('EditText' in str(elem_class) or 'input' in elem_type.lower() or 
                'text' in elem_type.lower()):
                analysis['input_fields'].append(elem.bbox)
                analysis['has_input_field'] = True
            
            # Check for buttons
            if ('Button' in str(elem_class) or 'button' in elem_type.lower() or 
                elem_type == 'clickable'):
                analysis['buttons'].append(elem.bbox)
                analysis['has_submit_button'] = True
        
        # Analyze OmniParser elements
        for elem in omni_elements:
            elem_type = elem.attrib
            
            if 'text' in elem_type or 'contour' in elem_type:
                # Potential CAPTCHA image area
                bbox_area = (elem.bbox[1][0] - elem.bbox[0][0]) * (elem.bbox[1][1] - elem.bbox[0][1])
                if 1000 < bbox_area < 50000:  # Reasonable size for CAPTCHA
                    analysis['captcha_regions'].append(elem.bbox)
                    analysis['has_captcha_image'] = True
        
        # Determine CAPTCHA type
        if analysis['has_captcha_image'] and analysis['has_input_field']:
            if any('slider' in text.lower() for text in [t['text'] for t in analysis['text_content']]):
                analysis['captcha_type'] = 'slider'
            elif any('click' in text.lower() for text in [t['text'] for t in analysis['text_content']]):
                analysis['captcha_type'] = 'click'
            elif analysis['text_content']:
                analysis['captcha_type'] = 'text'
            else:
                analysis['captcha_type'] = 'image'
        
        return analysis
    
    def _is_captcha_text(self, text: str) -> bool:
        """Check if text looks like CAPTCHA content"""
        if not text:
            return False
        
        # Check length (typical CAPTCHA is 4-8 characters)
        if not (3 <= len(text) <= 10):
            return False
        
        # Check for mix of letters and numbers
        has_alpha = any(c.isalpha() for c in text)
        has_digit = any(c.isdigit() for c in text)
        
        # CAPTCHA often has mixed case or distorted text
        has_mixed_case = text != text.lower() and text != text.upper()
        
        # Common CAPTCHA characteristics
        is_random_looking = not any(word in text.lower() for word in 
                                   ['the', 'and', 'for', 'are', 'but', 'not', 'you', 'all'])
        
        return (has_alpha or has_digit) and (has_mixed_case or is_random_looking)
    
    def _combine_all_elements(self, xml_elements: List[AndroidElement], 
                             omni_elements: List[AndroidElement], 
                             ocr_results: List[OCRResult],
                             screenshot_path: str) -> List[AndroidElement]:
        """Combine elements from all detection methods"""
        combined = []
        
        # Add XML elements
        combined.extend(xml_elements)
        
        # Add OmniParser elements (filter duplicates)
        for omni_elem in omni_elements:
            is_duplicate = False
            for xml_elem in xml_elements:
                if self._elements_overlap(omni_elem.bbox, xml_elem.bbox, threshold=0.5):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                combined.append(omni_elem)
        
        # Add OCR results as AndroidElements
        for i, ocr_result in enumerate(ocr_results):
            if ocr_result.bbox and ocr_result.text:
                elem_id = f"ocr_text_{i}_{ocr_result.text[:10]}"
                bbox = ((ocr_result.bbox[0], ocr_result.bbox[1]), 
                       (ocr_result.bbox[2], ocr_result.bbox[3]))
                
                # Check for duplicates
                is_duplicate = False
                for existing_elem in combined:
                    if self._elements_overlap(bbox, existing_elem.bbox, threshold=0.3):
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    ocr_element = AndroidElement(
                        uid=elem_id,
                        bbox=bbox,
                        attrib="ocr_text"
                    )
                    combined.append(ocr_element)
        
        # Final optimization
        return optimize_element_list(combined, screenshot_path)
    
    def _elements_overlap(self, bbox1: Tuple, bbox2: Tuple, threshold: float = 0.5) -> bool:
        """Check if two bounding boxes overlap significantly"""
        # Convert bbox formats if needed
        if isinstance(bbox1[0], tuple):  # ((x1,y1), (x2,y2)) format
            x1_1, y1_1, x2_1, y2_1 = bbox1[0][0], bbox1[0][1], bbox1[1][0], bbox1[1][1]
        else:  # (x1, y1, x2, y2) format
            x1_1, y1_1, x2_1, y2_1 = bbox1
        
        if isinstance(bbox2[0], tuple):
            x1_2, y1_2, x2_2, y2_2 = bbox2[0][0], bbox2[0][1], bbox2[1][0], bbox2[1][1]
        else:
            x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # Calculate intersection
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i <= x1_i or y2_i <= y1_i:
            return False
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        
        if area1 == 0 or area2 == 0:
            return False
        
        overlap_ratio = intersection / min(area1, area2)
        return overlap_ratio >= threshold
    
    def _create_labeled_images(self, screenshot_path: str, results: Dict, output_dir: str) -> Dict:
        """Create labeled images for each detection method"""
        labeled_images = {}
        
        # XML elements
        if results['xml_elements']:
            xml_labeled = os.path.join(output_dir, "xml_elements_labeled.png")
            draw_bbox_multi(screenshot_path, xml_labeled, results['xml_elements'])
            labeled_images['xml_elements'] = xml_labeled
        
        # OmniParser elements
        if results['omni_elements']:
            omni_labeled = os.path.join(output_dir, "omni_elements_labeled.png")
            draw_bbox_multi(screenshot_path, omni_labeled, results['omni_elements'])
            labeled_images['omni_elements'] = omni_labeled
        
        # Combined elements
        if results['combined_elements']:
            combined_labeled = os.path.join(output_dir, "combined_elements_labeled.png")
            draw_bbox_multi(screenshot_path, combined_labeled, results['combined_elements'])
            labeled_images['combined_elements'] = combined_labeled
        
        # OCR results visualization
        if results['ocr_results']:
            ocr_labeled = self._create_ocr_visualization(screenshot_path, results['ocr_results'], output_dir)
            labeled_images['ocr_results'] = ocr_labeled
        
        return labeled_images
    
    def _create_ocr_visualization(self, screenshot_path: str, ocr_results: List[OCRResult], output_dir: str) -> str:
        """Create visualization of OCR results"""
        img = cv2.imread(screenshot_path)
        if img is None:
            return ""
        
        for i, ocr_result in enumerate(ocr_results):
            if ocr_result.bbox:
                x1, y1, x2, y2 = ocr_result.bbox
                
                # Draw bounding box
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Draw text and confidence
                label = f"{ocr_result.text} ({ocr_result.confidence:.2f})"
                cv2.putText(img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        output_path = os.path.join(output_dir, "ocr_results_labeled.png")
        cv2.imwrite(output_path, img)
        return output_path
    
    def _generate_detection_report(self, results: Dict, output_dir: str):
        """Generate a detailed detection report"""
        report_path = os.path.join(output_dir, "detection_report.json")
        
        # Prepare report data
        report_data = {
            'detection_summary': {
                'xml_elements_count': len(results['xml_elements']),
                'omni_elements_count': len(results['omni_elements']),
                'ocr_results_count': len(results['ocr_results']),
                'combined_elements_count': len(results['combined_elements'])
            },
            'captcha_analysis': results['captcha_analysis'],
            'ocr_texts': [{'text': ocr.text, 'confidence': ocr.confidence} 
                         for ocr in results['ocr_results']],
            'labeled_images': results['labeled_images']
        }
        
        # Save report
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print_with_color(f"检测报告已保存: {report_path}", "green")
        
        # Print summary
        print_with_color("\n=== 检测结果摘要 ===", "cyan")
        print_with_color(f"XML元素: {report_data['detection_summary']['xml_elements_count']}", "white")
        print_with_color(f"视觉元素: {report_data['detection_summary']['omni_elements_count']}", "white")
        print_with_color(f"OCR文本: {report_data['detection_summary']['ocr_results_count']}", "white")
        print_with_color(f"合并元素: {report_data['detection_summary']['combined_elements_count']}", "white")
        
        if results['captcha_analysis']['captcha_type'] != 'unknown':
            print_with_color(f"验证码类型: {results['captcha_analysis']['captcha_type']}", "yellow")
        
        if results['ocr_results']:
            print_with_color("识别到的文本:", "blue")
            for ocr in results['ocr_results']:
                if ocr.text:
                    print_with_color(f"  '{ocr.text}' (置信度: {ocr.confidence:.2f})", "white")
