#!/usr/bin/env python3
"""
OCR Engine for text recognition in images, especially CAPTCHAs
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict
import re
import os

try:
    import paddleocr
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False
    print("PaddleOCR not available")

try:
    import easyocr
    EASY_AVAILABLE = True
except ImportError:
    EASY_AVAILABLE = False
    print("EasyOCR not available")

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("Tesseract not available")

from .utils import print_with_color


class OCRResult:
    def __init__(self, text: str, confidence: float, bbox: Tuple[int, int, int, int] = None):
        self.text = text
        self.confidence = confidence
        self.bbox = bbox  # (x1, y1, x2, y2)


class OCREngine:
    """Multi-engine OCR system for robust text recognition"""
    
    def __init__(self):
        self.engines = {}
        self._initialize_engines()
    
    def _initialize_engines(self):
        """Initialize available OCR engines"""
        if PADDLE_AVAILABLE:
            try:
                self.engines['paddle'] = paddleocr.PaddleOCR(
                    use_angle_cls=True, 
                    lang='en',
                    show_log=False
                )
                print_with_color("✅ PaddleOCR initialized", "green")
            except Exception as e:
                print_with_color(f"❌ PaddleOCR initialization failed: {e}", "red")
        
        if EASY_AVAILABLE:
            try:
                self.engines['easy'] = easyocr.Reader(['en'], gpu=False)
                print_with_color("✅ EasyOCR initialized", "green")
            except Exception as e:
                print_with_color(f"❌ EasyOCR initialization failed: {e}", "red")
        
        if TESSERACT_AVAILABLE:
            try:
                # Test if tesseract is available
                pytesseract.get_tesseract_version()
                self.engines['tesseract'] = True
                print_with_color("✅ Tesseract initialized", "green")
            except Exception as e:
                print_with_color(f"❌ Tesseract initialization failed: {e}", "red")
    
    def preprocess_captcha_image(self, image_path: str, output_path: str = None) -> str:
        """Preprocess CAPTCHA image for better OCR recognition"""
        img = cv2.imread(image_path)
        if img is None:
            return image_path
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply noise reduction
        denoised = cv2.medianBlur(gray, 3)
        
        # Apply threshold to get binary image
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Morphological operations to clean up
        kernel = np.ones((2, 2), np.uint8)
        cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # Resize image for better recognition (if too small)
        height, width = cleaned.shape
        if height < 50 or width < 150:
            scale_factor = max(50/height, 150/width)
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            cleaned = cv2.resize(cleaned, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        # Save preprocessed image
        if output_path is None:
            base_name = os.path.splitext(image_path)[0]
            output_path = f"{base_name}_preprocessed.png"
        
        cv2.imwrite(output_path, cleaned)
        return output_path
    
    def extract_text_paddle(self, image_path: str) -> List[OCRResult]:
        """Extract text using PaddleOCR"""
        if 'paddle' not in self.engines:
            return []
        
        try:
            result = self.engines['paddle'].ocr(image_path, cls=True)
            ocr_results = []
            
            if result and result[0]:
                for line in result[0]:
                    if len(line) >= 2:
                        bbox_points = line[0]
                        text_info = line[1]
                        text = text_info[0] if isinstance(text_info, (list, tuple)) else str(text_info)
                        confidence = text_info[1] if isinstance(text_info, (list, tuple)) and len(text_info) > 1 else 0.5
                        
                        # Convert bbox points to x1,y1,x2,y2 format
                        x_coords = [point[0] for point in bbox_points]
                        y_coords = [point[1] for point in bbox_points]
                        bbox = (int(min(x_coords)), int(min(y_coords)), 
                               int(max(x_coords)), int(max(y_coords)))
                        
                        ocr_results.append(OCRResult(text, confidence, bbox))
            
            return ocr_results
        except Exception as e:
            print_with_color(f"PaddleOCR error: {e}", "red")
            return []
    
    def extract_text_easy(self, image_path: str) -> List[OCRResult]:
        """Extract text using EasyOCR"""
        if 'easy' not in self.engines:
            return []
        
        try:
            result = self.engines['easy'].readtext(image_path)
            ocr_results = []
            
            for bbox_points, text, confidence in result:
                # Convert bbox points to x1,y1,x2,y2 format
                x_coords = [point[0] for point in bbox_points]
                y_coords = [point[1] for point in bbox_points]
                bbox = (int(min(x_coords)), int(min(y_coords)), 
                       int(max(x_coords)), int(max(y_coords)))
                
                ocr_results.append(OCRResult(text, confidence, bbox))
            
            return ocr_results
        except Exception as e:
            print_with_color(f"EasyOCR error: {e}", "red")
            return []
    
    def extract_text_tesseract(self, image_path: str) -> List[OCRResult]:
        """Extract text using Tesseract"""
        if 'tesseract' not in self.engines:
            return []
        
        try:
            img = cv2.imread(image_path)
            if img is None:
                return []
            
            # Get detailed output
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            ocr_results = []
            
            n_boxes = len(data['text'])
            for i in range(n_boxes):
                text = data['text'][i].strip()
                conf = float(data['conf'][i])
                
                if text and conf > 30:  # Filter low confidence results
                    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                    bbox = (x, y, x + w, y + h)
                    ocr_results.append(OCRResult(text, conf/100.0, bbox))
            
            return ocr_results
        except Exception as e:
            print_with_color(f"Tesseract error: {e}", "red")
            return []
    
    def recognize_captcha(self, image_path: str, preprocess: bool = True) -> Dict[str, any]:
        """
        Recognize CAPTCHA text using multiple OCR engines
        Returns the best result with consensus
        """
        print_with_color(f"开始识别验证码: {image_path}", "blue")
        
        # Preprocess image if requested
        processed_image = image_path
        if preprocess:
            processed_image = self.preprocess_captcha_image(image_path)
            print_with_color(f"图像预处理完成: {processed_image}", "green")
        
        # Try all available engines
        all_results = {}
        
        if 'paddle' in self.engines:
            paddle_results = self.extract_text_paddle(processed_image)
            if paddle_results:
                all_results['paddle'] = paddle_results
                print_with_color(f"PaddleOCR识别结果: {[r.text for r in paddle_results]}", "white")
        
        if 'easy' in self.engines:
            easy_results = self.extract_text_easy(processed_image)
            if easy_results:
                all_results['easy'] = easy_results
                print_with_color(f"EasyOCR识别结果: {[r.text for r in easy_results]}", "white")
        
        if 'tesseract' in self.engines:
            tesseract_results = self.extract_text_tesseract(processed_image)
            if tesseract_results:
                all_results['tesseract'] = tesseract_results
                print_with_color(f"Tesseract识别结果: {[r.text for r in tesseract_results]}", "white")
        
        # Find consensus or best result
        final_result = self._get_best_result(all_results)
        
        return {
            'text': final_result['text'],
            'confidence': final_result['confidence'],
            'bbox': final_result.get('bbox'),
            'engine': final_result['engine'],
            'all_results': all_results,
            'processed_image': processed_image
        }
    
    def _get_best_result(self, all_results: Dict[str, List[OCRResult]]) -> Dict[str, any]:
        """Get the best OCR result from multiple engines"""
        if not all_results:
            return {'text': '', 'confidence': 0.0, 'engine': 'none'}
        
        # Collect all text results
        text_candidates = []
        for engine, results in all_results.items():
            for result in results:
                # Clean up the text
                cleaned_text = self._clean_captcha_text(result.text)
                if cleaned_text:
                    text_candidates.append({
                        'text': cleaned_text,
                        'confidence': result.confidence,
                        'engine': engine,
                        'bbox': result.bbox
                    })
        
        if not text_candidates:
            return {'text': '', 'confidence': 0.0, 'engine': 'none'}
        
        # Sort by confidence
        text_candidates.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Check for consensus among top results
        if len(text_candidates) >= 2:
            top_text = text_candidates[0]['text']
            for candidate in text_candidates[1:]:
                if candidate['text'] == top_text:
                    # Found consensus
                    return candidate
        
        # Return highest confidence result
        return text_candidates[0]
    
    def _clean_captcha_text(self, text: str) -> str:
        """Clean OCR result for CAPTCHA text"""
        if not text:
            return ""
        
        # Remove common OCR artifacts
        cleaned = re.sub(r'[^\w\d]', '', text)  # Keep only alphanumeric
        cleaned = cleaned.strip()
        
        # Filter out very short or very long results (typical CAPTCHA is 4-8 chars)
        if len(cleaned) < 2 or len(cleaned) > 10:
            return ""
        
        return cleaned
    
    def extract_text_regions(self, image_path: str) -> List[OCRResult]:
        """Extract all text regions from an image"""
        all_regions = []
        
        # Try each engine and combine results
        engines_to_try = ['paddle', 'easy', 'tesseract']
        
        for engine_name in engines_to_try:
            if engine_name == 'paddle' and 'paddle' in self.engines:
                results = self.extract_text_paddle(image_path)
            elif engine_name == 'easy' and 'easy' in self.engines:
                results = self.extract_text_easy(image_path)
            elif engine_name == 'tesseract' and 'tesseract' in self.engines:
                results = self.extract_text_tesseract(image_path)
            else:
                continue
            
            all_regions.extend(results)
        
        # Remove duplicates and sort by confidence
        unique_regions = []
        for region in all_regions:
            is_duplicate = False
            for existing in unique_regions:
                if (abs(region.bbox[0] - existing.bbox[0]) < 10 and 
                    abs(region.bbox[1] - existing.bbox[1]) < 10 and
                    region.text.lower() == existing.text.lower()):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_regions.append(region)
        
        return sorted(unique_regions, key=lambda x: x.confidence, reverse=True)
