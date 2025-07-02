#!/usr/bin/env python3
"""
安装增强验证码检测系统的依赖项
"""

import subprocess
import sys
import os
from scripts.utils import print_with_color


def install_package(package_name, description="", use_user=False, force_reinstall=False):
    """安装Python包"""
    try:
        print_with_color(f"正在安装 {package_name}...", "yellow")
        if description:
            print_with_color(f"  {description}", "white")
        
        # 构建安装命令
        cmd = [sys.executable, "-m", "pip", "install"]
        
        # 添加用户模式安装选项
        if use_user:
            cmd.append("--user")
            print_with_color("  使用用户模式安装", "white")
        
        # 添加强制重装选项
        if force_reinstall:
            cmd.extend(["--force-reinstall", "--no-deps"])
            print_with_color("  强制重新安装", "white")
        
        # 添加包名
        cmd.append(package_name)
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print_with_color(f"✅ {package_name} 安装成功", "green")
            return True
        else:
            print_with_color(f"❌ {package_name} 安装失败: {result.stderr}", "red")
            
            # 如果是权限问题且还没有使用用户模式，尝试用户模式安装
            if "WinError 5" in result.stderr or "拒绝访问" in result.stderr or "Permission denied" in result.stderr:
                if not use_user:
                    print_with_color(f"⚠️ 检测到权限问题，尝试用户模式安装 {package_name}...", "yellow")
                    return install_package(package_name, description, use_user=True)
            
            return False
    except Exception as e:
        print_with_color(f"❌ 安装 {package_name} 时出错: {e}", "red")
        return False


def check_system_requirements():
    """检查系统要求"""
    print_with_color("=== 检查系统要求 ===", "blue")
    
    # 检查Python版本
    python_version = sys.version_info
    print_with_color(f"Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}", "white")
    
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print_with_color("❌ 需要Python 3.8或更高版本", "red")
        return False
    
    print_with_color("✅ Python版本符合要求", "green")
    return True


def install_core_dependencies():
    """安装核心依赖项"""
    print_with_color("\n=== 安装核心依赖项 ===", "blue")
    
    # 检查管理员权限
    is_admin = check_admin_privileges()
    if is_admin:
        print_with_color("✅ 检测到管理员权限", "green")
    else:
        print_with_color("⚠️ 未检测到管理员权限，将使用用户模式安装", "yellow")
    
    # 先处理OpenCV冲突
    opencv_success = handle_opencv_conflict()
    
    core_packages = [
        ("torch", "PyTorch深度学习框架"),
        ("torchvision", "PyTorch计算机视觉库"), 
        ("numpy", "数值计算库"),
        ("pillow", "图像处理库"),
        ("matplotlib", "绘图库")
    ]
    
    success_count = 1 if opencv_success else 0  # OpenCV已经处理过了
    
    for package, description in core_packages:
        if install_with_fallback(package, description):
            success_count += 1
    
    total_packages = len(core_packages) + 1  # 包括OpenCV
    print_with_color(f"\n核心依赖项安装结果: {success_count}/{total_packages}", "cyan")
    return success_count >= total_packages - 1  # 允许一个包失败


