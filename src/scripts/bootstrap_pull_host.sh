#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# GENERATED FILE - DO NOT EDIT
# This file is overwritten by generate_ansible_enterprise.py.
# Source of truth: PROMPT.md.
# Manual edits will be lost on the next regeneration.
# -----------------------------------------------------------------------------
set -euo pipefail
[ -f requirements.yml ] || { echo "requirements.yml missing - run from repo root"; exit 1; }
ansible-galaxy collection install -r requirements.yml
ansible-pull -i inventory/pull.ini site.yml
