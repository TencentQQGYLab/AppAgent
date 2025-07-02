# 增强验证码检测系统使用说明

## 概述

本系统集成了多种先进技术来提高验证码识别和元素检测的准确性：

- **OmniParser**: 使用计算机视觉检测XML中缺失的UI元素
- **多引擎OCR**: 集成PaddleOCR、EasyOCR和Tesseract进行文本识别
- **智能融合**: 将XML解析、视觉检测和文本识别结果智能合并

## 快速开始

### 1. 安装依赖项

```bash
python install_dependencies.py
```

### 2. 配置设置

编辑 `config.yaml` 文件中的增强检测设置：

```yaml
# Enhanced Detection Settings
ENABLE_OMNI_PARSER: true
ENABLE_OCR: true
OCR_CONFIDENCE_THRESHOLD: 0.3
OMNI_PARSER_CONFIDENCE_THRESHOLD: 0.2
CAPTCHA_DETECTION_MODE: "enhanced"
```

### 3. 运行测试

```bash
python test_enhanced_captcha.py
```

## 主要功能

### 1. 增强元素检测

**传统方法局限性**:
- 只能检测XML中明确标记的可交互元素
- 无法识别动态生成或图像中的元素
- 对验证码图片内容无法解析

**增强检测方案**:
- **XML解析**: 检测clickable、focusable等标准属性
- **OmniParser**: 使用YOLO和OpenCV检测视觉元素
- **OCR识别**: 识别图片中的文本内容
- **智能融合**: 去重并优化检测结果

### 2. 多引擎OCR

支持三种OCR引擎，提供更强的文本识别能力：

1. **PaddleOCR**: 百度开源，中英文识别效果好
2. **EasyOCR**: 支持多语言，安装简单
3. **Tesseract**: 经典OCR引擎，配置灵活

系统会自动选择置信度最高的结果。

### 3. OmniParser视觉检测

使用多种计算机视觉方法检测UI元素：

- **YOLO目标检测**: 识别图像中的对象
- **轮廓检测**: 检测矩形边框元素
- **边缘检测**: 识别按钮和输入框
- **模板匹配**: 匹配常见UI模式
- **文本区域检测**: 使用MSER检测文本区域

## 验证码类型支持

### 1. 文本验证码 (Image CAPTCHA)
- 自动识别验证码图片中的文字
- 支持数字、字母、混合验证码
- 图像预处理提高识别率

### 2. 滑动验证码 (Slider CAPTCHA)
- 检测滑动条和目标位置
- 识别需要拖拽的元素

### 3. 点击验证码 (Click CAPTCHA)
- 识别需要点击的目标对象
- 支持"点击所有交通灯"类型验证码

### 4. 旋转验证码 (Rotation CAPTCHA)
- 检测需要旋转的图片
- 识别正确的方向角度

## 使用示例

### 基本使用

```python
from scripts.captcha_detector import CaptchaDetector

# 创建检测器
detector = CaptchaDetector()

# 检测验证码元素
results = detector.detect_captcha_elements(
    screenshot_path="screenshot.png",
    xml_path="layout.xml",
    output_dir="./output"
)

# 查看结果
print(f"检测到 {len(results['combined_elements'])} 个元素")
print(f"验证码类型: {results['captcha_analysis']['captcha_type']}")
```

### 在CaptchaAgent中使用

```python
from agents.captcha_agent import CaptchaAgent

# 创建代理
agent = CaptchaAgent(controller, model, config, work_dir)

# 检测验证码类型
captcha_type = agent.detect_captcha_type(screenshot_path, xml_path)

# 获取任务提示
prompt = agent.get_task_prompt(task_desc, last_act, 
                              screenshot_path=screenshot_path,
                              xml_path=xml_path)
```

## 输出文件说明

系统会生成以下文件帮助调试和分析：

### 标注图片
- `xml_elements_labeled.png`: XML检测元素标注
- `omni_elements_labeled.png`: OmniParser检测元素标注
- `ocr_results_labeled.png`: OCR识别结果标注
- `combined_elements_labeled.png`: 合并后所有元素标注

### 检测报告
- `detection_report.json`: 详细的检测结果JSON报告

### 预处理图片
- `*_preprocessed.png`: OCR预处理后的图片

## 配置选项详解

### OCR设置
```yaml
OCR_ENGINES: ["paddle", "easy", "tesseract"]  # 使用的OCR引擎
OCR_CONFIDENCE_THRESHOLD: 0.3  # 置信度阈值
OCR_PREPROCESS_IMAGES: true    # 是否预处理图片
OCR_MAX_TEXT_LENGTH: 20        # 最大文本长度
```

### OmniParser设置
```yaml
OMNI_PARSER_MODEL: "yolov8n"               # YOLO模型
OMNI_PARSER_DEVICE: "auto"                 # 计算设备
OMNI_PARSER_CONFIDENCE_THRESHOLD: 0.2     # 置信度阈值
OMNI_PARSER_MIN_AREA: 100                 # 最小检测区域
OMNI_PARSER_MAX_AREA: 50000               # 最大检测区域
```

## 故障排除

### 常见问题

1. **OCR引擎初始化失败**
   - 确保已安装对应的Python包
   - 对于Tesseract，需要单独安装可执行文件

2. **YOLO模型下载失败**
   - 检查网络连接
   - 首次运行时会自动下载模型文件

3. **检测结果不理想**
   - 调整置信度阈值
   - 检查图片质量和分辨率
   - 尝试不同的OCR引擎组合

### 调试技巧

1. **查看标注图片**: 检查每个检测方法的结果
2. **分析检测报告**: 查看详细的JSON报告
3. **调整参数**: 根据具体应用调整配置
4. **测试单个组件**: 分别测试OCR和OmniParser

## 性能优化

### 提高检测速度
- 使用GPU加速（如果可用）
- 减少OCR引擎数量
- 调整图片预处理参数

### 提高检测精度
- 使用多个OCR引擎
- 启用图片预处理
- 调整置信度阈值
- 优化OmniParser参数

## 扩展开发

### 添加新的OCR引擎
1. 在`ocr_engine.py`中添加新的提取方法
2. 更新`_initialize_engines`方法
3. 在配置文件中添加新引擎

### 自定义OmniParser模型
1. 在`omni_parser.py`中添加新的检测方法
2. 实现自定义的模型加载和推理
3. 更新元素转换逻辑

### 添加新的验证码类型
1. 在`CaptchaType`枚举中添加新类型
2. 实现对应的检测逻辑
3. 添加相应的提示词模板

## 技术架构

```
增强验证码检测系统
├── OCR引擎 (ocr_engine.py)
│   ├── PaddleOCR
│   ├── EasyOCR
│   └── Tesseract
├── OmniParser (omni_parser.py)
│   ├── YOLO检测
│   ├── OpenCV处理
│   └── 传统CV方法
├── 综合检测器 (captcha_detector.py)
│   ├── 元素融合
│   ├── 结果优化
│   └── 分析报告
└── 验证码代理 (captcha_agent.py)
    ├── 类型识别
    ├── 任务规划
    └── 动作执行
```

## 更新日志

### v1.0.0 (当前版本)
- 集成OmniParser视觉检测
- 添加多引擎OCR支持
- 实现综合验证码检测器
- 支持多种验证码类型
- 提供完整的测试和调试工具

## 联系方式

如有问题或建议，请通过以下方式联系：
- 提交Issue到项目仓库
- 查看详细的错误日志和检测报告
- 参考故障排除章节
