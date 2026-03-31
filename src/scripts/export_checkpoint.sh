#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# GENERATED FILE - DO NOT EDIT
# This file is overwritten by generate_ansible_enterprise.py.
# Source of truth: PROMPT.md.
# Manual edits will be lost on the next regeneration.
# -----------------------------------------------------------------------------
# Creates a ZIP archive from a git tag using 'git archive'.
# Usage: scripts/export_checkpoint.sh <checkpoint-tag>
set -euo pipefail
TAG="${1:-}"
if [ -z "$TAG" ]; then
  echo "Usage: scripts/export_checkpoint.sh <checkpoint-tag>"
  exit 1
fi
ZIP="ansible-enterprise-${TAG}.zip"
git archive --format=zip --prefix="ansible-enterprise-${TAG}/" "$TAG" -o "$ZIP"
echo "Created $ZIP"
