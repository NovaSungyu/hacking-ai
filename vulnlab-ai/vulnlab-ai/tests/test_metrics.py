import unittest

from evaluator.metrics import compute_metrics


class MetricsTest(unittest.TestCase):
    def test_binary_counts(self):
        y_true = ["xss_reflected", "xss_reflected", "none", "none", "sql_error_leak"]
        y_pred = ["xss_reflected", "none", "xss_reflected", "none", "sql_error_leak"]
        b = compute_metrics(y_true, y_pred)["binary"]
        self.assertEqual((b["tp"], b["fp"], b["fn"], b["tn"]), (2, 1, 1, 1))
        self.assertAlmostEqual(b["accuracy"], 3 / 5)
        self.assertAlmostEqual(b["precision"], 2 / 3)
        self.assertAlmostEqual(b["recall"], 2 / 3)

    def test_multiclass_wrong_type_counts_as_error(self):
        m = compute_metrics(["xss_reflected"], ["sql_error_leak"])
        self.assertEqual(m["binary"]["tp"], 1)          # 취약 탐지 자체는 맞음
        self.assertEqual(m["multiclass"]["accuracy"], 0)  # 유형은 틀림


if __name__ == "__main__":
    unittest.main()
