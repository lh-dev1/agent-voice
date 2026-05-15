import unittest

from agent_voice.ui.qt_widget import _compact_status_text
from agent_voice.ui.settings_dialog import _audio_device_options
from agent_voice.ui.styles import floating_widget_style_sheet


class QtWidgetSettingsTest(unittest.TestCase):
    def test_audio_device_options_start_with_system_default(self):
        devices = [{"index": 3, "name": "MacBook Air麦克风", "max_input_channels": 1}]

        options = _audio_device_options(devices)

        self.assertEqual(options[0], ("系统默认麦克风", None))
        self.assertEqual(options[1], ("3: MacBook Air麦克风", 3))

    def test_audio_device_options_filters_output_only_devices(self):
        devices = [
            {"index": 1, "name": "扬声器", "max_input_channels": 0},
            {"index": 2, "name": "USB Mic", "max_input_channels": 2},
        ]

        options = _audio_device_options(devices)

        self.assertEqual(options, [("系统默认麦克风", None), ("2: USB Mic", 2)])

    def test_compact_status_text_shortens_microphone_level(self):
        text = _compact_status_text("麦克风：有声音，音量 23%\n最近识别：等待唤醒词")

        self.assertEqual(text, "有声音 23%")

    def test_compact_status_text_has_fallback(self):
        self.assertEqual(_compact_status_text(""), "等待语音")

    def test_compact_status_text_prefers_send_result(self):
        text = "最近识别：调取患者123456\n发送结果：已发送 / open_patient"

        self.assertEqual(_compact_status_text(text), "已发送")

    def test_context_menu_uses_rounded_border(self):
        style = floating_widget_style_sheet()

        self.assertIn("QMenu", style)
        self.assertIn("border-radius: 12px", style)
        self.assertIn("QMenu::item", style)

    def test_floating_style_does_not_leak_into_dialog_inputs(self):
        style = floating_widget_style_sheet()

        self.assertNotIn("QLineEdit", style)
        self.assertNotIn("QPushButton", style)


if __name__ == "__main__":
    unittest.main()
