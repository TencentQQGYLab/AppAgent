#!/usr/bin/env python3
"""
测试增强的验证码检测系统
"""

import sys
import os

# 添加scripts路径到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

from scripts.and_controller import AndroidController, list_all_devices
from scripts.captcha_detector import CaptchaDetector
from scripts.ocr_engine import OCREngine
from scripts.omni_parser import OmniParser
from scripts.utils import print_with_color


def test_enhanced_captcha_detection():
    """测试增强的验证码检测系统"""
    print_with_color("=== 测试增强验证码检测系统 ===", "blue")
    
    # 获取设备
    devices = list_all_devices()
    if not devices:
        print_with_color("❌ 没有找到设备", "red")
        return False
    
    device = devices[0]
    print_with_color(f"使用设备: {device}", "green")
    
    # 创建控制器
    controller = AndroidController(device)
    
    # 创建测试目录
    test_dir = "./test_enhanced_captcha"
    os.makedirs(test_dir, exist_ok=True)
    
    # 获取当前屏幕截图和XML
    print_with_color("获取当前屏幕状态...", "yellow")
    screenshot_path = controller.get_screenshot("captcha_test", test_dir)
    xml_path = controller.get_xml("captcha_test", test_dir)
    
    if screenshot_path == "ERROR" or xml_path == "ERROR":
        print_with_color("❌ 无法获取屏幕状态", "red")
        return False
    
    print_with_color("✅ 成功获取屏幕状态", "green")
    print_with_color(f"截图路径: {screenshot_path}", "white")
    print_with_color(f"XML路径: {xml_path}", "white")
    
    # 初始化增强检测器
    print_with_color("\n=== 初始化增强检测组件 ===", "blue")
    
    # 测试OCR引擎
    print_with_color("1. 测试OCR引擎...", "yellow")
    ocr_engine = OCREngine()
    ocr_result = ocr_engine.recognize_captcha(screenshot_path)
    print_with_color(f"OCR识别结果: {ocr_result}", "white")
    
    # 测试OmniParser
    print_with_color("2. 测试OmniParser...", "yellow")
    omni_parser = OmniParser()
    ui_elements = omni_parser.detect_ui_elements(screenshot_path)
    print_with_color(f"OmniParser检测到 {len(ui_elements)} 个UI元素", "white")
    
    # 测试综合验证码检测器
    print_with_color("3. 测试综合验证码检测器...", "yellow")
    captcha_detector = CaptchaDetector()
    detection_results = captcha_detector.detect_captcha_elements(screenshot_path, xml_path, test_dir)
    
    # 显示检测结果
    print_with_color("\n=== 检测结果摘要 ===", "cyan")
    print_with_color(f"XML元素数量: {len(detection_results['xml_elements'])}", "white")
    print_with_color(f"视觉元素数量: {len(detection_results['omni_elements'])}", "white")
    print_with_color(f"OCR文本数量: {len(detection_results['ocr_results'])}", "white")
    print_with_color(f"合并后元素数量: {len(detection_results['combined_elements'])}", "white")
    
    # 验证码分析结果
    captcha_analysis = detection_results['captcha_analysis']
    print_with_color("\n=== 验证码分析结果 ===", "cyan")
    print_with_color(f"是否检测到验证码图像: {captcha_analysis['has_captcha_image']}", "white")
    print_with_color(f"是否检测到输入框: {captcha_analysis['has_input_field']}", "white")
    print_with_color(f"是否检测到提交按钮: {captcha_analysis['has_submit_button']}", "white")
    print_with_color(f"验证码类型: {captcha_analysis['captcha_type']}", "white")
    
    # 显示识别到的文本
    if captcha_analysis['text_content']:
        print_with_color("\n=== 识别到的文本内容 ===", "cyan")
        for text_info in captcha_analysis['text_content']:
            print_with_color(f"文本: '{text_info['text']}' (置信度: {text_info['confidence']:.2f})", "white")
    
    # 显示生成的标注图片
    labeled_images = detection_results['labeled_images']
    if labeled_images:
        print_with_color("\n=== 生成的标注图片 ===", "cyan")
        for label, path in labeled_images.items():
            print_with_color(f"{label}: {path}", "white")
    
    print_with_color(f"\n✅ 测试完成！请查看 {test_dir} 目录中的结果文件", "green")
    return True


def test_specific_captcha_scenarios():
    """测试特定的验证码场景"""
    print_with_color("\n=== 测试特定验证码场景 ===", "blue")
    
    scenarios = [
        "请在应用中找到验证码界面",
        "如果看到输入验证码的界面，请截图测试",
        "如果看到滑动验证码，请截图测试",
        "如果看到点击验证码，请截图测试"
    ]
    
    for scenario in scenarios:
        print_with_color(f"💡 {scenario}", "yellow")
    
    print_with_color("\n手动测试步骤:", "blue")
    print_with_color("1. 在手机上打开包含验证码的应用", "white")
    print_with_color("2. 导航到验证码界面", "white")
    print_with_color("3. 运行此测试脚本", "white")
    print_with_color("4. 查看生成的检测结果和标注图片", "white")


if __name__ == "__main__":
    print_with_color("🚀 开始测试增强验证码检测系统", "green")
    
    success = test_enhanced_captcha_detection()
    
    if success:
        print_with_color("\n🎉 增强验证码检测测试完成！", "green")
        test_specific_captcha_scenarios()
    else:
        print_with_color("\n❌ 测试失败", "red")
        
    print_with_color("\n📋 测试完成后请检查以下内容:", "blue")
    print_with_color("1. OCR是否正确识别了验证码文本", "white")
    print_with_color("2. OmniParser是否检测到了XML中缺失的元素", "white")
    print_with_color("3. 综合检测是否提供了更全面的元素列表", "white")
    print_with_color("4. 验证码类型是否被正确识别", "white")
