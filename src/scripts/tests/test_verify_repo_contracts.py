import pathlib
import sys
import tempfile
import unittest
import yaml

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src" / "scripts" / "internal"))
import verify_repo_contracts as vrc


class TestLocalConfigScrubContract(unittest.TestCase):

    def test_detects_private_identifiers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            sample = root / "README.md"
            sample.write_text("node: hypervisor-alpha\nip: 198.51.100.44\ndomain: operator.internal\n", encoding="utf-8")
            patterns = root / "patterns.yml"
            patterns.write_text(
                yaml.safe_dump(
                    {
                        "patterns": {
                            r"\bhypervisor-alpha\b": "example local node name",
                            r"\b198\.51\.100\.44\b": "example local IP",
                            r"\boperator\.internal\b": "example local domain",
                        }
                    }
                ),
                encoding="utf-8",
            )

            original_roots = vrc.LOCAL_CONFIG_SCAN_ROOTS
            original_default = vrc.DEFAULT_LOCAL_CONFIG_PATTERNS_FILE
            try:
                vrc.LOCAL_CONFIG_SCAN_ROOTS = [sample]
                vrc.DEFAULT_LOCAL_CONFIG_PATTERNS_FILE = patterns
                violations = vrc.find_local_config_violations()
            finally:
                vrc.LOCAL_CONFIG_SCAN_ROOTS = original_roots
                vrc.DEFAULT_LOCAL_CONFIG_PATTERNS_FILE = original_default

            joined = "\n".join(violations)
            self.assertIn("example local node name", joined)
            self.assertIn("198.51.100.44", sample.read_text(encoding="utf-8"))
            self.assertIn("operator.internal", sample.read_text(encoding="utf-8"))
            self.assertTrue(violations)

    def test_allows_generic_examples(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            sample = root / "README.md"
            patterns = root / "patterns.yml"
            patterns.write_text(
                yaml.safe_dump(
                    {
                        "patterns": {
                            r"\bhypervisor-alpha\b": "example local node name",
                            r"\b198\.51\.100\.44\b": "example local IP",
                            r"\boperator\.internal\b": "example local domain",
                        }
                    }
                ),
                encoding="utf-8",
            )
            sample.write_text(
                "node: pve01\nip: 192.0.2.9\ndomain: example.internal\nrepo: git@github.com:your-org/ansible-enterprise.git\n",
                encoding="utf-8",
            )

            original_roots = vrc.LOCAL_CONFIG_SCAN_ROOTS
            original_default = vrc.DEFAULT_LOCAL_CONFIG_PATTERNS_FILE
            try:
                vrc.LOCAL_CONFIG_SCAN_ROOTS = [sample]
                vrc.DEFAULT_LOCAL_CONFIG_PATTERNS_FILE = patterns
                violations = vrc.find_local_config_violations()
            finally:
                vrc.LOCAL_CONFIG_SCAN_ROOTS = original_roots
                vrc.DEFAULT_LOCAL_CONFIG_PATTERNS_FILE = original_default

            self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
