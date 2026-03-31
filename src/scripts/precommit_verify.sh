#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# GENERATED FILE - DO NOT EDIT
# This file is overwritten by generate_ansible_enterprise.py.
# Source of truth: PROMPT.md.
# Manual edits will be lost on the next regeneration.
# -----------------------------------------------------------------------------
set -euo pipefail

echo "Running repository contract verification..."
python3 scripts/verify_repo_contracts.py
python3 scripts/validate_services_schema.py
python3 scripts/verify_checkpoints.py
echo "Contracts verified."
