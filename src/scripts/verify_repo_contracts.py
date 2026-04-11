#!/usr/bin/env python3
# PROTECTED IMPLEMENTATION FILE
# Changes to this file must preserve repository contracts.
# See: src/spec/contracts.md and src/spec/ai-development-mode.md.
# This file is validated by CI.
from __future__ import annotations

import importlib.util
import json
import pathlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

# REPO  = repo root  (parent of src/)
# SRC   = src/       (spec, schemas, scripts, generator)
# BUILD = build/     (generated Ansible runtime, gitignored)
REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src"
BUILD = REPO / "build"
LOCK_FILE = SRC / ".generator.lock.yml"
GENERATED_HEADER = "GENERATED FILE"
PROTECTED_HEADER = "PROTECTED IMPLEMENTATION"

# The repository currently preserves scaffolds for these protected roles.
PROTECTED_ROLES = {
    "roles/certbot": 7,
    "roles/firewall_geo": 3,
    "roles/mailserver": 7,
    "roles/nextcloud": 5,
}

# Explicit scaffold markers used to identify known stub files.
SCAFFOLD_MARKERS = (
    "Placeholder for firewall_geo",
    "Placeholder for mailserver",
    "Placeholder for nextcloud",
)

SOURCE_OF_TRUTH_KEY = "source_of_truth"

# Protected files live in build/ (generated from FILE_MANIFEST in src/).
PROTECTED_FILES = [
    "roles/firewall_geo/tasks/main.yml",
    "roles/firewall_geo/handlers/main.yml",
    "roles/mailserver/tasks/main.yml",
    "roles/mailserver/handlers/main.yml",
    "roles/nextcloud/tasks/main.yml",
]

# Required source files in SRC (not build/).
REQUIRED_SRC_FILES = [
    "PROMPT.md",
    ".prompt.sha256",
    ".prompt.version",
    ".generator.lock.yml",
    "generate_ansible_enterprise.py",
    "spec/contracts.md",
    "spec/ai-development-mode.md",
    "scripts/generation_contracts.yml",
    "scripts/known_gaps.yml",
    "scripts/verify_repo_contracts.py",
    "scripts/verify_checkpoints.py",
    "schemas/services.schema.json",
]

# Each runtime script that contains testable logic must have a corresponding
# test file. The mapping is: script_path (relative to src/) -> test file name.
REQUIRED_TEST_COVERAGE = {
    "../build/roles/geoip/files/geoip_ingest.py":    "test_geoip_ingest.py",
    "../build/roles/dns/files/dns-bump-serial":        "test_dns_bump_serial.py",
    "scripts/resolve_service_order.py":               "test_resolve_service_order.py",
    "scripts/validate_services_schema.py":            "test_services_schema.py",
    "scripts/resolve_capabilities.py":                "test_resolve_capabilities.py",
    "scripts/derive_dns_zones.py":                    "test_derive_dns_zones.py",
    "../build/roles/dns/files/sync_dns_records.py":   "test_sync_dns_records.py",
}

# Required files at repo root (hand-managed, not generated).
REQUIRED_ROOT_FILES = [
    "README.md",
    "CODEOWNERS",
    ".gitignore",
    "Makefile",
    "ansible.cfg",
]

# The committed repo must not contain obviously local/operator-specific
# configuration examples copied from a real environment. Keep this list small
# and explicit so generic documentation examples remain usable.
LOCAL_CONFIG_FORBIDDEN_PATTERNS = {
    r"\bgregoriusgild\b": "private domain fragment 'gregoriusgild'",
    r"\bkjsl\b": "private domain fragment 'kjsl'",
    r"\bpve-nuc\b": "local Proxmox node naming pattern 'pve-nuc'",
    r"\bautomator_nosep\b": "local Proxmox API token example 'automator_nosep'",
    r"\b192\.168\.20\.\d{1,3}\b": "private LAN address in committed example content",
    r"\bhome\.lan\b": "local search/domain example 'home.lan'",
}

