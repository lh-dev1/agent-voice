import unittest

from agent_voice.ui.qt_widget import _audio_device_options, _compact_status_text


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


if __name__ == "__main__":
    unittest.main()
