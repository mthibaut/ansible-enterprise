#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# GENERATED FILE - DO NOT EDIT
# This file is overwritten by generate_ansible_enterprise.py.
# Source of truth: PROMPT.md.
# Manual edits will be lost on the next regeneration.
# -----------------------------------------------------------------------------
from __future__ import annotations
import json
from pathlib import Path
import yaml
from jsonschema import validate

SRC = Path(__file__).resolve().parents[1]
BUILD = SRC.parent / "build"
schema = json.loads((SRC / "schemas/services.schema.json").read_text(encoding="utf-8"))
data = yaml.safe_load((BUILD / "group_vars/all/main.yml").read_text(encoding="utf-8")) or {}
validate(instance=data.get("services", {}), schema=schema)
print("services schema validation passed")