LOCAL_CONFIG_SCAN_ROOTS = [
    REPO / "README.md",
    REPO / "docs",
    SRC,
]

LOCAL_CONFIG_EXEMPT_PATHS = {
    SRC / "scripts" / "verify_repo_contracts.py",
    SRC / "scripts" / "tests" / "test_verify_repo_contracts.py",
}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_generator_module():
    spec = importlib.util.spec_from_file_location(
        "repo_generator", SRC / "generate_ansible_enterprise.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def verify_required_files(module) -> None:
    # Source files in SRC
    missing_src = [p for p in REQUIRED_SRC_FILES if not (SRC / p).exists()]
    if missing_src:
        fail("Missing required src/ files:\n" + "\n".join(missing_src))
    # Root-level hand-managed files
    missing_root = [p for p in REQUIRED_ROOT_FILES if not (REPO / p).exists()]
    if missing_root:
        fail("Missing required root files:\n" + "\n".join(missing_root))
    # Build files (generated)
    missing_build = [p for p in module.FILE_MANIFEST if not (BUILD / p).exists()]
    if missing_build:
        fail("Missing build/ files (run: make generate):\n" + "\n".join(missing_build))


def verify_generated_header(path: str) -> None:
    full_path = BUILD / path
    if not full_path.exists():
        fail(f"missing generated file in build/: {path}")
    head = read_text(full_path)[:400]
    if GENERATED_HEADER not in head and "MANAGED FILE" not in head and '"$comment"' not in head:
        fail(f"build/{path} missing generated-file header")


def verify_protected_header(path: str) -> None:
    full_path = BUILD / path
    if not full_path.exists():
        fail(f"missing protected file in build/: {path}")
    head = read_text(full_path)[:400]
    if PROTECTED_HEADER not in head and "MANAGED FILE" not in head:
        fail(f"build/{path} missing protected-file header")


def verify_generation_contracts(module) -> None:
    contracts_path = SRC / "scripts" / "generation_contracts.yml"
    if not contracts_path.exists():
        fail(f"missing generation contracts file: {contracts_path}")

    data = load_yaml(contracts_path)
    contracts = data.get("generated_contracts")
    if not isinstance(contracts, dict) or not contracts:
        fail("scripts/generation_contracts.yml must define a non-empty generated_contracts mapping")

    for manifest_path in module.FILE_MANIFEST:
        if manifest_path not in contracts:
            fail(f"{manifest_path} is in FILE_MANIFEST but missing from generation_contracts.yml")

    for managed_path, entry in contracts.items():
        if managed_path not in module.FILE_MANIFEST:
            fail(f"{managed_path} appears in generation_contracts.yml but not FILE_MANIFEST")
        if not isinstance(entry, dict):
            fail(f"generation contract entry for {managed_path} must be a mapping")
        sources = entry.get(SOURCE_OF_TRUTH_KEY)
        if not isinstance(sources, list) or not sources:
            fail(f"{managed_path} must declare a non-empty {SOURCE_OF_TRUTH_KEY} list")
        # source_of_truth paths are relative to SRC
        for source in sources:
            source_path = SRC / source
            if not source_path.exists():
                fail(f"{managed_path} declares missing source_of_truth path: src/{source}")


def file_contains_only_whitespace(path: Path) -> bool:
    return read_text(path).strip() == ""


def file_is_scaffold(text: str) -> bool:
    return any(marker in text for marker in SCAFFOLD_MARKERS)


def verify_role_contracts() -> None:
    for role_path, minimum_count in PROTECTED_ROLES.items():
        role_root = BUILD / role_path
        if not role_root.exists():
            fail(f"missing protected role in build/: {role_path}")

        files = [
            path for path in role_root.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        ]

        if len(files) < minimum_count:
            fail(f"{role_path} violates minimum file count: {len(files)} < {minimum_count}")

        main_tasks = role_root / "tasks" / "main.yml"
        if not main_tasks.exists():
            fail(f"{role_path} is missing tasks/main.yml")

        if file_contains_only_whitespace(main_tasks):
            fail(f"{role_path} has empty tasks/main.yml")

        main_text = read_text(main_tasks)
        if not file_is_scaffold(main_text):
            non_comment_lines = [
                line for line in main_text.splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            ]
            if not non_comment_lines:
                fail(f"{role_path} tasks/main.yml contains no executable content")


def verify_managed_roots_covered(module) -> None:
    from pathlib import PurePosixPath
    manifest_paths = {PurePosixPath(p) for p in module.FILE_MANIFEST}
    for root_name in module.MANAGED_ROOTS:
        root = BUILD / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts:
                continue
            rel = PurePosixPath(path.relative_to(BUILD).as_posix())
            if rel not in manifest_paths and str(rel) not in module.UNMANAGED_FILES:
                fail(f"File under managed build/ root missing from FILE_MANIFEST: {rel}")


def verify_export_hygiene() -> None:
    result = subprocess.run(
        ["git", "ls-files", "--cached"],
        capture_output=True, text=True, cwd=str(REPO)
    )
    for line in result.stdout.splitlines():
        if "__pycache__" in line:
            fail(f"repository has committed cache file: {line}")
        if line.startswith("build/"):
            fail(f"build/ file should not be committed: {line}")


def find_local_config_violations() -> list[str]:
    violations: list[str] = []
    text_paths: list[Path] = []

    for root in LOCAL_CONFIG_SCAN_ROOTS:
        if not root.exists():
            continue
        if root.is_file():
            text_paths.append(root)
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts:
                continue
            if path.suffix in {".pyc", ".zip"}:
                continue
            if path in LOCAL_CONFIG_EXEMPT_PATHS:
                continue
            text_paths.append(path)

    for path in text_paths:
        try:
            text = read_text(path)
        except UnicodeDecodeError:
            continue
        try:
            rel = path.relative_to(REPO)
        except ValueError:
            rel = path
        for pattern, label in LOCAL_CONFIG_FORBIDDEN_PATTERNS.items():
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            line_no = text[:match.start()].count("\n") + 1
            violations.append(f"{rel}:{line_no}: contains {label}")

    return violations


def verify_local_config_scrubbed() -> None:
    violations = find_local_config_violations()
    if violations:
        fail(
            "Repository contains local configuration identifiers that must be scrubbed:\n"
            + "\n".join(violations)
        )


def verify_lock(module) -> None:
    if not LOCK_FILE.exists():
        fail("Missing src/.generator.lock.yml")
    lock_data = yaml.safe_load(LOCK_FILE.read_text(encoding="utf-8")) or {}
    expected = module.compute_lock_data(BUILD)
    for key in ("source_hash", "output_hash", "generated_files", "source_files"):
        if lock_data.get(key) != expected.get(key):
            fail(f"src/.generator.lock.yml is stale for key: {key} "
                 f"(run: make generate)")


def verify_regenerated_tree(module) -> None:
    staging = SRC / ".regen-staging-verify"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    module.generate(staging)
    try:
        for rel_path in sorted(module.FILE_MANIFEST):
            actual = (BUILD / rel_path).read_bytes()
            staged = (staging / rel_path).read_bytes()
            if actual != staged:
                fail(f"Generated file drift detected: build/{rel_path} "
                     f"(run: make generate)")
    finally:
        shutil.rmtree(staging)


def verify_checkpoints() -> None:
    result = subprocess.run(
        ["python3", str(SRC / "scripts/verify_checkpoints.py")],
        capture_output=True, text=True, cwd=str(REPO)
    )
    if result.returncode != 0:
        fail("Checkpoint validation failed:\n" + result.stderr)


def verify_vhost_template_coverage() -> None:
    """For each non-generic app.type in the schema, a vhost template must exist."""
    schema_path = SRC / "schemas" / "services.schema.json"
    if not schema_path.exists():
        fail("src/schemas/services.schema.json missing")

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        app_type_enum = (
            schema["definitions"]["service"]["properties"]["app"]
            ["properties"]["type"]["enum"]
        )
    except KeyError:
        fail("Cannot read app.type enum from services.schema.json")

    # App types that are backend servers (not nginx-specific templates).
    # These use the standard proxy vhost template via upstream port.
    backend_types = {"apache2"}

    for app_type in app_type_enum:
        if app_type == "generic" or app_type in backend_types:
            continue
        tmpl = BUILD / "roles" / "nginx" / "templates" / f"{app_type}.conf.j2"
        if not tmpl.exists():
            fail(
                f"app.type '{app_type}' is in schema enum but "
                f"build/roles/nginx/templates/{app_type}.conf.j2 does not exist."
            )

    render = BUILD / "roles" / "nginx" / "tasks" / "render_service.yml"
    if render.exists():
        render_text = render.read_text(encoding="utf-8")
        for app_type in app_type_enum:
            if app_type == "generic" or app_type in backend_types:
                continue
            if app_type not in render_text:
                fail(
                    f"app.type '{app_type}' has a vhost template but is not "
                    f"referenced in build/roles/nginx/tasks/render_service.yml."
                )


def verify_service_start_coverage() -> None:
    """Roles that install a service package must also start and enable it."""
    SERVICE_PACKAGES = {
        "nginx", "php-fpm", "bind", "bind9", "mariadb-server",
        "postfix", "dovecot", "dovecot-core", "opendkim",
    }
    roles_dir = BUILD / "roles"
    if not roles_dir.exists():
        return

    for role_dir in sorted(roles_dir.iterdir()):
        if not role_dir.is_dir():
            continue
        tasks_dir = role_dir / "tasks"
        if not tasks_dir.exists():
            continue

        all_task_text = ""
        for task_file in sorted(tasks_dir.rglob("*.yml")):
            all_task_text += task_file.read_text(encoding="utf-8") + "\n"

        has_service_pkg = any(
            f"name: {pkg}" in all_task_text or f'name: "{pkg}"' in all_task_text
            for pkg in SERVICE_PACKAGES
        )
        if not has_service_pkg:
            continue

        has_start = "state: started" in all_task_text
        if not has_start:
            fail(
                f"{role_dir.name} installs a service package but has no "
                f"'state: started' task. Add a service: state: started task."
            )


def verify_known_gaps() -> None:
    """Report open known gaps; fail on blocking ones."""
    gaps_path = SRC / "scripts" / "known_gaps.yml"
    if not gaps_path.exists():
        return

    data = yaml.safe_load(gaps_path.read_text(encoding="utf-8")) or {}
    gaps = data.get("gaps", [])

    blocking_open = []
    nonblocking_open = []

    for gap in gaps:
        status = gap.get("status", "open")
        if status == "closed":
            fail(
                f"known_gaps.yml: gap '{gap.get('id')}' is marked closed. "
                f"Remove it from known_gaps.yml."
            )
        if gap.get("blocking", False):
            blocking_open.append(gap)
        else:
            nonblocking_open.append(gap)

    if nonblocking_open:
        for gap in nonblocking_open:
            print(
                f"WARNING: open gap [{gap.get('id')}]: {gap.get('description')}",
                file=sys.stderr,
            )

    if blocking_open:
        descriptions = "\n".join(
            f"  [{g.get('id')}] {g.get('description')}" for g in blocking_open
        )
        fail(f"Blocking known gaps must be resolved before merging:\n{descriptions}")


def verify_role_order() -> None:
    """Assert build/site.yml lists roles in the required dependency order."""
    site_yml_path = BUILD / "site.yml"
    if not site_yml_path.exists():
        fail("build/site.yml is missing")

    plays = yaml.safe_load(site_yml_path.read_text(encoding="utf-8")) or []
    if not isinstance(plays, list) or not plays:
        fail("build/site.yml contains no plays")

    role_sequence = []
    for play in plays:
        for role_entry in play.get("roles", []):
            if isinstance(role_entry, str):
                role_sequence.append(role_entry)
            elif isinstance(role_entry, dict):
                role_sequence.append(role_entry.get("role", ""))

    def pos(name):
        try:
            return role_sequence.index(name)
        except ValueError:
            return None

    CONSTRAINTS = [
        ("dns",     "certbot",   "dns before certbot: BIND must run before nsupdate"),
        ("certbot", "nginx",     "certbot before nginx: certs must exist before nginx starts TLS vhosts"),
        ("users",   "nextcloud", "users before nextcloud: service owner account must exist"),
    ]

    for before, after, reason in CONSTRAINTS:
        p_before = pos(before)
        p_after  = pos(after)
        if p_before is None or p_after is None:
            continue
        if p_before >= p_after:
            fail(
                f"site.yml role order violation: {reason}. "
                f"'{before}' at position {p_before}, '{after}' at position {p_after}."
            )


def verify_variable_contracts() -> None:
    """Verify templates do not reference variables not guaranteed at render time."""
    import re as _re

    schema_path = SRC / "schemas" / "services.schema.json"
    if not schema_path.exists():
        fail("src/schemas/services.schema.json missing")

    schema  = json.loads(schema_path.read_text(encoding="utf-8"))
    svc_def = schema["definitions"]["service"]
    always_req = set(svc_def.get("required", []))

    TEMPLATE_GUARANTEED = {
        "site.conf.j2":             always_req | {"web", "security"},
        "client_cert_site.conf.j2": always_req | {"web", "security"},
        "nextcloud.conf.j2":        always_req | {"app", "security"},
    }

    for tmpl_name, guaranteed in TEMPLATE_GUARANTEED.items():
        tmpl_path = BUILD / "roles" / "nginx" / "templates" / tmpl_name
        if not tmpl_path.exists():
            continue
        text = tmpl_path.read_text(encoding="utf-8")
        blocks = _re.findall(r"\{\{(.*?)\}\}", text, _re.DOTALL) + \
                 _re.findall(r"\{%(.*?)%\}", text, _re.DOTALL)
        for block in blocks:
            if "| default" in block or "|default" in block:
                continue
            for field in _re.findall(r"svc\.([a-zA-Z_]\w*)", block):
                if field not in guaranteed:
                    fail(
                        f"build/roles/nginx/templates/{tmpl_name}: "
                        f"svc.{field} accessed without | default() and "
                        f"'{field}' is not guaranteed for this template type."
                    )

    known_vars: set = set()
    for defaults_file in sorted(BUILD.glob("roles/*/defaults/main.yml")):
        data = yaml.safe_load(defaults_file.read_text(encoding="utf-8")) or {}
        known_vars.update(str(k) for k in data.keys())
    for gv_path in (BUILD / "group_vars" / "all" / "main.yml",
                    BUILD / "group_vars" / "all" / "vault.yml.example"):
        if gv_path.exists():
            data = yaml.safe_load(gv_path.read_text(encoding="utf-8")) or {}
            known_vars.update(str(k) for k in data.keys())

    MAGIC = {
        "ansible_os_family", "ansible_default_ipv4", "ansible_hostname",
        "ansible_facts", "ansible_distribution", "ansible_all_ipv4_addresses",
        "hostvars", "groups", "group_names", "inventory_hostname",
        "playbook_dir", "role_path",
        "item", "svc", "service", "loop", "result",
    }

    for tmpl_file in sorted(BUILD.glob("roles/*/templates/*.j2")):
        text = tmpl_file.read_text(encoding="utf-8")
        loop_vars = set(_re.findall(r"\{%[^%]*for\s+(\w+)\s+in\b", text))
        issues = []
        for expr in _re.findall(r"\{\{(.*?)\}\}", text, _re.DOTALL):
            if "| default" in expr or "|default" in expr:
                continue
            m = _re.match(r"\s*([a-zA-Z_]\w*)", expr)
            if not m:
                continue
            varname = m.group(1)
            if varname in MAGIC or varname in loop_vars or varname.startswith("_"):
                continue
            if varname not in known_vars:
                issues.append((varname, expr.strip()[:80]))

        if issues:
            rel = tmpl_file.relative_to(REPO).as_posix()
            seen = set()
            for varname, ctx in issues:
                if varname in seen:
                    continue
                seen.add(varname)
                fail(
                    f"{rel}: variable '{varname}' used without | default() "
                    f"and not declared in role defaults, group_vars, or vault. "
                    f"Context: {ctx!r}"
                )



def verify_capability_contracts() -> None:
    """Every requires[] entry in services must name a key in capabilities."""
    import json as _json

    schema_path = SRC / "schemas" / "services.schema.json"
    main_yml = BUILD / "group_vars" / "all" / "main.yml"
    if not schema_path.exists() or not main_yml.exists():
        return

    data = load_yaml(main_yml)
    capabilities = data.get("capabilities", {}) or {}
    services = data.get("services", {}) or {}

    known_caps = set(capabilities.keys())
    errors = []
    for svc_name, svc in services.items():
        if not svc.get("enabled", False):
            continue
        for cap in svc.get("requires", []):
            if cap not in known_caps:
                errors.append(
                    f"services.{svc_name}.requires: unknown capability '{cap}'. "
                    f"Known: {sorted(known_caps)}"
                )
    if errors:
        fail("Capability contract violations:\n" + "\n".join(errors))


def verify_unit_tests() -> None:
    """Run the unit test suite and fail the contract if any test fails.

    Checks:
    1. The tests directory exists.
    2. Every script in REQUIRED_TEST_COVERAGE has a corresponding test file.
    3. The full test suite passes (exit code 0). Skipped tests are permitted;
       failures and errors are not.
    """
    tests_dir = SRC / "scripts" / "tests"
    if not tests_dir.exists():
        fail(
            f"Unit test directory {tests_dir} is missing. "
            f"Run: mkdir -p src/scripts/tests"
        )

    # Check each required script has a test file
    missing_tests = []
    for script_rel, test_file in REQUIRED_TEST_COVERAGE.items():
        script_path = (SRC / script_rel).resolve()
        if not script_path.exists():
            fail(
                f"Test coverage mapping references missing script: {script_path}. "
                f"Update REQUIRED_TEST_COVERAGE in verify_repo_contracts.py."
            )
        if not (tests_dir / test_file).exists():
            missing_tests.append((script_rel, test_file))

    if missing_tests:
        descriptions = "\n".join(
            f"  {s} -> scripts/tests/{t}" for s, t in missing_tests
        )
        fail(
            f"The following scripts lack required test coverage:\n{descriptions}\n"
            f"Add a test file for each script listed above."
        )

    # Run the test suite
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover",
         "-s", "scripts/tests", "-p", "test_*.py"],
        cwd=SRC,
        capture_output=True,
        text=True,
    )

    # Parse the summary line to distinguish failures/errors from skips
    summary = result.stderr  # unittest writes to stderr
    if result.returncode != 0:
        fail(
            f"Unit tests failed. Fix all failures before merging.\n"
            f"{summary.strip()}"
        )


def main() -> None:
    module = load_generator_module()

    if not BUILD.exists():
        fail(f"build/ directory does not exist. Run: make generate")

    verify_required_files(module)

    skip_gitkeep = {k for k in module.FILE_MANIFEST if k.endswith(".gitkeep")}
    for rel_path in module.FILE_MANIFEST:
        if rel_path in skip_gitkeep:
            continue
        if rel_path in PROTECTED_FILES:
            verify_protected_header(rel_path)
        else:
            verify_generated_header(rel_path)

    verify_generation_contracts(module)
    verify_managed_roots_covered(module)
    verify_role_contracts()
    verify_vhost_template_coverage()
    verify_service_start_coverage()
    verify_known_gaps()
    verify_role_order()
    verify_variable_contracts()
    verify_capability_contracts()
    verify_lock(module)
    verify_export_hygiene()
    verify_local_config_scrubbed()
    verify_regenerated_tree(module)
    verify_unit_tests()
    verify_checkpoints()

    print("repository contracts verified successfully")


if __name__ == "__main__":
    main()
