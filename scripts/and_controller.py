import os
import subprocess
import xml.etree.ElementTree as ET

from .config import load_config
from .utils import print_with_color


configs = load_config()


class AndroidElement:
    def __init__(self, uid, bbox, attrib):
        self.uid = uid
        self.bbox = bbox
        self.attrib = attrib


def execute_adb(adb_command):
    # print(adb_command)
    try:
        result = subprocess.run(adb_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
        if result.returncode == 0:
            return result.stdout.strip() if result.stdout else ""
        print_with_color(f"Command execution failed: {adb_command}", "red")
        if result.stderr:
            print_with_color(result.stderr, "red")
        return "ERROR"
    except Exception as e:
        print_with_color(f"Exception executing command: {adb_command}", "red")
        print_with_color(str(e), "red")
        return "ERROR"


def list_all_devices():
    adb_command = "adb devices"
    device_list = []
    result = execute_adb(adb_command)
    if result != "ERROR":
        devices = result.split("\n")[1:]
        for d in devices:
            device_list.append(d.split()[0])

    return device_list


def get_id_from_element(elem):
    bounds = elem.attrib["bounds"][1:-1].split("][")
    x1, y1 = map(int, bounds[0].split(","))
    x2, y2 = map(int, bounds[1].split(","))
    elem_w, elem_h = x2 - x1, y2 - y1
    if "resource-id" in elem.attrib and elem.attrib["resource-id"]:
        elem_id = elem.attrib["resource-id"].replace(":", ".").replace("/", "_")
    else:
        elem_id = f"{elem.attrib['class']}_{elem_w}_{elem_h}"
    if "content-desc" in elem.attrib and elem.attrib["content-desc"] and len(elem.attrib["content-desc"]) < 20:
        content_desc = elem.attrib['content-desc'].replace("/", "_").replace(" ", "").replace(":", "_")
        elem_id += f"_{content_desc}"
    return elem_id


def traverse_tree(xml_path, elem_list, attrib, add_index=False):
    path = []
    for event, elem in ET.iterparse(xml_path, ['start', 'end']):
        if event == 'start':
            path.append(elem)
            if attrib in elem.attrib and elem.attrib[attrib] == "true":
                parent_prefix = ""
                if len(path) > 1:
                    parent_prefix = get_id_from_element(path[-2])
                bounds = elem.attrib["bounds"][1:-1].split("][")
                x1, y1 = map(int, bounds[0].split(","))
                x2, y2 = map(int, bounds[1].split(","))
                center = (x1 + x2) // 2, (y1 + y2) // 2
                elem_id = get_id_from_element(elem)
                if parent_prefix:
                    elem_id = parent_prefix + "_" + elem_id
                if add_index:
                    elem_id += f"_{elem.attrib['index']}"
                close = False
                for e in elem_list:
                    bbox = e.bbox
                    center_ = (bbox[0][0] + bbox[1][0]) // 2, (bbox[0][1] + bbox[1][1]) // 2
                    dist = (abs(center[0] - center_[0]) ** 2 + abs(center[1] - center_[1]) ** 2) ** 0.5
                    if dist <= configs["MIN_DIST"]:
                        close = True
                        break
                if not close:
                    elem_list.append(AndroidElement(elem_id, ((x1, y1), (x2, y2)), attrib))

        if event == 'end':
            path.pop()


class AndroidController:
    def __init__(self, device, diagnose=False):
        self.device = device
        self.screenshot_dir = configs["ANDROID_SCREENSHOT_DIR"]
        self.xml_dir = configs["ANDROID_XML_DIR"]
        self.width, self.height = self.get_device_size()
        self.backslash = "\\"
        
        if diagnose:
            self.diagnose_device_permissions()

    def get_device_size(self):
        adb_command = f"adb -s {self.device} shell wm size"
        result = execute_adb(adb_command)
        if result != "ERROR":
            return map(int, result.split(": ")[1].split("x"))
        return 0, 0

    def get_screenshot(self, prefix, save_dir):
        cap_command = f"adb -s {self.device} shell screencap -p " \
                      f"{os.path.join(self.screenshot_dir, prefix + '.png').replace(self.backslash, '/')}"
        pull_command = f"adb -s {self.device} pull " \
                       f"{os.path.join(self.screenshot_dir, prefix + '.png').replace(self.backslash, '/')} " \
                       f"{os.path.join(save_dir, prefix + '.png')}"
        
        # First, execute the screenshot command
        print_with_color(f"Executing: {cap_command}", "yellow")
        result = execute_adb(cap_command)
        if result == "ERROR":
            print_with_color("Primary screenshot method failed, trying fallback methods", "yellow")
            return self.get_screenshot_fallback(prefix, save_dir)
        
        # Wait a moment for the file to be written
        import time
        time.sleep(1)
        
        # Check if the screenshot file exists on the device before pulling
        check_command = f"adb -s {self.device} shell ls " \
                       f"{os.path.join(self.screenshot_dir, prefix + '.png').replace(self.backslash, '/')}"
        check_result = execute_adb(check_command)
        if check_result == "ERROR" or "No such file" in check_result:
            print_with_color(f"Screenshot file does not exist on device: {os.path.join(self.screenshot_dir, prefix + '.png')}", "red")
            print_with_color("Trying fallback methods", "yellow")
            return self.get_screenshot_fallback(prefix, save_dir)
        
        # Now pull the file
        print_with_color(f"Executing: {pull_command}", "yellow")
        result = execute_adb(pull_command)
        if result != "ERROR":
            local_path = os.path.join(save_dir, prefix + ".png")
            if os.path.exists(local_path):
                return local_path
            else:
                print_with_color(f"Failed to pull screenshot to local path: {local_path}", "red")
                return self.get_screenshot_fallback(prefix, save_dir)
        
        # If all else fails, try fallback
        print_with_color("Primary screenshot method failed, trying fallback methods", "yellow")
        return self.get_screenshot_fallback(prefix, save_dir)

    def get_screenshot_fallback(self, prefix, save_dir):
        """Fallback method to get screenshot if the primary method fails"""
        # Try alternative screenshot locations
        alternative_paths = [
            "/data/local/tmp",
            "/storage/emulated/0",
            "/storage/emulated/0/Download"
        ]
        
        for alt_path in alternative_paths:
            cap_command = f"adb -s {self.device} shell screencap -p " \
                          f"{alt_path}/{prefix}.png"
            pull_command = f"adb -s {self.device} pull " \
                           f"{alt_path}/{prefix}.png " \
                           f"{os.path.join(save_dir, prefix + '.png')}"
            
            print_with_color(f"Trying alternative screenshot path: {alt_path}", "yellow")
            result = execute_adb(cap_command)
            if result != "ERROR":
                # Wait a moment for the file to be written
                import time
                time.sleep(1)
                
                # Check if file exists
                check_command = f"adb -s {self.device} shell ls {alt_path}/{prefix}.png"
                check_result = execute_adb(check_command)
                if check_result != "ERROR" and "No such file" not in check_result:
                    # Try to pull the file
                    result = execute_adb(pull_command)
                    if result != "ERROR":
                        local_path = os.path.join(save_dir, prefix + ".png")
                        if os.path.exists(local_path):
                            print_with_color(f"Successfully got screenshot using alternative path: {alt_path}", "green")
                            return local_path
        
        print_with_color("All alternative screenshot methods failed", "red")
        return "ERROR"

    def get_xml(self, prefix, save_dir):
        dump_command = f"adb -s {self.device} shell uiautomator dump " \
                       f"{os.path.join(self.xml_dir, prefix + '.xml').replace(self.backslash, '/')}"
        pull_command = f"adb -s {self.device} pull " \
                       f"{os.path.join(self.xml_dir, prefix + '.xml').replace(self.backslash, '/')} " \
                       f"{os.path.join(save_dir, prefix + '.xml')}"
        
        # First, execute the dump command
        print_with_color(f"Executing: {dump_command}", "yellow")
        result = execute_adb(dump_command)
        if result == "ERROR":
            print_with_color("Primary XML dump method failed, trying fallback methods", "yellow")
            fallback_result = self.get_xml_fallback(prefix, save_dir)
            if fallback_result != "ERROR":
                return fallback_result
            # 如果常规备选方法也失败，尝试修复UIAutomator服务
            print_with_color("常规方法都失败了，尝试修复UIAutomator服务", "yellow")
            self.fix_uiautomator_service()
            return self.advanced_xml_dump(prefix, save_dir)
        
        # Wait a moment for the file to be written
        import time
        time.sleep(1)
        
        # Check if the XML file exists on the device before pulling
        check_command = f"adb -s {self.device} shell ls " \
                       f"{os.path.join(self.xml_dir, prefix + '.xml').replace(self.backslash, '/')}"
        check_result = execute_adb(check_command)
        if check_result == "ERROR" or "No such file" in check_result:
            print_with_color(f"XML file does not exist on device: {os.path.join(self.xml_dir, prefix + '.xml')}", "red")
            print_with_color("Trying fallback methods", "yellow")
            fallback_result = self.get_xml_fallback(prefix, save_dir)
            if fallback_result != "ERROR":
                return fallback_result
            # 如果常规备选方法也失败，尝试修复UIAutomator服务
            print_with_color("常规方法都失败了，尝试修复UIAutomator服务", "yellow")
            self.fix_uiautomator_service()
            return self.advanced_xml_dump(prefix, save_dir)
        
        # Now pull the file
        print_with_color(f"Executing: {pull_command}", "yellow")
        result = execute_adb(pull_command)
        if result != "ERROR":
            local_path = os.path.join(save_dir, prefix + ".xml")
            if os.path.exists(local_path):
                return local_path
            else:
                print_with_color(f"Failed to pull XML file to local path: {local_path}", "red")
                fallback_result = self.get_xml_fallback(prefix, save_dir)
                if fallback_result != "ERROR":
                    return fallback_result
                # 如果常规备选方法也失败，尝试修复UIAutomator服务
                print_with_color("常规方法都失败了，尝试修复UIAutomator服务", "yellow")
                self.fix_uiautomator_service()
                return self.advanced_xml_dump(prefix, save_dir)
        
        # If all else fails, try advanced methods
        print_with_color("所有常规方法都失败了，尝试高级方法", "yellow")
        self.fix_uiautomator_service()
        return self.advanced_xml_dump(prefix, save_dir)

    def get_xml_fallback(self, prefix, save_dir):
        """Fallback method to get XML if the primary method fails"""
        # Try alternative dump locations
        alternative_paths = [
            "/data/local/tmp",
            "/storage/emulated/0",
            "/storage/emulated/0/Download"
        ]
        
        for alt_path in alternative_paths:
            dump_command = f"adb -s {self.device} shell uiautomator dump " \
                           f"{alt_path}/{prefix}.xml"
            pull_command = f"adb -s {self.device} pull " \
                           f"{alt_path}/{prefix}.xml " \
                           f"{os.path.join(save_dir, prefix + '.xml')}"
            
            print_with_color(f"Trying alternative path: {alt_path}", "yellow")
            result = execute_adb(dump_command)
            if result != "ERROR":
                # Wait a moment for the file to be written
                import time
                time.sleep(1)
                
                # Check if file exists
                check_command = f"adb -s {self.device} shell ls {alt_path}/{prefix}.xml"
                check_result = execute_adb(check_command)
                if check_result != "ERROR" and "No such file" not in check_result:
                    # Try to pull the file
                    result = execute_adb(pull_command)
                    if result != "ERROR":
                        local_path = os.path.join(save_dir, prefix + ".xml")
                        if os.path.exists(local_path):
                            print_with_color(f"Successfully got XML using alternative path: {alt_path}", "green")
                            return local_path
        
        print_with_color("All alternative XML dump methods failed", "red")
        return "ERROR"

    def back(self):
        adb_command = f"adb -s {self.device} shell input keyevent KEYCODE_BACK"
        ret = execute_adb(adb_command)
        return ret

    def tap(self, x, y):
        adb_command = f"adb -s {self.device} shell input tap {x} {y}"
        ret = execute_adb(adb_command)
        return ret

    def text(self, input_str):
        input_str = input_str.replace(" ", "%s")
        input_str = input_str.replace("'", "")
        adb_command = f"adb -s {self.device} shell input text {input_str}"
        ret = execute_adb(adb_command)
        return ret

    def long_press(self, x, y, duration=1000):
        adb_command = f"adb -s {self.device} shell input swipe {x} {y} {x} {y} {duration}"
        ret = execute_adb(adb_command)
        return ret

    def swipe(self, x, y, direction, dist="medium", quick=False):
        unit_dist = int(self.width / 10)
        if dist == "long":
            unit_dist *= 3
        elif dist == "medium":
            unit_dist *= 2
        if direction == "up":
            offset = 0, -2 * unit_dist
        elif direction == "down":
            offset = 0, 2 * unit_dist
        elif direction == "left":
            offset = -1 * unit_dist, 0
        elif direction == "right":
            offset = unit_dist, 0
        else:
            return "ERROR"
        duration = 100 if quick else 400
        adb_command = f"adb -s {self.device} shell input swipe {x} {y} {x+offset[0]} {y+offset[1]} {duration}"
        ret = execute_adb(adb_command)
        return ret

    def swipe_precise(self, start, end, duration=400):
        start_x, start_y = start
        end_x, end_y = end
        
        adb_command = f"adb -s {self.device} shell input swipe {start_x} {start_y} {end_x} {end_y} {duration}"
        ret = execute_adb(adb_command)
        return ret

    def diagnose_device_permissions(self):
        """Diagnose device permissions and capabilities"""
        print_with_color("Diagnosing device permissions and capabilities...", "yellow")
        
        # Check if device is connected
        devices = list_all_devices()
        if self.device not in devices:
            print_with_color(f"Device {self.device} is not connected or authorized", "red")
            return False
        
        # Check if we can access shell
        shell_test = execute_adb(f"adb -s {self.device} shell echo 'test'")
        if shell_test == "ERROR":
            print_with_color("Cannot access device shell", "red")
            return False
        
        # Check uiautomator service
        uiautomator_test = execute_adb(f"adb -s {self.device} shell dumpsys activity services | grep -i uiautomator")
        print_with_color(f"UIAutomator service status: {uiautomator_test}", "blue")
        
        # Check available directories and permissions
        test_dirs = ["/sdcard", "/data/local/tmp", "/storage/emulated/0", "/storage/emulated/0/Download"]
        for test_dir in test_dirs:
            # Test if directory exists
            dir_check = execute_adb(f"adb -s {self.device} shell ls {test_dir}")
            if dir_check != "ERROR" and "No such file" not in dir_check:
                # Test write permissions
                write_test = execute_adb(f"adb -s {self.device} shell touch {test_dir}/test_permission.txt")
                if write_test != "ERROR":
                    # Clean up test file
                    execute_adb(f"adb -s {self.device} shell rm {test_dir}/test_permission.txt")
                    print_with_color(f"Directory {test_dir}: Accessible and writable", "green")
                else:
                    print_with_color(f"Directory {test_dir}: Accessible but not writable", "yellow")
            else:
                print_with_color(f"Directory {test_dir}: Not accessible", "red")
        
        # Test basic uiautomator functionality
        print_with_color("Testing basic uiautomator functionality...", "yellow")
        temp_xml_test = execute_adb(f"adb -s {self.device} shell uiautomator dump /data/local/tmp/test_ui.xml")
        if temp_xml_test != "ERROR":
            # Check if file was created
            file_check = execute_adb(f"adb -s {self.device} shell ls /data/local/tmp/test_ui.xml")
            if file_check != "ERROR" and "No such file" not in file_check:
                print_with_color("UIAutomator dump test: SUCCESS", "green")
                # Clean up
                execute_adb(f"adb -s {self.device} shell rm /data/local/tmp/test_ui.xml")
                return True
            else:
                print_with_color("UIAutomator dump test: File not created", "red")
        else:
            print_with_color("UIAutomator dump test: FAILED", "red")
        
        return False

    def fix_uiautomator_service(self):
        """尝试修复UIAutomator服务"""
        print_with_color("尝试修复UIAutomator服务...", "yellow")
        
        # 方法1：尝试重启UIAutomator服务
        print_with_color("方法1：重启UIAutomator服务", "blue")
        restart_cmd = f"adb -s {self.device} shell am force-stop com.android.commands.uiautomator"
        result = execute_adb(restart_cmd)
        if result != "ERROR":
            print_with_color("UIAutomator服务重启命令执行成功", "green")
        
        # 方法2：清除UIAutomator缓存
        print_with_color("方法2：清除UIAutomator缓存", "blue")
        clear_cmd = f"adb -s {self.device} shell rm -rf /data/local/tmp/uidump.xml"
        execute_adb(clear_cmd)
        
        # 方法3：尝试启动UIAutomator服务
        print_with_color("方法3：启动UIAutomator服务", "blue")
        start_cmd = f"adb -s {self.device} shell am start -n com.android.commands.uiautomator/.UiAutomatorService"
        execute_adb(start_cmd)
        
        # 方法4：检查并启用必要的服务
        print_with_color("方法4：检查辅助服务", "blue")
        accessibility_cmd = f"adb -s {self.device} shell settings get secure enabled_accessibility_services"
        result = execute_adb(accessibility_cmd)
        print_with_color(f"辅助服务状态: {result}", "blue")
        
        # 方法5：尝试通过不同的方式dump UI
        alternative_methods = [
            "shell uiautomator dump --compressed",
            "shell uiautomator dump /dev/stdout",
            "shell dumpsys window windows",
            "shell dumpsys activity top"
        ]
        
        for i, method in enumerate(alternative_methods, 1):
            print_with_color(f"方法{4+i}：尝试 {method}", "blue")
            test_cmd = f"adb -s {self.device} {method}"
            result = execute_adb(test_cmd)
            if result != "ERROR" and len(result) > 100:  # 假设成功的输出应该比较长
                print_with_color(f"方法{4+i} 可能有效", "green")
                return True
        
        return False

    def advanced_xml_dump(self, prefix, save_dir):
        """高级XML获取方法"""
        print_with_color("尝试高级XML获取方法...", "yellow")
        
        # 方法1：使用stdout直接输出
        print_with_color("尝试直接输出到stdout", "blue")
        stdout_cmd = f"adb -s {self.device} shell uiautomator dump /dev/stdout"
        result = execute_adb(stdout_cmd)
        if result != "ERROR" and "<?xml" in result:
            # 直接保存输出到本地文件
            local_path = os.path.join(save_dir, prefix + ".xml")
            try:
                with open(local_path, 'w', encoding='utf-8') as f:
                    f.write(result)
                print_with_color(f"成功通过stdout获取XML: {local_path}", "green")
                return local_path
            except Exception as e:
                print_with_color(f"保存XML文件失败: {e}", "red")
        
        # 方法2：使用压缩格式
        print_with_color("尝试压缩格式", "blue")
        for path in ["/data/local/tmp", "/sdcard", "/storage/emulated/0"]:
            compressed_cmd = f"adb -s {self.device} shell uiautomator dump --compressed {path}/{prefix}.xml"
            result = execute_adb(compressed_cmd)
            if result != "ERROR":
                import time
                time.sleep(1)
                # 检查文件是否存在
                check_cmd = f"adb -s {self.device} shell ls {path}/{prefix}.xml"
                check_result = execute_adb(check_cmd)
                if check_result != "ERROR" and "No such file" not in check_result:
                    # 尝试拉取文件
                    pull_cmd = f"adb -s {self.device} pull {path}/{prefix}.xml {os.path.join(save_dir, prefix + '.xml')}"