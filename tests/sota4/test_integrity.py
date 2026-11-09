"""SOTA-4 Task B: properties of the canonical-JSON dataset manifest (bench/sota4/integrity.py)."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from bench.sota4 import integrity as I

REPO = Path(__file__).resolve().parents[2]
HELD = REPO / "research/cjcs/core_heldout.MANIFEST.json"


class Canonical(unittest.TestCase):
    def test_newline_representations_hash_identically(self):
        a = b'{"a": 1, "b": [1, 2]}'
        for v in (a + b"\n", a + b"\r\n", b'{"a":1,\r\n "b":[1,2]}\r\n', b'{ "b" : [1,2], "a" : 1 }'):
            self.assertEqual(I.file_digest(a), I.file_digest(v))

    def test_semantic_changes_change_digest(self):
        a = b'{"a": 1, "b": [1, 2], "s": "x"}'
        for v in (b'{"a": 2, "b": [1, 2], "s": "x"}', b'{"a": 1, "b": [2, 1], "s": "x"}',
                  b'{"a": "1", "b": [1, 2], "s": "x"}', b'{"a": 1, "b": [1, 2], "s": "x "}',
                  b'{"a": 1, "b": [1, 2]}', b'{"a": 1, "b": [1, 2], "s": "x", "t": null}'):
            self.assertNotEqual(I.file_digest(a), I.file_digest(v))

    def test_invalid_json_rejected(self):
        for v in (b'{"a": 1', b'{"a": 1, "a": 2}', b'{"a": NaN}', b'\xef\xbb\xbf{"a":1}', b'\xff\xfe'):
            with self.assertRaises(I.IntegrityError):
                I.file_digest(v)


class Manifest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "repo"
        shutil.copytree(REPO / "research/cjcs/core_heldout", self.root / "research/cjcs/core_heldout")
        self.mp = self.root / "research/cjcs/core_heldout.MANIFEST.json"
        shutil.copy(HELD, self.mp)
        self.d = self.root / "research/cjcs/core_heldout"

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _m(self):
        return json.loads(self.mp.read_text())

    def _w(self, m):
        self.mp.write_text(json.dumps(m))

    def test_repository_files_verify_and_reproduce_recorded_sota3_digest(self):
        r = I.verify(HELD, REPO, require_legacy=True)
        self.assertEqual(r["files"], 14)
        self.assertEqual(r["legacy_reconstructed"], "bb8628b61ff16efd674dc6380a94bc64f301f37ae273ae26f7768027b8a29495")

    def test_original_bytes_without_trailing_newline_verify(self):
        for f in self.d.glob("*.json"):
            b = f.read_bytes()
            f.write_bytes(b[:-1] if b.endswith(b"\n") else b)
        self.assertTrue(I.verify(self.mp, self.root, require_legacy=True)["legacy_match"])

    def test_crlf_checkout_verifies(self):
        for f in self.d.glob("*.json"):
            f.write_bytes(f.read_bytes().replace(b"\n", b"\r\n"))
        r = I.verify(self.mp, self.root)
        self.assertTrue(r["ok"])
        self.assertFalse(r["legacy_match"])            # byte-level legacy digest is LF-only, reported
        with self.assertRaisesRegex(I.IntegrityError, "legacy digest"):
            I.verify(self.mp, self.root, require_legacy=True)

    def test_changed_label_detected(self):
        f = self.d / "h01_int_abs_sq.json"
        d = json.loads(f.read_text())
        d["expected"] = "CERTIFIED_LOGICAL_DIFFERENCE"
        f.write_text(json.dumps(d, ensure_ascii=False))
        with self.assertRaisesRegex(I.IntegrityError, "canonical digest mismatch"):
            I.verify(self.mp, self.root)

    def test_missing_file_detected(self):
        (self.d / "h07_vacuous_ref.json").unlink()
        with self.assertRaisesRegex(I.IntegrityError, "missing"):
            I.verify(self.mp, self.root)

    def test_extra_file_rejected(self):
        (self.d / "h99_injected.json").write_text('{"id": "h99"}')
        with self.assertRaisesRegex(I.IntegrityError, "unexpected additional"):
            I.verify(self.mp, self.root)

    def test_duplicated_entry_rejected(self):
        m = self._m()
        m["files"].insert(1, m["files"][0])
        m["set_digest"] = I.set_digest(m["files"])
        self._w(m)
        with self.assertRaisesRegex(I.IntegrityError, "duplicated"):
            I.verify(self.mp, self.root)

    def test_order_is_committed(self):
        m = self._m()
        m["files"][0], m["files"][1] = m["files"][1], m["files"][0]
        m["set_digest"] = I.set_digest(m["files"])
        self._w(m)
        with self.assertRaisesRegex(I.IntegrityError, "order"):
            I.verify(self.mp, self.root)

    def test_names_are_committed(self):
        m = self._m()
        m["files"][0]["name"] = "h00_renamed.json"
        self._w(m)                                   # set digest no longer matches
        with self.assertRaisesRegex(I.IntegrityError, "set digest"):
            I.verify(self.mp, self.root)

    def test_renamed_file_detected(self):
        (self.d / "h01_int_abs_sq.json").rename(self.d / "h01_renamed.json")
        with self.assertRaises(I.IntegrityError):
            I.verify(self.mp, self.root)

    def test_invalid_json_file_rejected(self):
        (self.d / "h02_nat_div_mul.json").write_text('{"id": "h02",')
        with self.assertRaisesRegex(I.IntegrityError, "invalid JSON"):
            I.verify(self.mp, self.root)

    def test_manifest_not_recomputable_from_tampered_checkout(self):
        """Recomputing a manifest from a tampered checkout cannot reproduce the recorded SOTA-3 digest."""
        f = self.d / "h03_bool_and_comm.json"
        f.write_text(f.read_text().replace("CERTIFIED", "XCERTIFIED", 1))
        m = I.build_manifest(self.d, "*.json", "research/cjcs/core_heldout")
        m["legacy"] = self._m()["legacy"]
        self._w(m)
        with self.assertRaisesRegex(I.IntegrityError, "legacy digest"):
            I.verify(self.mp, self.root, require_legacy=True)


if __name__ == "__main__":
    unittest.main()
