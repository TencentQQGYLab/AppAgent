import sys
import tempfile
import types
import unittest
from pathlib import Path


scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(scripts_dir))

utils_stub = types.ModuleType("utils")
utils_stub.print_with_color = lambda *_args, **_kwargs: None
sys.modules["utils"] = utils_stub

from and_controller import traverse_tree


class TraverseTreeTest(unittest.TestCase):
    def traverse(self, xml):
        with tempfile.TemporaryDirectory() as temp_dir:
            xml_path = Path(temp_dir) / "window.xml"
            xml_path.write_text(xml, encoding="utf-8")
            elements = []
            traverse_tree(xml_path, elements, "focusable", True)
        return elements

    def test_handles_root_without_bounds(self):
        elements = self.traverse(
            '<hierarchy rotation="0">'
            '<node index="0" class="android.widget.EditText" focusable="true" '
            'bounds="[10,20][110,60]" />'
            '</hierarchy>'
        )

        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].uid, "android.widget.EditText_100_40_0")
        self.assertEqual(elements[0].bbox, ((10, 20), (110, 60)))

    def test_skips_interactive_elements_without_valid_bounds(self):
        elements = self.traverse(
            '<hierarchy rotation="0">'
            '<node index="0" class="android.widget.EditText" focusable="true" />'
            '<node index="1" class="android.widget.Button" focusable="true" bounds="invalid" />'
            '<node index="2" class="android.widget.Button" focusable="true" '
            'bounds="[0,0][50,30]" />'
            '</hierarchy>'
        )

        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].uid, "android.widget.Button_50_30_2")


if __name__ == "__main__":
    unittest.main()
