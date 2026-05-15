import unittest

from agent_voice.logging.privacy_filter import mask_sensitive_text


class PrivacyFilterTest(unittest.TestCase):
    def test_masks_patient_id_and_name_in_text(self):
        masked = mask_sensitive_text("正在调取患者123456，查看患者张三")

        self.assertNotIn("123456", masked)
        self.assertNotIn("张三", masked)
        self.assertIn("患者******", masked)
        self.assertIn("患者**", masked)

    def test_masks_secret_values(self):
        masked = mask_sensitive_text("X-Voice-Signature=abcdef123456 token=secret-value")

        self.assertNotIn("abcdef123456", masked)
        self.assertNotIn("secret-value", masked)
        self.assertIn("X-Voice-Signature=***", masked)
        self.assertIn("token=***", masked)


if __name__ == "__main__":
    unittest.main()
