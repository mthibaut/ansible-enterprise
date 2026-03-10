#!/usr/bin/env bash
set -euo pipefail
[ -f requirements.yml ] || { echo "requirements.yml missing"; exit 1; }
ansible-galaxy collection install -r requirements.yml
ansible-pull -i inventory/pull.ini site.yml
