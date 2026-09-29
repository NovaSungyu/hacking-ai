import unittest

from agent.safety import TargetNotAllowed, assert_allowed


class SafetyTest(unittest.TestCase):
    def test_allows_loopback(self):
        for u in ["http://127.0.0.1:8080/x", "http://localhost:8080/", "http://[::1]:8080/"]:
            assert_allowed(u)

    def test_blocks_external(self):
        for u in ["http://example.com/", "https://8.8.8.8/", "http://192.168.0.5/", "file:///etc/passwd",
                  "ftp://127.0.0.1/"]:
            with self.assertRaises(TargetNotAllowed):
                assert_allowed(u)

    def test_extra_host_must_be_listed(self):
        with self.assertRaises(TargetNotAllowed):
            assert_allowed("http://vuln-lab:8080/")

    def test_public_ip_never_allowed_even_if_listed(self):
        with self.assertRaises(TargetNotAllowed):
            assert_allowed("http://8.8.8.8/", extra_hosts=["8.8.8.8"])


if __name__ == "__main__":
    unittest.main()
