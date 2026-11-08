import tempfile
import unittest
from pathlib import Path
from proofscope.audit import classified_failure, digest, GOOD

class AuditTests(unittest.TestCase):
    def test_detect_kernel_type_mismatch(self):
        r = {"exit_code": 1, "execution_error": None,
             "stdout": "while replaying declaration 'kc_forged': (kernel) declaration type mismatch",
             "stderr": ""}
        self.assertTrue(classified_failure(r))

    def test_dont_count_missing_module_as_rejection(self):
        r = {"exit_code": 1, "execution_error": None,
             "stdout": "Could not resolve module: KernelControl.Forged", "stderr": ""}
        self.assertFalse(classified_failure(r))

    def test_dont_count_unavailable_checker(self):
        r = {"exit_code": None, "execution_error": "FileNotFoundError",
             "stdout": "", "stderr": ""}
        self.assertFalse(classified_failure(r))

    def test_digest(self):
        self.assertEqual(len(digest(GOOD)), 64)

if __name__ == "__main__":
    unittest.main()
