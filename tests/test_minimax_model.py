import ast
import base64
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# Only optional device/image-rendering and unrelated provider dependencies are
# stubbed. Use the real config loader, image encoder and requests serializer.
with patch.dict(sys.modules, {
    name: types.ModuleType(name) for name in ("dashscope", "cv2", "pyshine")
}):
    import model
    from config import load_config


class MiniMaxModelTest(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.response = {
            "choices": [{"message": {"content": "Action: FINISH"}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 20},
        }
        self.status_code = 200
        transport = patch("requests.adapters.HTTPAdapter.send", self.send)
        transport.start()
        self.addCleanup(transport.stop)
        printer = patch.object(model, "print_with_color")
        self.printer = printer.start()
        self.addCleanup(printer.stop)

    def send(self, request, **kwargs):
        self.requests.append(request)
        response = requests.Response()
        response.status_code = self.status_code
        response._content = json.dumps(self.response).encode()
        response.headers["Content-Type"] = "application/json"
        response.request = request
        return response

    def make_model(self, name="MiniMax-M3.1-Flash", base="https://api.minimax.io/v1"):
        return model.MiniMaxModel(base, "test-key", name, 0.0, 16384)

    def select_model(self, script, configs):
        # Execute each entry point's actual selector without starting Android
        # interaction or prompting the test runner for a device/task.
        path = SCRIPTS_DIR / script
        tree = ast.parse(path.read_text())
        selector = next(node for node in tree.body if isinstance(node, ast.If))
        namespace = {
            "configs": configs,
            "OpenAIModel": model.OpenAIModel,
            "QwenModel": model.QwenModel,
            "MiniMaxModel": model.MiniMaxModel,
            "print_with_color": Mock(),
            "sys": sys,
        }
        exec(compile(ast.Module(body=[selector], type_ignores=[]), str(path), "exec"), namespace)
        return namespace["mllm"]

    def test_default_config_reaches_http_from_all_entry_points(self):
        for script in ("task_executor.py", "self_explorer.py", "document_generation.py"):
            for base in ("https://api.minimax.io/v1/", "https://api.minimaxi.com/v1/chat/completions"):
                with self.subTest(script=script, base=base):
                    configs = load_config(ROOT / "config.yaml")
                    self.assertEqual(configs["MODEL"], "OpenAI")
                    self.assertEqual(configs["MINIMAX_API_MODEL"], "MiniMax-M3.1-Flash")
                    configs.update(MODEL="MiniMax", MINIMAX_API_KEY="test-key", MINIMAX_API_BASE=base)
                    selected = self.select_model(script, configs)
                    self.assertEqual(selected.get_model_response("prompt", []), (True, "Action: FINISH"))
                    request = self.requests[-1]
                    self.assertEqual(request.method, "POST")
                    self.assertEqual(request.url, base.rstrip("/") if base.endswith("/chat/completions") else base.rstrip("/") + "/chat/completions")
                    self.assertEqual(request.headers["Authorization"], "Bearer test-key")
                    self.assertEqual(request.headers["Content-Type"], "application/json")
                    payload = json.loads(request.body)
                    self.assertEqual(payload["model"], "MiniMax-M3.1-Flash")
                    self.assertEqual(payload["thinking"], {"type": "adaptive"})
                    self.assertEqual(payload["max_tokens"], 16384)
                    self.assertEqual(payload["messages"], [{"role": "user", "content": [{"type": "text", "text": "prompt"}]}])
                    for key in ("reasoning_effort", "reasoning_split", "service_tier"):
                        self.assertNotIn(key, payload)

    def test_saved_and_custom_models_and_old_budget_are_preserved(self):
        for script in ("task_executor.py", "self_explorer.py", "document_generation.py"):
            for name, thinking in (("MiniMax-M3", "disabled"), ("MiniMax-M2.7", "enabled"), ("custom-model", None)):
                with self.subTest(script=script, model=name):
                    configs = load_config(ROOT / "config.yaml")
                    configs.pop("MINIMAX_MAX_TOKENS")
                    configs.update(MODEL="MiniMax", MINIMAX_API_KEY="test-key", MINIMAX_API_MODEL=name, MAX_TOKENS=456)
                    selected = self.select_model(script, configs)
                    selected.get_model_response("saved prompt", [])
                    payload = json.loads(self.requests[-1].body)
                    self.assertEqual(payload["model"], name)
                    self.assertEqual(payload["max_tokens"], 456)
                    if thinking:
                        self.assertEqual(payload["thinking"], {"type": thinking})
                    else:
                        self.assertNotIn("thinking", payload)
                    self.assertNotIn("reasoning_effort", payload)

    def test_custom_endpoint_and_explicit_budget_are_preserved(self):
        configs = load_config(ROOT / "config.yaml")
        configs.update(MODEL="MiniMax", MINIMAX_API_KEY="test-key", MINIMAX_API_BASE="https://gateway.example/v1", MINIMAX_MAX_TOKENS=8192)
        self.select_model("task_executor.py", configs).get_model_response("prompt", [])
        self.assertEqual(self.requests[-1].url, "https://gateway.example/v1/chat/completions")
        self.assertEqual(json.loads(self.requests[-1].body)["max_tokens"], 8192)
        self.printer.assert_called_with("Request cost estimate is unavailable.", "yellow")

    def test_screenshot_bytes_reach_http_unchanged(self):
        image_bytes = b"\xff\xd8\xff\xe0test-screenshot\xff\xd9"
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            image = Path(directory) / "screen.jpg"
            image.write_bytes(image_bytes)
            for name in ("MiniMax-M3.1-Flash", "MiniMax-M3", "custom-model"):
                with self.subTest(model=name):
                    self.make_model(name).get_model_response("screen prompt", [str(image)])
                    content = json.loads(self.requests[-1].body)["messages"][0]["content"]
                    self.assertEqual(content, [
                        {"type": "text", "text": "screen prompt"},
                        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode()}},
                    ])

    def test_rejects_images_for_saved_text_only_model_before_transport(self):
        self.assertEqual(self.make_model("MiniMax-M2.7").get_model_response("prompt", ["screen.jpg"]), (False, "MiniMax-M2.7 accepts text input only."))
        self.assertEqual(self.requests, [])

    def test_non_minimax_selection_and_payload_are_preserved(self):
        for script in ("task_executor.py", "self_explorer.py", "document_generation.py"):
            configs = load_config(ROOT / "config.yaml")
            configs["OPENAI_API_KEY"] = "test-key"
            selected = self.select_model(script, configs)
            self.assertIsInstance(selected, model.OpenAIModel)
            selected.get_model_response("prompt", [])
            payload = json.loads(self.requests[-1].body)
            self.assertEqual(self.requests[-1].url, "https://api.openai.com/v1/chat/completions")
            self.assertEqual(payload["model"], "gpt-4-vision-preview")
            self.assertEqual(payload["max_tokens"], 300)
            self.assertNotIn("thinking", payload)
            configs["MODEL"] = "Qwen"
            self.assertIsInstance(self.select_model(script, configs), model.QwenModel)

    def test_api_error_reaches_caller(self):
        self.status_code = 400
        self.response = {"error": {"message": "invalid request"}}
        self.assertEqual(self.make_model().get_model_response("prompt", []), (False, "invalid request"))
        self.printer.assert_not_called()

    def test_flash_price_uses_cached_input_rate(self):
        self.response["usage"] = {
            "prompt_tokens": 1_000_000, "completion_tokens": 1_000_000,
            "prompt_tokens_details": {"cached_tokens": 200_000},
        }
        self.make_model().get_model_response("prompt", [])
        self.printer.assert_called_with("Estimated request cost is $0.723000", "yellow")

    def test_flash_price_without_cache(self):
        self.assertAlmostEqual(self.make_model()._calculate_cost({"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000}), 0.75)

    def test_unknown_cache_write_rate_does_not_invent_cost(self):
        self.response["usage"]["cache_creation_input_tokens"] = 10
        self.make_model().get_model_response("prompt", [])
        self.printer.assert_called_with("Request cost estimate is unavailable.", "yellow")

    def test_m3_tier_and_custom_model_cost_are_not_invented(self):
        for name in ("MiniMax-M3", "custom-model"):
            self.make_model(name).get_model_response("prompt", [])
            self.printer.assert_called_with("Request cost estimate is unavailable.", "yellow")

    def test_regional_cost_is_not_assumed_to_be_global_usd(self):
        self.make_model(base="https://api.minimaxi.com/v1").get_model_response("prompt", [])
        self.printer.assert_called_with("Request cost estimate is unavailable.", "yellow")

    def test_saved_legacy_pricing_is_preserved(self):
        usage = {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000}
        self.assertEqual(self.make_model("MiniMax-M2.7")._calculate_cost(usage), 1.5)


if __name__ == "__main__":
    unittest.main()
