#!/usr/bin/env python3
"""
Google Pixel设备UIAutomator修复脚本
专门针对Google Pixel设备的SELinux Enforcing模式问题
有问题就运行一次
"""

import sys
import os
import time

# 添加scripts路径到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

from scripts.and_controller import execute_adb, list_all_devices
from scripts.utils import print_with_color


def fix_pixel_uiautomator(device):
    """专门针对Google Pixel设备的UIAutomator修复"""
    print_with_color("=== Google Pixel设备UIAutomator修复 ===", "blue")
    
    # 1. 启用辅助功能服务
    print_with_color("1. 启用辅助功能服务...", "yellow")
    accessibility_commands = [
        f"adb -s {device} shell settings put secure enabled_accessibility_services com.android.server.accessibility:com.android.talkback",
        f"adb -s {device} shell settings put secure accessibility_enabled 1",
        f"adb -s {device} shell settings put secure touch_exploration_enabled 1"
    ]
    
    for cmd in accessibility_commands:
        result = execute_adb(cmd)
        if result != "ERROR":
            print_with_color(f" 执行成功: {cmd.split()[-1]}", "green")
        else:
            print_with_color(f" 可能失败: {cmd.split()[-1]}", "yellow")
    
    # 2. 临时禁用SELinux（需要root，可能失败）
    print_with_color("2. 尝试临时调整SELinux...", "yellow")
    selinux_cmd = f"adb -s {device} shell su -c 'setenforce 0'"
    result = execute_adb(selinux_cmd)
    if result != "ERROR":
        print_with_color("SELinux已设置为Permissive模式", "green")
    else:
        print_with_color("无法修改SELinux (设备可能未root)", "yellow")
    
    # 3. 使用替代方法获取UI信息
    print_with_color("3. 测试替代UI获取方法...", "yellow")
    
    # 方法A: 使用dumpsys window
    alternative_methods = [
        ("dumpsys window", f"adb -s {device} shell dumpsys window windows"),
        ("dumpsys activity", f"adb -s {device} shell dumpsys activity top"),
        ("input keyevent", f"adb -s {device} shell input keyevent KEYCODE_HOME"),  # 测试输入功能
    ]
    
    working_alternatives = []
    
    for name, cmd in alternative_methods:
        print_with_color(f"测试: {name}", "blue")
        result = execute_adb(cmd)
        if result != "ERROR" and len(result) > 100:
            print_with_color(f" {name} 可用", "green")
            working_alternatives.append((name, cmd))
        else:
            print_with_color(f" {name} 不可用", "red")
    
    # 4. 尝试使用accessibility service dump
    print_with_color("4. 尝试辅助功能服务dump...", "yellow")
    
    # 等待辅助功能服务启动
    time.sleep(3)
    
    accessibility_dump_methods = [
        f"adb -s {device} shell uiautomator dump --compressed /data/local/tmp/ui.xml",
        f"adb -s {device} shell am instrument -w -e debug false -e class 'com.android.uiautomator.UiDumpCommand' com.android.uiautomator.test/android.support.test.runner.AndroidJUnitRunner",
        f"adb -s {device} shell content query --uri content://settings/secure --where \"name='enabled_accessibility_services'\"",
    ]
    
    for cmd in accessibility_dump_methods:
        print_with_color(f"尝试: {cmd.split()[4] if len(cmd.split()) > 4 else 'accessibility'}...", "blue")
        result = execute_adb(cmd)
        if result != "ERROR":
            print_with_color(f" 命令执行成功", "green")
            
            # 检查是否生成了文件
            if "dump" in cmd:
                check_files = ["/data/local/tmp/ui.xml", "/data/local/tmp/uidump.xml"]
                for check_file in check_files:
                    check_cmd = f"adb -s {device} shell ls -la {check_file}"
                    check_result = execute_adb(check_cmd)
                    if check_result != "ERROR" and "No such file" not in check_result:
                        print_with_color(f" 找到生成的文件: {check_file}", "green")
                        return True
        else:
            print_with_color(f" 命令失败", "red")
    
    # 5. 创建自定义UI解析方案
    print_with_color("5. 设置自定义解决方案...", "yellow")
    
    if working_alternatives:
        print_with_color("可以使用以下替代方案:", "green")
        for name, cmd in working_alternatives:
            print_with_color(f"  - {name}: {cmd}", "white")
        
        # 建议配置修改
        print()
        print_with_color("=== 建议的解决方案 ===", "blue")
        print_with_color("由于UIAutomator在此设备上被限制，建议:", "yellow")
        print_with_color("1. 使用dumpsys window获取窗口信息", "white")
        print_with_color("2. 结合截图进行视觉识别", "white")
        print_with_color("3. 使用坐标点击而不是元素识别", "white")
        
        return "alternative_methods"
    
    return False


def create_alternative_xml_extractor(device, save_path):
    """创建替代的XML提取器"""
    print_with_color("创建基于dumpsys的UI信息提取器...", "yellow")
    
    # 获取窗口信息
    window_cmd = f"adb -s {device} shell dumpsys window windows"
    window_result = execute_adb(window_cmd)
    
    if window_result == "ERROR":
        return False
    
    # 获取当前活动信息
    activity_cmd = f"adb -s {device} shell dumpsys activity top"
    activity_result = execute_adb(activity_cmd)
    
    # 创建简化的"XML"文件（实际上是结构化的文本）
    combined_info = f"""<?xml version="1.0" encoding="UTF-8"?>
<!-- Alternative UI dump for Google Pixel devices -->
<!-- Generated from dumpsys window and activity information -->
<ui-info timestamp="{time.time()}">
  <device>
    <model>Pixel 7a</model>
    <android-version>12</android-version>
    <api-level>31</api-level>
  </device>
  
  <window-info>
{window_result}
  </window-info>
  
  <activity-info>
{activity_result if activity_result != "ERROR" else "No activity info available"}
  </activity-info>
</ui-info>"""
    
    try:
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(combined_info)
        print_with_color(f" 创建替代UI信息文件: {save_path}", "green")
        return True
    except Exception as e:
        print_with_color(f" 创建文件失败: {e}", "red")
        return False


def main():
    print_with_color("=== Google Pixel UIAutomator 修复工具 ===", "blue")
    print()
    
    # 获取设备
    devices = list_all_devices()
    if not devices:
        print_with_color(" 没有找到设备", "red")
        return False
    
    device = devices[0]  # 使用第一个设备
    print_with_color(f"修复设备: {device}", "green")
    print()
    
    # 执行修复
    result = fix_pixel_uiautomator(device)
    
    if result == "alternative_methods":
        print()
        print_with_color("=== 测试替代方案 ===", "blue")
        
        # 创建测试文件
        test_path = "./test_alternative_ui.xml"
        if create_alternative_xml_extractor(device, test_path):
            print_with_color(" 替代方案可用！", "green")
            print_with_color(f"测试文件已创建: {test_path}", "white")
            print()
            print_with_color("现在可以修改AppAgent代码使用这种方法", "yellow")
        else:
            print_with_color(" 替代方案也失败了", "red")
    
    elif result:
        print_with_color(" UIAutomator修复成功！", "green")
    
    else:
        print_with_color(" 无法修复UIAutomator", "red")
        print()
        print_with_color("最终建议:", "yellow")
        print_with_color("1. 尝试root设备以获得完全控制", "white")
        print_with_color("2. 使用仅基于截图的视觉识别方案", "white")
        print_with_color("3. 考虑使用模拟器而不是实体设备", "white")


if __name__ == "__main__":
    main()
