import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

dashscope = types.ModuleType("dashscope")
dashscope.MultiModalConversation = Mock()
sys.modules.setdefault("dashscope", dashscope)

requests = types.ModuleType("requests")
requests.post = Mock()
sys.modules.setdefault("requests", requests)

utils = types.ModuleType("utils")
utils.encode_image = Mock(return_value="encoded-image")
utils.print_with_color = Mock()
sys.modules.setdefault("utils", utils)

from model import MiniMaxModel


class MiniMaxModelTest(unittest.TestCase):
    def test_normalizes_regional_base_url(self):
        model = MiniMaxModel(
            "https://api.minimax.io/v1/",
            "key",
            "MiniMax-M3",
            0.0,
            100
        )

        self.assertEqual(
            model.base_url,
            "https://api.minimax.io/v1/chat/completions"
        )

    def test_rejects_images_for_text_only_model(self):
        model = MiniMaxModel(
            "https://api.minimaxi.com/v1",
            "key",
            "MiniMax-M2.7",
            0.0,
            100
        )

        with patch("model.requests.post") as post:
            success, message = model.get_model_response("prompt", ["screen.jpg"])

        self.assertFalse(success)
        self.assertEqual(message, "MiniMax-M2.7 accepts text input only.")
        post.assert_not_called()

    def test_uses_model_specific_pricing(self):
        usage = {
            "prompt_tokens": 1_000_000,
            "completion_tokens": 1_000_000
        }
        m3 = MiniMaxModel(
            "https://api.minimax.io/v1",
            "key",
            "MiniMax-M3",
            0.0,
            100
        )
        m27 = MiniMaxModel(
            "https://api.minimax.io/v1",
            "key",
            "MiniMax-M2.7",
            0.0,
            100
        )

        self.assertEqual(m3._calculate_cost(usage), 3.0)
        self.assertEqual(m27._calculate_cost(usage), 1.5)


if __name__ == "__main__":
    unittest.main()