def install_ocr_dependencies():
    """安装OCR相关依赖项"""
    print_with_color("\n=== 安装OCR依赖项 ===", "blue")
    
    # 特殊处理PaddlePaddle和PaddleOCR
    print_with_color("安装PaddlePaddle和PaddleOCR (这可能需要一些时间)...", "blue")
    
    # 先安装PaddlePaddle CPU版本
    paddle_success = False
    try:
        print_with_color("正在安装PaddlePaddle CPU版本...", "yellow")
        # 使用清华源安装paddlepaddle
        cmd = [sys.executable, "-m", "pip", "install", "paddlepaddle", "--user", 
               "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print_with_color("✅ PaddlePaddle 安装成功", "green")
            paddle_success = True
        else:
            print_with_color(f"PaddlePaddle安装失败，尝试其他方式: {result.stderr[:200]}", "yellow")
    except Exception as e:
        print_with_color(f"PaddlePaddle安装异常: {e}", "yellow")
    
    # 安装PaddleOCR
    paddleocr_success = False
    if paddle_success:
        paddleocr_success = install_with_fallback("paddleocr", "百度PaddleOCR文字识别库")
    else:
        print_with_color("⚠️ 跳过PaddleOCR安装 (PaddlePaddle安装失败)", "yellow")
    
    # 安装其他OCR引擎
    ocr_packages = [
        ("easyocr", "EasyOCR文字识别库"),
        ("pytesseract", "Tesseract OCR Python接口")
    ]
    
    success_count = 1 if paddleocr_success else 0
    
    for package, description in ocr_packages:
        if install_with_fallback(package, description):
            success_count += 1
    
    total_packages = len(ocr_packages) + 1  # 包括PaddleOCR
    print_with_color(f"\nOCR依赖项安装结果: {success_count}/{total_packages}", "cyan")
    
    if success_count > 0:
        print_with_color("\n📋 OCR引擎安装提示:", "blue")
        if paddleocr_success:
            print_with_color("1. ✅ PaddleOCR: 首次使用时会自动下载模型", "white")
        if success_count > (1 if paddleocr_success else 0):
            print_with_color("2. ✅ EasyOCR: 首次使用时会自动下载模型", "white")
            print_with_color("3. ⚠️ Tesseract: 需要单独安装Tesseract可执行文件", "white")
            print_with_color("   Windows下载: https://github.com/UB-Mannheim/tesseract/wiki", "white")
        
        print_with_color("\n💡 如果PaddleOCR安装失败，系统仍可使用其他OCR引擎", "yellow")
    
    return success_count > 0


def install_omni_parser_dependencies():
    """安装OmniParser相关依赖项"""
    print_with_color("\n=== 安装OmniParser依赖项 ===", "blue")
    
    omni_packages = [
        ("ultralytics", "YOLOv8目标检测库"),
        ("transformers", "Hugging Face Transformers库"),
        ("scipy", "科学计算库"),
        ("scikit-image", "图像处理库")
    ]
    
    success_count = 0
    for package, description in omni_packages:
        if install_with_fallback(package, description):
            success_count += 1
    
    print_with_color(f"\nOmniParser依赖项安装结果: {success_count}/{len(omni_packages)}", "cyan")
    
    if success_count > 0:
        print_with_color("\n📋 OmniParser安装提示:", "blue")
        print_with_color("1. 首次运行时会自动下载YOLO模型", "white")
        print_with_color("2. 如果需要GPU加速，请安装CUDA版本的PyTorch", "white")
        if success_count < len(omni_packages):
            print_with_color("3. ⚠️ 部分组件安装失败，但基本功能仍可使用", "yellow")
    
    return success_count > 0


def verify_installation():
    """验证安装"""
    print_with_color("\n=== 验证安装 ===", "blue")
    
    test_imports = [
        ("cv2", "OpenCV"),
        ("numpy", "NumPy"),
        ("PIL", "Pillow"),
        ("torch", "PyTorch"),
        ("torchvision", "TorchVision")
    ]
    
    optional_imports = [
        ("paddleocr", "PaddleOCR"),
        ("easyocr", "EasyOCR"),
        ("pytesseract", "Tesseract"),
        ("ultralytics", "Ultralytics")
    ]
    
    # 测试必需的导入
    print_with_color("检查必需组件:", "yellow")
    required_success = True
    for module, name in test_imports:
        try:
            __import__(module)
            print_with_color(f"✅ {name}", "green")
        except ImportError:
            print_with_color(f"❌ {name}", "red")
            required_success = False
    
    # 测试可选的导入
    print_with_color("\n检查可选组件:", "yellow")
    optional_count = 0
    for module, name in optional_imports:
        try:
            __import__(module)
            print_with_color(f"✅ {name}", "green")
            optional_count += 1
        except ImportError:
            print_with_color(f"⚠️ {name} (可选)", "yellow")
    
    # 总结
    print_with_color(f"\n安装验证结果:", "cyan")
    print_with_color(f"必需组件: {'全部就绪' if required_success else '存在问题'}", "green" if required_success else "red")
    print_with_color(f"可选组件: {optional_count}/{len(optional_imports)} 可用", "white")
    
    return required_success


def check_admin_privileges():
    """检查是否有管理员权限"""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False


def install_with_fallback(package_name, description=""):
    """使用多种方式尝试安装包"""
    print_with_color(f"尝试安装 {package_name}...", "yellow")
    
    # 方法1: 标准安装
    if install_package(package_name, description):
        return True
    
    print_with_color(f"标准安装失败，尝试其他方法...", "yellow")
    
    # 方法2: 用户模式安装
    print_with_color("尝试用户模式安装...", "white")
    if install_package(package_name, description, use_user=True):
        return True
    
    # 方法3: 升级pip后重试
    print_with_color("尝试升级pip后重试...", "white")
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "--user"], 
                   capture_output=True)
    if install_package(package_name, description, use_user=True):
        return True
    
    # 方法4: 使用国内镜像源
    print_with_color("尝试使用国内镜像源...", "white")
    mirrors = [
        "-i https://pypi.tuna.tsinghua.edu.cn/simple",
        "-i https://pypi.douban.com/simple/",
        "-i https://mirrors.aliyun.com/pypi/simple/"
    ]
    
    for mirror in mirrors:
        try:
            cmd = [sys.executable, "-m", "pip", "install", "--user"] + mirror.split() + [package_name]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print_with_color(f"✅ {package_name} 使用镜像源安装成功", "green")
                return True
        except:
            continue
    
    print_with_color(f"❌ {package_name} 所有安装方法都失败了", "red")
    return False


def handle_opencv_conflict():
    """处理OpenCV版本冲突问题"""
    print_with_color("检查OpenCV安装...", "blue")
    
    try:
        import cv2
        print_with_color(f"✅ OpenCV已安装，版本: {cv2.__version__}", "green")
        return True
    except ImportError:
        print_with_color("OpenCV未安装，开始安装...", "yellow")
        
        # 先尝试卸载可能冲突的包
        conflicting_packages = ["opencv-python", "opencv-contrib-python", "opencv-python-headless"]
        for pkg in conflicting_packages:
            subprocess.run([sys.executable, "-m", "pip", "uninstall", pkg, "-y", "--user"], 
                          capture_output=True)
        
        # 重新安装opencv-python
        return install_with_fallback("opencv-python", "OpenCV计算机视觉库")
    except Exception as e:
        print_with_color(f"OpenCV检查失败: {e}", "red")
        return False


