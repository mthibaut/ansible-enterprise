#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# GENERATED FILE - DO NOT EDIT
# This file is overwritten by generate_ansible_enterprise.py.
# Source of truth: PROMPT.md.
# Manual edits will be lost on the next regeneration.
# -----------------------------------------------------------------------------
# Validates spec/checkpoints.md ordering and naming.
from __future__ import annotations
import pathlib
import re
import sys

# SRC = src/ directory (grandparent of internal/)
SRC = pathlib.Path(__file__).resolve().parents[2]
CHECKPOINTS_FILE = SRC / "spec" / "checkpoints.md"
PATTERN = re.compile(r"`(checkpoint-(\d{3})-[a-z0-9][a-z0-9-]*)`")

def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)

def main() -> None:
    if not CHECKPOINTS_FILE.exists():
        fail(f"missing file: {CHECKPOINTS_FILE}")
    text = CHECKPOINTS_FILE.read_text(encoding="utf-8")
    matches = PATTERN.findall(text)
    if not matches:
        fail("no checkpoints found in spec/checkpoints.md")
    ordered = []
    seen_names, seen_numbers = set(), set()
    for full_name, number_text in matches:
        number = int(number_text)
        if full_name in seen_names:
            fail(f"duplicate checkpoint name: {full_name}")
        if number in seen_numbers:
            fail(f"duplicate checkpoint number: {number_text}")
        seen_names.add(full_name)
        seen_numbers.add(number)
        ordered.append((number, full_name))
    numbers = [n for n, _ in ordered]
    if numbers != sorted(numbers):
        fail("checkpoints are not listed in ascending order")
    expected = list(range(numbers[0], numbers[0] + len(numbers)))
    if numbers != expected:
        fail(f"checkpoint numbering not contiguous: found {numbers}, expected {expected}")
    print("Checkpoint validation passed.")
    for number, full_name in ordered:
        print(f"  {number:03d}  {full_name}")

if __name__ == "__main__":
    main()
