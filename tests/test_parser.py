import unittest

from agent_voice.nlu.parser import IntentParser


class IntentParserTest(unittest.TestCase):
    def setUp(self):
        self.parser = IntentParser()

    def test_fetches_patient_by_id_with_synonym(self):
        result = self.parser.parse("打开患者 123456", asr_confidence=0.91)

        self.assertTrue(result.matched)
        self.assertEqual(result.intent, "fetch_patient")
        self.assertEqual(result.params, {"patient_id": "123456"})
        self.assertGreaterEqual(result.parser_confidence, 0.95)
        self.assertEqual(result.normalized_text, "打开患者123456")

    def test_fetches_patient_by_spoken_digit_id_after_wake_word(self):
        result = self.parser.parse("小图小图，调取患者一二三四五六", asr_confidence=0.91)

        self.assertTrue(result.matched)
        self.assertEqual(result.intent, "fetch_patient")
        self.assertEqual(result.params, {"patient_id": "123456"})
        self.assertEqual(result.normalized_text, "调取患者123456")

    def test_fetches_patient_by_id_with_extra_words(self):
        result = self.parser.parse("帮我打开病人123456的病历", asr_confidence=0.91)

        self.assertTrue(result.matched)
        self.assertEqual(result.intent, "fetch_patient")
        self.assertEqual(result.params, {"patient_id": "123456"})

    def test_fetches_patient_by_chinese_name(self):
        result = self.parser.parse("查看患者张三", asr_confidence=0.88)

        self.assertTrue(result.matched)
        self.assertEqual(result.intent, "fetch_patient")
        self.assertEqual(result.params, {"patient_name": "张三"})

    def test_calls_next_patient(self):
        result = self.parser.parse("呼叫下一个患者", asr_confidence=0.93)

        self.assertTrue(result.matched)
        self.assertEqual(result.intent, "call_next_patient")
        self.assertEqual(result.params, {})

    def test_record_control_actions(self):
        cases = {
            "开始录音": "start",
            "暂停录音": "pause",
            "继续录音": "resume",
            "关闭录音": "stop",
        }

        for text, action in cases.items():
            with self.subTest(text=text):
                result = self.parser.parse(text, asr_confidence=0.9)
                self.assertTrue(result.matched)
                self.assertEqual(result.intent, "record_control")
                self.assertEqual(result.params, {"action": action})

    def test_low_asr_confidence_does_not_match(self):
        result = self.parser.parse("调取患者123456", asr_confidence=0.2)

        self.assertFalse(result.matched)
        self.assertIsNone(result.intent)
        self.assertEqual(result.reason, "low_asr_confidence")

    def test_unknown_command_does_not_match(self):
        result = self.parser.parse("今天天气怎么样", asr_confidence=0.9)

        self.assertFalse(result.matched)
        self.assertIsNone(result.intent)
        self.assertEqual(result.reason, "no_rule_matched")


if __name__ == "__main__":
    unittest.main()
