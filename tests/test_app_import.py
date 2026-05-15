import importlib
import unittest


class AppImportTest(unittest.TestCase):
    def test_app_import_does_not_require_tkinter(self):
        module = importlib.import_module("agent_voice.app")

        self.assertTrue(callable(module.main))


if __name__ == "__main__":
    unittest.main()
