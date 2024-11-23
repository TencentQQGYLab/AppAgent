import sys
from typing import Optional
from model import BaseModel, OpenAIModel, QwenModel
from utils import print_with_color


def parse(configs: dict) -> BaseModel:
    mllm: Optional[BaseModel] = None
    if configs["MODEL"] == "OpenAI":
        mllm = OpenAIModel(base_url=configs["OPENAI_API_BASE"],
                           api_key=configs["OPENAI_API_KEY"],
                           model=configs["OPENAI_API_MODEL"],
                           temperature=configs["TEMPERATURE"],
                           max_tokens=configs["MAX_TOKENS"])
    elif configs["MODEL"] == "Qwen":
        mllm = QwenModel(api_key=configs["DASHSCOPE_API_KEY"],
                         model=configs["QWEN_MODEL"])
    else:
        print_with_color(f"ERROR: Unsupported model type {configs['MODEL']}!", "red")
        sys.exit()
    return mllm