import json
from config import load_config
from model_parser import parse as model_parse

configs = load_config('../config.yaml')
mllm = model_parse(configs)

form = {
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "objects": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "type": {
            "type": "string",
            "description": "The type of the object."
          },
          "color": {
            "type": "string",
            "description": "The color of the object."
          }
        },
        "required": ["type", "color"]
      }
    },
    "count": {
      "type": "integer",
      "description": "The number of objects present in this image."
    }
  },
  "required": ["objects", "count"]
}

prompt = """
Please count the objects present in this picture? Describe the type, color of each object. 
Please respond with the following json format:
%s
""".format(json.dumps(form, indent=2))

prompt = """What is inside this image?
"""

status, rsp = mllm.get_model_response(prompt, ['./image.jpg'], '')
print(status)
print(json.dumps(rsp,indent=2))
