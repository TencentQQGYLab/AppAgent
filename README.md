# AppAgent Extended - 多Agent架构设置指南

## 新架构概述

AppAgent Extended 将原始的AppAgent扩展为支持多种专门任务的agent系统：

- **CAPTCHA Agent**: 专门处理各种验证码
- **Payment Agent**: 处理支付流程（开发中）
- **Quiz Agent**: 处理问答和测验（开发中）
- **General Agent**: 原始的通用AppAgent

## 目录结构

```
AppAgent/
├── agents/                    # 专门的agent模块
│   ├── __init__.py
│   ├── base_agent.py         # 基础Agent类
│   ├── captcha_agent.py      # 验证码Agent
│   ├── captcha_utils.py      # 验证码处理工具
│   ├── payment_agent.py      # 支付Agent（待实现）
│   └── quiz_agent.py         # 答题Agent（待实现）
├── prompts/                   # 提示词模块
│   ├── __init__.py
│   ├── base_prompts.py       # 基础提示词
│   └── captcha_prompts.py    # 验证码相关提示词
├── scripts/                   # 原有脚本（保持不变）
├── agent_runner.py           # 新的多Agent运行器
└── [其他原有文件]
```

## 安装步骤

### 1. 创建新目录结构

```bash
# 在AppAgent根目录下创建新目录
mkdir agents
mkdir prompts

# 将新文件放入对应目录
# agents/目录下：
# - __init__.py
# - base_agent.py
# - captcha_agent.py
# - captcha_utils.py

# prompts/目录下：
# - __init__.py
# - base_prompts.py
# - captcha_prompts.py
```

### 2. 安装额外依赖

```bash
# 验证码处理需要的额外依赖
pip install opencv-python numpy
```

### 3. 修改原有文件

将原来的 `prompts.py` 文件移动到 `scripts/prompts.py`，或者更新导入路径。

## 使用方法

### 运行CAPTCHA Agent

1. **启动Agent运行器**：
```bash
python agent_runner.py
```

2. **选择Agent类型**：
```
Select the type of agent you want to use:
1. CAPTCHA Agent - Handles various types of CAPTCHAs
2. Payment Agent - Handles payment processes (Coming soon)
3. Quiz Agent - Handles quiz and questionnaire (Coming soon)
4. General Agent - Original AppAgent for general tasks

Enter your choice (1-4): 1
```

3. **导航到验证码页面**：
   - 在手机上打开包含验证码的应用页面
   - 按Enter键开始处理

### 命令行参数

```bash
# 直接指定agent类型
python agent_runner.py --agent captcha

# 运行通用agent（原AppAgent）
python agent_runner.py --agent general --app Twitter
```

## CAPTCHA Agent 功能

### 支持的验证码类型

1. **图片验证码**：识别扭曲的文字/数字
2. **滑块验证码**：拖动滑块完成拼图
3. **点击验证码**：点击特定对象（如"点击所有红绿灯"）
4. **旋转验证码**：旋转图片到正确方向

### 工作流程

1. **检测验证码类型**：自动识别屏幕上的验证码类型
2. **应用专门策略**：根据类型使用不同的解决方案
3. **执行操作**：自动完成验证码验证
4. **验证结果**：检查是否成功通过验证

## 扩展新的Agent

要添加新的专门Agent（如PaymentAgent）：

1. **创建新的Agent类**：
```python
# agents/payment_agent.py
from agents.base_agent import BaseAgent

class PaymentAgent(BaseAgent):
    def get_task_prompt(self, task_desc, last_act, **kwargs):
        # 实现支付相关的提示词
        pass
    
    def parse_response(self, response):
        # 解析支付相关的响应
        pass
    
    def execute_action(self, action):
        # 执行支付相关的操作
        pass
    
    def check_task_completion(self, screenshot_path, xml_path):
        # 检查支付是否完成
        pass
```

2. **创建对应的提示词**：
```python
# prompts/payment_prompts.py
PAYMENT_DETECTION_PROMPT = """..."""
PAYMENT_EXECUTION_PROMPT = """..."""
```

3. **在agent_runner.py中注册**：
```python
from agents.payment_agent import PaymentAgent

# 在main()函数中添加：
elif agent_choice == "2":
    run_payment_agent(controller, model, configs, work_dir)
```

## 注意事项

1. **兼容性**：新架构完全兼容原有的AppAgent功能
2. **配置文件**：使用相同的 `config.yaml`
3. **文档生成**：CAPTCHA Agent不需要预先的文档学习阶段
4. **错误处理**：增强了错误处理和重试机制

## 故障排除

### 常见问题

1. **导入错误**：确保正确创建了目录结构和__init__.py文件
2. **验证码识别失败**：
   - 检查截图质量
   - 确保验证码完全可见
   - 尝试调整屏幕亮度

3. **Agent选择错误**：使用 `--agent` 参数直接指定agent类型

### 调试模式

设置环境变量启用详细日志：
```bash
export APPAGENT_DEBUG=1
python agent_runner.py
```

## 未来计划

- [ ] 集成OCR服务提高图片验证码识别率
- [ ] 添加机器学习模型用于对象检测
- [ ] 实现PaymentAgent
- [ ] 实现QuizAgent
- [ ] 添加更多验证码类型支持