import unittest

from agent_voice.ui.qt_widget import _audio_device_options


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


if __name__ == "__main__":
    unittest.main()
