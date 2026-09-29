import unittest

from analyzer.llm_detector import LLMDetector
from analyzer.rules import RuleDetector
from analyzer.schema import HttpExchange
from models.mock import MockProvider

HDR_OK = {"Content-Type": "text/html", "Content-Security-Policy": "x",
          "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY"}


def ex(body, headers=None, inputs=None, status=200):
    return HttpExchange("GET", "http://127.0.0.1:8080/t", status, headers or HDR_OK, body, inputs or {})


class RuleTest(unittest.TestCase):
    def test_xss_reflected(self):
        self.assertEqual(RuleDetector().predict(ex("<p>a<x>b</p>", inputs={"q": "a<x>b"})).label, "xss_reflected")

    def test_xss_encoded_is_none(self):
        self.assertEqual(RuleDetector().predict(ex("<p>a&lt;x&gt;b</p>", inputs={"q": "a<x>b"})).label, "none")

    def test_sql_error(self):
        self.assertEqual(RuleDetector().predict(ex("Database error: no such column: abc", status=500)).label, "sql_error_leak")

    def test_traceback(self):
        self.assertEqual(RuleDetector().predict(ex("Traceback (most recent call last):\n  File \"/app/a.py\", line 3")).label, "info_disclosure")

    def test_missing_headers(self):
        self.assertEqual(RuleDetector().predict(ex("<p>x</p>", headers={"Content-Type": "text/html"})).label, "insecure_headers")


class LLMDetectorTest(unittest.TestCase):
    def test_fenced_json_is_parsed(self):
        raw = '```json\n{"label":"xss_reflected","confidence":0.8,"evidence":["e"],"reasoning":"r"}\n```'
        p = LLMDetector(MockProvider([raw])).predict(ex("x"))
        self.assertEqual(p.label, "xss_reflected")
        self.assertIsNone(p.error)

    def test_invalid_output_is_flagged(self):
        p = LLMDetector(MockProvider(["I think it is vulnerable"])).predict(ex("x"))
        self.assertIsNotNone(p.error)
        self.assertEqual(p.label, "none")

    def test_invalid_label_is_flagged(self):
        p = LLMDetector(MockProvider(['{"label":"rce"}'])).predict(ex("x"))
        self.assertIsNotNone(p.error)


if __name__ == "__main__":
    unittest.main()
