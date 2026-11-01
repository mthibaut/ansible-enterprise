"""
Tests for the repo-root CLAUDE.md (checkpoint-246).

CLAUDE.md is the entry point that makes every Claude session load the
repository contracts before changing anything. These tests keep it pointing
at files that exist and keep the key rules present.
"""
import pathlib
import re
import unittest

REPO = pathlib.Path(__file__).resolve().parents[3]
CLAUDE_MD = REPO / "CLAUDE.md"

CONTRACT_FILES = [
    "src/spec/contracts.md",
    "src/spec/ai-development-mode.md",
    "src/PROMPT.md",
    "src/spec/architecture.md",
    "src/spec/generator.md",
    "src/spec/roles.md",
    "src/spec/services.md",
    "src/spec/checkpoints.md",
    "src/scripts/generation_contracts.yml",
]


class TestClaudeMd(unittest.TestCase):
    def setUp(self):
        self.assertTrue(CLAUDE_MD.exists(), "CLAUDE.md missing at repo root")
        self.text = CLAUDE_MD.read_text(encoding="utf-8")

    def test_ascii_only(self):
        self.text.encode("ascii")

    def test_lists_every_contract_file_and_they_exist(self):
        for rel in CONTRACT_FILES:
            self.assertIn(f"`{rel}`", self.text, f"CLAUDE.md does not reference {rel}")
            self.assertTrue((REPO / rel).exists(), f"{rel} referenced but missing")

    def test_every_backticked_src_path_exists(self):
        for rel in re.findall(r"`(src/[^`*]+)`", self.text):
            if rel.endswith("/"):
                rel = rel.rstrip("/")
            self.assertTrue((REPO / rel).exists(), f"CLAUDE.md points at missing {rel}")

    def test_key_rules_present(self):
        for phrase in [
            "Every change needs a test",
            "Never put real local identifiers",
            "ASCII-only",
            "must never be edited by hand",
            "src/.generator.lock.yml",
        ]:
            self.assertIn(phrase, self.text)

    def test_validation_commands_present(self):
        for cmd in ("make all", "make test", "make checkpoints", "make services"):
            self.assertIn(cmd, self.text)

    def test_make_targets_exist(self):
        makefile = (REPO / "Makefile").read_text(encoding="utf-8")
        for target in ("all", "test", "checkpoints", "services"):
            self.assertRegex(makefile, rf"(?m)^{target}:", f"Makefile lacks target {target}")


if __name__ == "__main__":
    unittest.main()
