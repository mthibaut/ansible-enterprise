#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# GENERATED FILE - DO NOT EDIT
# This file is overwritten by generate_ansible_enterprise.py.
# Source of truth: PROMPT.md.
# Manual edits will be lost on the next regeneration.
# -----------------------------------------------------------------------------
set -euo pipefail

echo "Running repository contract verification..."
python3 scripts/internal/verify_repo_contracts.py
python3 scripts/internal/validate_services_schema.py
python3 scripts/internal/verify_checkpoints.py
echo "Contracts verified."
