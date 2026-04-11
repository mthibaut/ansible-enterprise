import pathlib
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src" / "scripts"))
import verify_repo_contracts as vrc


class TestLocalConfigScrubContract(unittest.TestCase):

    def test_detects_private_identifiers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            sample = root / "README.md"
            sample.write_text("node: pve-nuc-1\nip: 192.168.20.9\ndomain: home.lan\n", encoding="utf-8")

            original_roots = vrc.LOCAL_CONFIG_SCAN_ROOTS
            try:
                vrc.LOCAL_CONFIG_SCAN_ROOTS = [sample]
                violations = vrc.find_local_config_violations()
            finally:
                vrc.LOCAL_CONFIG_SCAN_ROOTS = original_roots

            joined = "\n".join(violations)
            self.assertIn("pve-nuc", joined)
            self.assertIn("192.168.20.9", sample.read_text(encoding="utf-8"))
            self.assertIn("home.lan", sample.read_text(encoding="utf-8"))
            self.assertTrue(violations)

    def test_allows_generic_examples(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            sample = root / "README.md"
            sample.write_text(
                "node: pve01\nip: 192.0.2.9\ndomain: example.internal\nrepo: git@github.com:your-org/ansible-enterprise.git\n",
                encoding="utf-8",
            )

            original_roots = vrc.LOCAL_CONFIG_SCAN_ROOTS
            try:
                vrc.LOCAL_CONFIG_SCAN_ROOTS = [sample]
                violations = vrc.find_local_config_violations()
            finally:
                vrc.LOCAL_CONFIG_SCAN_ROOTS = original_roots

            self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
