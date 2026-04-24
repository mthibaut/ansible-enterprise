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


class TestRequiredFileContracts(unittest.TestCase):

    def test_repo_root_does_not_require_generated_ansible_cfg(self):
        self.assertNotIn("ansible.cfg", vrc.REQUIRED_ROOT_FILES)

    def test_verify_required_files_accepts_missing_repo_root_ansible_cfg(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            src = root / "src"
            build = root / "build"
            for path in (
                src / "PROMPT.md",
                src / ".prompt.sha256",
                src / ".prompt.version",
                src / ".generator.lock.yml",
                src / "generate_ansible_enterprise.py",
                src / "spec" / "contracts.md",
                src / "spec" / "ai-development-mode.md",
                src / "scripts" / "generation_contracts.yml",
                src / "scripts" / "known_gaps.yml",
                src / "scripts" / "internal" / "verify_repo_contracts.py",
                src / "scripts" / "internal" / "verify_checkpoints.py",
                src / "schemas" / "services.schema.json",
                root / "README.md",
                root / "CODEOWNERS",
                root / ".gitignore",
                root / "Makefile",
                build / "ansible.cfg",
            ):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("x\n", encoding="utf-8")

            module = type("Module", (), {"FILE_MANIFEST": {"ansible.cfg": ""}})()

            original_repo = vrc.REPO
            original_src = vrc.SRC
            original_build = vrc.BUILD
            try:
                vrc.REPO = root
                vrc.SRC = src
                vrc.BUILD = build
                vrc.verify_required_files(module)
            finally:
                vrc.REPO = original_repo
                vrc.SRC = original_src
                vrc.BUILD = original_build


if __name__ == "__main__":
    unittest.main()
