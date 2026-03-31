#!/usr/bin/env bash
# contrib/pull_website.sh
#
# Copy a provisioned website from a remote host to the local machine and
# apply the exact ownership and permissions that the Ansible users role sets.
#
# Usage:
#   pull_website.sh --site <service-name> --remote <user@host>
#   pull_website.sh -s <service-name> -r <user@host>
#
# Arguments:
#   --site, -s    Service name as declared in the Ansible services dict
#                 (the key under `services:` in group_vars/all/main.yml).
#   --remote, -r  Remote to copy from, in the form user@host or host.
#                 The script appends :/var/www/<domain>/ automatically.
#
# What it does:
#   1. Reads build/group_vars/all/main.yml to resolve the service domain
#      and owner (matching what `roles/users` provisions on the server).
#   2. rsyncs /var/www/<domain>/ from the remote to the local machine.
#   3. Sets ownership (<owner>:<owner>) and permissions (dirs 0755,
#      files 0644) to match the provisioned state.
#
# Requirements:
#   - python3 with PyYAML (pip install PyYAML)
#   - rsync
#   - sudo (for chown; the local web root is owned by the service account)
#
# Run this script from the repository root so the relative path to
# build/group_vars/all/main.yml resolves correctly, or set REPO_ROOT.
#
# Example:
#   cd /path/to/ansible-enterprise
#   contrib/pull_website.sh --site myapp --remote deploy@192.0.2.10

set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

usage() {
    sed -n '/^# Usage:/,/^[^#]/p' "$0" | sed 's/^# \{0,3\}//' | head -n -1
    exit 1
}

die() { echo "error: $*" >&2; exit 1; }
info() { echo "==> $*"; }

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || die "'$1' is required but not found in PATH"
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

SITE=""
REMOTE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --site|-s)
            [[ $# -ge 2 ]] || die "--site requires an argument"
            SITE="$2"; shift 2 ;;
        --remote|-r)
            [[ $# -ge 2 ]] || die "--remote requires an argument"
            REMOTE="$2"; shift 2 ;;
        --help|-h)
            usage ;;
        *)
            die "unknown argument: $1 (try --help)" ;;
    esac
done

[[ -n "$SITE"   ]] || die "--site is required"
[[ -n "$REMOTE" ]] || die "--remote is required"

# ---------------------------------------------------------------------------
# Locate repository root and group_vars
# ---------------------------------------------------------------------------

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
VARS_FILE="$REPO_ROOT/build/group_vars/all/main.yml"

[[ -f "$VARS_FILE" ]] || die "group_vars not found at $VARS_FILE
Run 'make generate' first, or set REPO_ROOT to the repository root."

# ---------------------------------------------------------------------------
# Resolve domain and owner from the services dict
# ---------------------------------------------------------------------------

read -r DOMAIN OWNER < <(python3 - "$VARS_FILE" "$SITE" <<'PYEOF'
import sys, pathlib
try:
    import yaml
except ImportError:
    print("error: PyYAML is required (pip install PyYAML)", file=sys.stderr)
    sys.exit(1)

vars_file, site = pathlib.Path(sys.argv[1]), sys.argv[2]
data = yaml.safe_load(vars_file.read_text())
services = data.get("services", {})

if site not in services:
    known = ", ".join(sorted(services)) or "(none)"
    print(f"error: service '{site}' not found in services dict\nKnown services: {known}",
          file=sys.stderr)
    sys.exit(1)

svc = services[site]

if not svc.get("enabled", False):
    print(f"error: service '{site}' exists but is not enabled", file=sys.stderr)
    sys.exit(1)

domain = svc.get("domain", "")
owner  = svc.get("owner", "")

if not domain:
    print(f"error: service '{site}' has no domain", file=sys.stderr)
    sys.exit(1)
if not owner:
    print(f"error: service '{site}' has no owner", file=sys.stderr)
    sys.exit(1)

print(domain, owner)
PYEOF
)

[[ -n "$DOMAIN" ]] || die "could not resolve domain for site '$SITE'"
[[ -n "$OWNER"  ]] || die "could not resolve owner for site '$SITE'"

# ---------------------------------------------------------------------------
# Confirm and execute
# ---------------------------------------------------------------------------

LOCAL_WEB_ROOT="/var/www/$DOMAIN"
REMOTE_PATH="$REMOTE:/var/www/$DOMAIN/"

info "Site:        $SITE"
info "Domain:      $DOMAIN"
info "Owner:       $OWNER"
info "Remote:      $REMOTE_PATH"
info "Local:       $LOCAL_WEB_ROOT"
echo

require_cmd rsync
require_cmd python3

# Ensure the local web root exists with correct ownership before syncing.
# Mirrors what roles/users tasks/main.yml creates:
#   path: /var/www/{{ service.domain }}
#   owner: {{ service.owner }}  group: {{ service.owner }}  mode: 0755
if [[ ! -d "$LOCAL_WEB_ROOT" ]]; then
    info "Creating $LOCAL_WEB_ROOT"
    sudo install -d -m 0755 -o "$OWNER" -g "$OWNER" "$LOCAL_WEB_ROOT"
fi

info "Syncing files from $REMOTE_PATH ..."
# --archive      : preserve permissions, timestamps, symlinks, owner, group
# --delete       : remove local files that no longer exist on the remote
# --human-readable --progress : visible transfer progress
# Trailing slash on source: copy contents, not the directory itself.
rsync \
    --archive \
    --delete \
    --human-readable \
    --progress \
    "$REMOTE_PATH" \
    "$LOCAL_WEB_ROOT/"

# Apply ownership and permissions matching the Ansible users role:
#   directory mode 0755, file mode 0644, owner:group = owner:owner
info "Applying ownership ($OWNER:$OWNER) and permissions ..."
sudo chown -R "$OWNER:$OWNER" "$LOCAL_WEB_ROOT"
sudo find "$LOCAL_WEB_ROOT" -type d -exec chmod 0755 {} +
sudo find "$LOCAL_WEB_ROOT" -type f -exec chmod 0644 {} +

info "Done. $LOCAL_WEB_ROOT is up to date."
