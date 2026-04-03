#!/usr/bin/env bash
# contrib/pull_website.sh
#
# Copy a provisioned website from a remote host to the local machine and
# apply the exact ownership and permissions that the Ansible users role sets.
#
# Usage:
#   pull_website.sh --domain <domain> --owner <user> --remote <user@host>
#   pull_website.sh -d <domain> -o <user> -r <user@host> [-p <port>]
#
# Arguments:
#   --domain, -d  The domain of the site (e.g. myapp.example.com).
#                 Used to derive the web root: /var/www/<domain>/
#   --owner, -o   The Unix user that owns the web root on the server.
#   --remote, -r  Remote to copy from. Accepts user@host (the script
#                 appends :/var/www/<domain>/) or user@host:/path to
#                 override the remote directory.
#   --port, -p    SSH port on the remote host (default: 22).
#
# What it does:
#   1. rsyncs /var/www/<domain>/ from the remote to the local machine.
#   2. Sets ownership (<owner>:<owner>) and permissions (dirs 0755,
#      files 0644) to match the provisioned state.
#
# Requirements:
#   - rsync
#   - sudo (for chown; the local web root is owned by the service account)
#
# Example:
#   pull_website.sh --domain myapp.example.com --owner myapp --remote deploy@192.0.2.10

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
step() { STEP_N=$(( ${STEP_N:-0} + 1 )); echo "[${STEP_N}/${STEP_TOTAL}] $*"; }
STEP_TOTAL=4

require_cmd() {
    command -v "$1" >/dev/null 2>&1 || die "'$1' is required but not found in PATH"
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

DOMAIN=""
OWNER=""
REMOTE=""
PORT="22"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --domain|-d)
            [[ $# -ge 2 ]] || die "--domain requires an argument"
            DOMAIN="$2"; shift 2 ;;
        --owner|-o)
            [[ $# -ge 2 ]] || die "--owner requires an argument"
            OWNER="$2"; shift 2 ;;
        --remote|-r)
            [[ $# -ge 2 ]] || die "--remote requires an argument"
            REMOTE="$2"; shift 2 ;;
        --port|-p)
            [[ $# -ge 2 ]] || die "--port requires an argument"
            PORT="$2"; shift 2 ;;
        --help|-h)
            usage ;;
        *)
            die "unknown argument: $1 (try --help)" ;;
    esac
done

[[ -n "$DOMAIN" ]] || die "--domain is required"
[[ -n "$OWNER"  ]] || die "--owner is required"
[[ -n "$REMOTE" ]] || die "--remote is required"

# ---------------------------------------------------------------------------
# Confirm and execute
# ---------------------------------------------------------------------------

LOCAL_WEB_ROOT="/var/www/$DOMAIN"
if [[ "$REMOTE" == *:* ]]; then
    # Ensure trailing slash so rsync copies contents, not the directory itself.
    REMOTE_PATH="${REMOTE%/}/"
else
    REMOTE_PATH="$REMOTE:/var/www/$DOMAIN/"
fi

info "Domain:      $DOMAIN"
info "Owner:       $OWNER"
info "Remote:      $REMOTE_PATH"
info "Local:       $LOCAL_WEB_ROOT"
echo

require_cmd rsync

step "Checking prerequisites"

# Ensure the local web root exists with correct ownership before syncing.
# Mirrors what roles/users tasks/main.yml creates:
#   path: /var/www/{{ service.domain }}
#   owner: {{ service.owner }}  group: {{ service.owner }}  mode: 0755
if [[ ! -d "$LOCAL_WEB_ROOT" ]]; then
    step "Creating $LOCAL_WEB_ROOT"
    sudo install -d -m 0755 -o "$OWNER" -g "$OWNER" "$LOCAL_WEB_ROOT"
else
    step "Local web root exists"
fi

step "Syncing files from $REMOTE_PATH"
# --archive      : preserve permissions, timestamps, symlinks, owner, group
# --delete       : remove local files that no longer exist on the remote
# --out-format   : one line per file, piped through awk for a running counter
# Trailing slash on source: copy contents, not the directory itself.
rsync \
    --archive \
    --delete \
    --info=progress2 \
    --human-readable \
    -e "ssh -p $PORT" \
    "$REMOTE_PATH" \
    "$LOCAL_WEB_ROOT/"

# Apply ownership and permissions matching the Ansible users role:
#   directory mode 0755, file mode 0644, owner:group = owner:owner
step "Applying ownership ($OWNER:$OWNER) and permissions"
sudo chown -R "$OWNER:$OWNER" "$LOCAL_WEB_ROOT"
sudo find "$LOCAL_WEB_ROOT" -type d -exec chmod 0755 {} +
sudo find "$LOCAL_WEB_ROOT" -type f -exec chmod 0644 {} +

info "Done. $LOCAL_WEB_ROOT is up to date."