def show_installation_tips():
    """显示安装提示和故障排除建议"""
    print_with_color("\n=== 安装提示和故障排除 ===", "blue")
    
    # 检查是否是管理员权限
    is_admin = check_admin_privileges()
    
    if not is_admin:
        print_with_color("💡 权限建议:", "yellow")
        print_with_color("1. 以管理员身份运行命令提示符或PowerShell", "white")
        print_with_color("2. 右键点击命令提示符 -> '以管理员身份运行'", "white")
        print_with_color("3. 或者使用 --user 选项安装到用户目录", "white")
        print_with_color("4. 当前脚本会自动尝试用户模式安装", "green")
    
    print_with_color("\n🔧 常见问题解决方案:", "blue")
    print_with_color("1. 权限问题 (WinError 5):", "white")
    print_with_color("   - 使用管理员权限运行", "white")
    print_with_color("   - 或者脚本会自动使用 --user 选项", "white")
    
    print_with_color("2. 网络问题:", "white")
    print_with_color("   - 脚本会自动尝试国内镜像源", "white")
    print_with_color("   - 清华源、豆瓣源、阿里云源", "white")
    
    print_with_color("3. OpenCV冲突:", "white")
    print_with_color("   - 脚本会自动处理版本冲突", "white")
    print_with_color("   - 卸载冲突包后重新安装", "white")
    
    print_with_color("4. PaddlePaddle安装:", "white")
    print_with_color("   - 使用CPU版本，兼容性更好", "white")
    print_with_color("   - 如果失败会跳过，使用其他OCR引擎", "white")


def main():
    """主安装流程"""
    print_with_color("🚀 开始安装增强验证码检测系统依赖项", "green")
    
    # 显示安装提示
    show_installation_tips()
    
    # 检查系统要求
    if not check_system_requirements():
        print_with_color("❌ 系统要求不满足，安装终止", "red")
        return False
    
    # 安装依赖项
    print_with_color("\n开始安装依赖项，请耐心等待...", "blue")
    core_success = install_core_dependencies()
    ocr_success = install_ocr_dependencies()
    omni_success = install_omni_parser_dependencies()
    
    # 验证安装
    verify_success = verify_installation()
    
    # 总结
    print_with_color("\n=== 安装总结 ===", "blue")
    if core_success and verify_success:
        print_with_color("🎉 核心组件安装成功！增强验证码检测系统基本可用", "green")
        print_with_color("\n下一步:", "blue")
        print_with_color("1. 运行 python test_enhanced_captcha.py 测试系统", "white")
        print_with_color("2. 查看生成的检测结果和标注图片", "white")
        print_with_color("3. 根据需要调整config.yaml中的配置", "white")
        
        # 详细的组件状态
        print_with_color("\n📊 组件安装状态:", "cyan")
        print_with_color(f"✅ 核心组件: {'成功' if core_success else '失败'}", "green" if core_success else "red")
        print_with_color(f"{'✅' if ocr_success else '⚠️'} OCR引擎: {'成功' if ocr_success else '部分成功'}", "green" if ocr_success else "yellow")
        print_with_color(f"{'✅' if omni_success else '⚠️'} OmniParser: {'成功' if omni_success else '部分成功'}", "green" if omni_success else "yellow")
        
        if not ocr_success:
            print_with_color("\n⚠️ OCR注意事项:", "yellow")
            print_with_color("- 部分OCR引擎安装失败，但系统仍可使用可用的引擎", "white")
            print_with_color("- 如需完整功能，请手动安装PaddleOCR或EasyOCR", "white")
            
        if not omni_success:
            print_with_color("\n⚠️ OmniParser注意事项:", "yellow")
            print_with_color("- 部分视觉检测组件安装失败", "white")
            print_with_color("- 系统仍可使用XML检测和OCR功能", "white")
        
        return True
    else:
        print_with_color("❌ 安装过程中遇到关键问题", "red")
        print_with_color("\n🆘 故障排除建议:", "blue")
        print_with_color("1. 以管理员身份重新运行此脚本", "white")
        print_with_color("2. 检查网络连接是否正常", "white")
        print_with_color("3. 手动安装失败的包:", "white")
        print_with_color("   pip install --user <package_name>", "white")
        print_with_color("4. 使用国内镜像源:", "white")
        print_with_color("   pip install -i https://pypi.tuna.tsinghua.edu.cn/simple <package_name>", "white")
        return False


if __name__ == "__main__":
    success = main()
    
    if success:
        print_with_color("\n✨ 安装完成！现在可以使用增强验证码检测功能了", "green")
    else:
        print_with_color("\n💔 安装未完全成功，请根据提示进行故障排除", "red")
        sys.exit(1)
