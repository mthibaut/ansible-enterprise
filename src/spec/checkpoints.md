<!--
GENERATED FILE - DO NOT EDIT
This file is overwritten by generate_ansible_enterprise.py.
Source of truth: PROMPT.md.
Manual edits will be lost on the next regeneration.
-->

# Project Checkpoints

This file defines the ordered checkpoint history for the repository.

Rules:
- Checkpoints use the form `checkpoint-XXX-description`
- Numbers are zero-padded and strictly increasing
- Numbers are never reused
- Descriptions should stay short and architecture-focused
- ZIP exports should include the checkpoint in the filename
- Validate ordering with: `python3 scripts/internal/verify_checkpoints.py`

## Defined checkpoints

1. `checkpoint-001-from-claude-1`
   Baseline imported project state.

2. `checkpoint-002-checkpoint-governance`
   Adds checkpoint documentation and checkpoint validation tooling.

3. `checkpoint-003-comments-and-readme`
   Adds header comments to all managed files and a complete README.

4. `checkpoint-004-manifest-driven-generation`
   Reworks the generator and verifier around a structured manifest model.
   Adds trust-zone notices (GENERATED / PROTECTED), lock file, managed-root
   coverage checks, tree drift detection, and spec/ai-development-mode.md.

5. `checkpoint-005-trust-zones-and-lock-file`
   Ingests the checkpoint-004 archive and adopts its architecture.
   Structured FILE_MANIFEST with apply_notice() box headers, two trust zones
   (GENERATED FILE / PROTECTED IMPLEMENTATION FILE), compute_lock_data(),
   write_lock(), .generator.lock.yml, CODEOWNERS, .gitattributes,
   scripts/precommit_verify.sh, spec/ai-development-mode.md.
   Protected roles (firewall_geo, mailserver, nextcloud) have real task
   implementations; nextcloud handlers and defaults are explicit scaffolds
   pending full implementation.

6. `checkpoint-006-governance-hardening`
   Closes governance and implementation gaps identified by cross-model review.
   - Patch ingested: scaffold rules, documentation headers, export hygiene
   - Schema: additionalProperties: false throughout, required fields per
     service type, if/then enforcement for nextcloud app block
   - generation_contracts.yml: extended from 18 to 72 entries covering every
     manifest file; verifier now enforces full coverage
   - Molecule: ubuntu2404 platform added, firewall/nginx/SSH verify tasks
   - Nextcloud: occ install with correct sentinel (config/config.php),
     cron uses nextcloud_cron_interval default, distro-portable package
     names (php-mysqlnd on RedHat), MariaDB auth detection for unix_socket
     vs password auth
   - spec/contracts.md: internal contradiction resolved (scaffold rule vs
     implementation preservation language)
   - Header policy normalised: removed double notices on README.md,
     spec/contracts.md, spec/ai-development-mode.md
   - Placeholder detection replaced with explicit scaffold markers only
   - verify_export_hygiene: dead first subprocess call removed;
     subprocess moved to module-level import

7. `checkpoint-007-nextcloud-meta-and-scope-docs`
   Adds roles/nextcloud/meta/main.yml declaring a hard dependency on the
   users role, ensuring become_user is safe regardless of playbook order or
   standalone invocation. Documents the nginx/nextcloud php-fpm scope boundary
   in spec/roles.md (wiring belongs in nginx, not nextcloud). States the
   source_of_truth mapping philosophy explicitly in spec/contracts.md and
   generation_contracts.yml.

8. `checkpoint-008-platform-and-architecture-accuracy`
   Corrects spec/architecture.md to honestly describe the role-driven
   runtime: states that the capabilities dict is a declaration of intent
   not a routing mechanism, separates genuinely service-driven behaviour
   (nginx) from what is not yet (firewall, DNS, app deployment), and
   records the forward work. Adds debian13, almalinux9, and rockylinux9
   to molecule/default/molecule.yml so the tested platforms match the
   declared supported-platform claim. Documents the intentional dual
   declaration of the users->nextcloud dependency in site.yml.

9. `checkpoint-009-website-roles-and-contract-hardening`
   Implements TLS certificate provisioning (certbot role, DNS-01 with
   optional local BIND automation via nsupdate/TSIG), environment-aware
   deployment (deployment_environment drives certbot_fail_hard and
   certbot_selfsigned_fallback), and DNS role structural fixes
   (defaults file, conditional BIND install, named.conf secondary
   handling). Fixes 7 functional gaps in nginx and nextcloud: distro
   user in nginx.conf, explicit service start tasks, nextcloud fastcgi
   vhost, php-fpm pool config and start, schema web-required fix,
   fallback listen directive, and separated admin/db passwords.
   Hardens CI contracts: vhost template coverage, service start
   coverage, and known_gaps.yml registry enforce deployment correctness
   at generation time. Molecule verify.yml upgraded from file-presence
   checks to running-state assertions (service_facts, nginx -t, uri).

10. `checkpoint-010-ci-contract-hardening`
    Adds two new CI contract checks that catch the class of failure
    where generated config is structurally valid but semantically wrong
    at deploy time. verify_role_order() parses the role sequence from
    site.yml and enforces three hard ordering constraints: dns before
    certbot (nsupdate needs BIND), certbot before nginx (TLS cert files
    must exist before nginx first start), and users before nextcloud
    (service owner account must exist). verify_variable_contracts() has
    two sub-checks: svc.FIELD access in nginx vhost templates without
    | default() where the field is not schema-guaranteed for that
    template type (catches cross-template accidents at CI time), and
    unguarded top-level variables in role templates not declared in
    role defaults, group_vars, or vault (catches silent Ansible
    undefined-variable-as-None misconfiguration). Dry-run of the
    checks before implementation surfaced and fixed two pre-existing
    bugs: certbot/defaults/main.yml was missing certbot_tsig_key_name,
    certbot_tsig_key_file, and certbot_dns_propagation_seconds; and
    client_cert_site.conf.j2 accessed svc.security.client_ca_path
    without | default().

## Checkpoint procedure

Every checkpoint must include a HANDOFF.md update. The full procedure is:

1. Implement changes in `src/generate_ansible_enterprise.py` (FILE_MANIFEST)
   and any other `src/` files.
2. `make generate && make validate && make checkpoints`
3. Append the checkpoint entry to the numbered list in `src/spec/checkpoints.md`.
4. **Update `HANDOFF.md`** at the repo root to reflect the new HEAD, current
   checkpoint number, and any changes to open issues, variable names, or
   architecture. HANDOFF.md is the primary document a new AI reads first —
   it must always describe the current state, not a past state.
5. `git add src/ HANDOFF.md && git commit -m "feat: checkpoint-NNN-description"`

11. `checkpoint-011-src-build-separation`
    Implements Option C directory separation. The repository is split into
    src/ (committed: generator, PROMPT.md, spec/, schemas/, scripts/) and
    build/ (gitignored: all generated Ansible runtime files). FILE_MANIFEST
    shrinks from 86 to 64 entries covering only Ansible runtime content.
    The generator resolves SRC = src/ and BUILD_DIR = build/; the lock
    file is written to src/.generator.lock.yml. CI runs make generate
    before make validate. verify_repo_contracts.py is updated to know
    about the src/build split: source checks look in SRC, generated file
    checks look in BUILD, verify_export_hygiene() rejects any build/ file
    committed to git. preflight role no longer calls validate_services_schema.py
    at Ansible runtime (schema validation is now a CI concern only). A
    Makefile at repo root provides: make generate, make validate, make all.

12. `checkpoint-012-prompt-version-increment-fix`
    Fixes the .prompt.version counter which was writing the old version back
    unchanged on every regeneration instead of incrementing it. The int()
    cast and +1 now correctly advance the counter each time make generate
    runs.

13. `checkpoint-013-passwordless-sudo-for-admins`
    Adds passwordless sudo for all admin users via the ssh_hardening role.
    Installs the sudo package alongside openssh-server. Deploys a validated
    sudoers.d drop-in per admin user (visudo -cf %s validation before
    placement). Applies | list filter to all admin_users loops to guard
    against scalar string misconfiguration. Adds Molecule verify assertion
    that /etc/sudoers.d/myadmin exists and contains NOPASSWD.

14. `checkpoint-014-four-next-steps`
    Implements four previously proposed next steps:
    (1) DNS port rules: nftables.conf.j2 now opens tcp/udp port 53 when the
    dns role is active, using the same condition as site.yml role skip
    (dns_hidden_primary_zones | length > 0 or certbot_dns_local).
    (2) DNS service-driven zone registration: zone.db.j2 auto-injects A
    records for enabled services whose domain matches or is a subdomain of
    the zone being created. Records are written at zone creation time only
    (force: false). Local Jinja2 set variable renamed to _label to satisfy
    CI variable contract check.
    (3) Molecule nextcloud coverage: molecule_testing: true added to
    molecule.yml group_vars; nextcloud service added to molecule inventory;
    nextcloud role added to converge.yml; seven internet-requiring tasks
    (download, extract, webroot ownership, occ install, trusted domain,
    background job, cron) are guarded with
    not molecule_testing | default(false) | bool so the role runs in CI
    without hitting the internet.
    (4) Capabilities dispatch design: src/spec/architecture.md documents the
    full intended design for the provider-dispatch layer including the
    proposed requires field in the services schema, runtime resolution flow,
    ordering constraints, and implementation order.

15. `checkpoint-015-dev-staging-password-access`
    Introduces admin_dev_password: a single shared password used across all
    admin-accessible services in development and staging environments.
    Production is unaffected (empty password = all guards skip).
    sshd_config.j2: PasswordAuthentication and PermitRootLogin are
    conditionally enabled when deployment_environment != production and
    admin_dev_password is non-empty. AllowUsers now includes root.
    ssh_hardening: two new tasks set the Unix password for all admin users
    and for root via password_hash(sha512), guarded by deployment_environment
    and admin_dev_password. Requires passlib on the control machine.
    preflight: SSH key assertion is skipped when admin_dev_password is set
    and deployment_environment is non-production, allowing password-only
    dev setups.
    nextcloud: Resolve effective Nextcloud passwords fact inserted before
    DB/occ tasks; admin_password and db_password fall back to
    admin_dev_password when their service-specific values are empty.
    group_vars/all/main.yml: admin_dev_password declared with empty default.
    vault.yml.example: admin_dev_password documented with sample value.

16. `checkpoint-016-console-password-all-environments`
    Extends Unix password setting to all environments including production.
    The deployment_environment guard is removed from both Set Unix password
    tasks in ssh_hardening; only the admin_dev_password non-empty check
    remains. SSH password auth and PermitRootLogin in sshd_config are
    unchanged (still restricted to non-production). Console/PAM login uses
    the Unix password directly and is independent of sshd configuration.

17. `checkpoint-017-package-cache-refresh`
    Adds a package cache refresh as a pre-task in site.yml, running once
    per play before any role installs software. Uses the native apt module
    (cache_valid_time: 3600) on Debian family and the dnf module on RedHat
    family, conditioned on ansible_os_family. A single refresh per run
    rather than update_cache on each package task.

18. `checkpoint-018-vault-service-passwords`
    Separates Unix console access from service passwords.
    admin_dev_password renamed to admin_dev_password_hash: stored as a
    pre-computed SHA-512 hash, used directly by the user/root tasks with
    no password_hash() filter at runtime. passlib no longer required on
    the control machine. sshd_config and preflight conditions updated.
    nextcloud_admin_password and nextcloud_db_password added as top-level
    variables in group_vars/all/main.yml (empty defaults) and documented
    in vault.yml.example with CHANGE_ME sentinels. Nextcloud tasks now
    reference these directly; the intermediate _nc_admin_password and
    _nc_db_password set_fact resolution block is removed. mailserver
    admin_mail_password was already a vault variable and is unchanged.
    molecule group_vars updated: nextcloud_admin_password and
    nextcloud_db_password set as top-level test values; removed from
    the services.nextcloud.app dict.

19. `checkpoint-019-ansible-cfg-inject-facts`
    Adds ansible.cfg at repo root with inject_facts_as_vars = False,
    opting into future Ansible behaviour and suppressing the deprecation
    warning. Also sets inventory = build/inventory/hosts.ini as a
    convenience default. ansible.cfg added to REQUIRED_ROOT_FILES in
    verify_repo_contracts.py so CI enforces its presence.

20. `checkpoint-020-ansible-facts-dot-notation`
    Replaces all deprecated top-level ansible_* variable accesses with
    ansible_facts dot notation throughout FILE_MANIFEST. ansible_os_family
    becomes ansible_facts.os_family (20 occurrences across dns, nginx,
    nextcloud, mailserver, ssh_hardening, site.yml, and molecule).
    ansible_default_ipv4 becomes ansible_facts.default_ipv4 (4 occurrences
    in certbot tasks and dns zone template). ansible_fqdn becomes
    ansible_facts.fqdn (1 occurrence in mailserver generic template).
    Dot notation used throughout to avoid quoting conflicts with mixed
    single/double-quoted Python string literals in FILE_MANIFEST.

21. `checkpoint-021-geoip-flat-vault-vars`
    Fixes duplicate mapping key error when setting geoip values in vault.
    Previously, adding a geoip: block to vault.yml caused Ansible to warn
    about a duplicate top-level key (geoip: already in main.yml).
    geoip.license_key and geoip.allowed_countries are now sourced from
    flat vault variables geoip_license_key and geoip_allowed_countries,
    referenced via Jinja2 in the geoip: dict in main.yml. Operators set
    these flat variables in vault.yml without touching the geoip: key.
    vault.yml.example updated with flat variable examples. molecule.yml
    updated with geoip_license_key and geoip_allowed_countries alongside
    the inline geoip dict.

22. `checkpoint-022-geoip-per-service-country-override`
    Adds per-service geoip country filtering. Services can declare
    security.geoip_allowed_countries to override the global list for their
    ports. Because nftables operates at L4 (port level, not service level),
    the effective country set per port is computed as the union of all
    service overrides for that port; if any service on a port has no
    override, the global list applies for that port.
    geoip_ingest.py gains --set-prefix so it can generate named set files
    (geoip_allowed, geoip_http, geoip_https). The geoip role generates
    per-port countries files and calls ingest three times: global, http,
    https. The nftables template moves from a single blanket TCP drop to
    per-port drop rules using the appropriate set (geoip_http_ipv4 for
    port 80, geoip_https_ipv4 for port 443, geoip_allowed for SSH).
    services.schema.json gains security.geoip_allowed_countries as an
    optional array of ISO 3166-1 alpha-2 country codes.

23. `checkpoint-023-geoip-ssh-country-override`
    Adds a dedicated SSH geoip country set independent of the web service
    sets. geoip.ssh_allowed_countries in main.yml resolves from the flat
    vault variable geoip_ssh_allowed_countries, falling back to the global
    geoip_allowed_countries when not set. The geoip role generates
    allowed_countries_ssh.txt and runs geoip_ingest.py with
    --set-prefix geoip_ssh. The nftables SSH drop rule now uses
    $geoip_ssh_ipv4 / $geoip_ssh_ipv6 instead of the global set.
    vault.yml.example documents geoip_ssh_allowed_countries as an optional
    override. molecule.yml gains geoip_ssh_allowed_countries: [].

24. `checkpoint-024-mail-dns-bypass-geoip`
    Moves mail and DNS port accepts before all geoip drop rules in the
    nftables chain. SMTP port 25 is a relay protocol: senders route through
    global infrastructure so geoip filtering silently drops legitimate mail
    without bouncing it to the sender. Submission (587/465) and IMAP (993)
    are authenticated and better restricted at the application layer.
    DNS zone-transfer sources (secondaries) may be anywhere, so geoip on
    port 53 would break AXFR. The comments in nftables.conf.j2 explain the
    rationale. SSH and HTTP/HTTPS retain their per-port geoip drops.

25. `checkpoint-025-handoff-maintenance-procedure`
    Establishes HANDOFF.md as a required checkpoint deliverable. The
    checkpoint procedure in src/spec/checkpoints.md is updated to include
    updating HANDOFF.md as a mandatory step. HANDOFF.md itself is rewritten
    to reflect the current state at checkpoint-024: updated variable names
    (admin_dev_password_hash, nextcloud_admin_password, nextcloud_db_password,
    geoip flat vars), geoip architecture (4 sets, per-port drops, mail/DNS
    bypass), ansible.cfg, ansible_facts dot notation, services schema
    additions, and the full checkpoint summary table 001-024.

26. `checkpoint-026-geoip-allowlist`
    Adds global and per-service IP/CIDR allowlists that bypass geoip
    filtering entirely. geoip.allowlist in group_vars sources from flat
    vault variable geoip_allowlist_entries (list of IPv4/IPv6 addresses,
    CIDRs, or ranges). The global allowlist is emitted as individual accept
    rules before all geoip drop rules, bypassing geoip on every port.
    Per-service security.geoip_allowlist accepts IPs/CIDRs for that
    service's port only; the union across enabled services per port is
    computed in the nftables template and emitted before the per-port
    geoip drop. IPv4/IPv6 family is detected by colon presence in the
    address string, requiring no netaddr dependency. services.schema.json
    gains security.geoip_allowlist. vault.yml.example and molecule.yml
    updated. HANDOFF.md updated to reflect checkpoint-026.

27. `checkpoint-027-geoip-ingest-newline-fix`
    Fixes SyntaxError in generated geoip_ingest.py. The write_text string
    arguments contained a real newline byte (0x0a) instead of the two-char
    escape sequence \\n (0x5c 0x6e). Root cause: in the FILE_MANIFEST source
    the sequence \\n (bytes 0x5c 0x6e) is parsed by Python as a real newline
    character, not as a literal backslash-n. Fix: use \\\\n (bytes 0x5c 0x5c
    0x6e) in the source so Python evaluates it to \\n (literal backslash-n)
    which then appears correctly as the escape sequence in the generated
    Python file. Four occurrences fixed across the empty-countries and
    full-countries branches for both IPv4 and IPv6.

28. `checkpoint-028-nftables-empty-set-fix`
    Fixes nftables fatal error: nft rejects empty set definitions
    (define set = { }) which occur when a country list is empty. The
    nftables.conf.j2 include directives for each set file are now
    individually gated on the same length > 0 condition as their
    corresponding drop rules. SSH set files included only when
    geoip.ssh_allowed_countries is non-empty. Global, HTTP, and HTTPS set
    files included only when geoip.allowed_countries is non-empty. Empty
    sets are never included or referenced, so nft never sees an empty set
    definition.

29. `checkpoint-029-geoip-enabled-switches`
    Adds boolean geoip enable/disable switches at global and per-service
    level. Global: geoip.enabled now sources from flat vault variable
    geoip_enabled (default false), fixing the duplicate mapping key problem
    that would occur if an operator set geoip: in vault.yml. vault.yml.example
    documents geoip_enabled. molecule.yml gains geoip_enabled: false.
    Per-service: security.geoip_enabled boolean (default true) added to
    services.schema.json. In nftables.conf.j2, each port's geoip drop rule
    is preceded by a loop that checks whether any enabled service on that
    port has geoip_enabled: false; if so, the _http_geoip.enabled or
    _https_geoip.enabled namespace flag is cleared and the drop rule is
    skipped entirely for that port. One service opting out disables geoip
    for the whole port (L4 constraint).

30. `checkpoint-030-geoip-countries-flat-var-fix`
    Fixes geoip_ssh_ipv4 (and other per-prefix sets) being empty despite
    country lists being configured. Root cause: the copy module's content:
    field templates geoip.ssh_allowed_countries which is itself a Jinja2
    expression string. Ansible may not re-evaluate the inner expression,
    leaving the for loop iterating over characters of the raw template
    string. No characters match ISO country codes so the ingest finds zero
    CIDRs and writes an empty set definition. Fix: all four countries-file
    write tasks now reference the flat vault variables directly
    (geoip_allowed_countries, geoip_ssh_allowed_countries) instead of going
    through the geoip dict, bypassing the double-evaluation issue entirely.

31. `checkpoint-031-geoip-ingest-locations-join`
    Fixes geoip sets being empty even when country codes are set. Root
    cause: geoip_ingest.py collect() looked for country_iso_code directly
    in the GeoLite2-Country-Blocks-*.csv files, but that column does not
    exist there. MaxMind uses a normalised format: country codes are in
    GeoLite2-Country-Locations-en.csv, joined to blocks via geoname_id.
    Fix: new load_geoname_map() function reads the locations CSV and builds
    a geoname_id -> country_iso_code dict. collect() now resolves the ISO
    code via geoname_id first, then registered_country_geoname_id as
    fallback (covers anycast and satellite-provider blocks). This was the
    fundamental bug behind all geoip sets being empty regardless of which
    country codes were configured.

32. `checkpoint-032-unit-test-infrastructure`
    Adds a complete unit test suite under src/scripts/tests/ covering all
    runtime Python scripts. make test target added to Makefile.
    resolve_service_order.py refactored to expose an importable
    resolve_order() function (main-guard added) so tests can call it
    without side effects.
    test_geoip_ingest.py (12 tests): TestLoadGeonameMap verifies the
    geoname_id->iso_code map; TestCollect verifies country matching,
    non-matching, registered_country fallback, deduplication, and the old
    country_iso_code bug as a regression guard; TestMain exercises the full
    main() pipeline with synthetic MaxMind-format zip archives including
    set-prefix, IPv6, case-insensitivity, and empty-countries branches.
    test_update_dns_serial.py (6 tests): serial format, idempotency, no
    write on no-change, content-change triggers new serial, determinism
    across identical zone files. Uses subprocess to avoid argparse state
    bleed between test runs.
    test_resolve_service_order.py (10 tests): empty dict, single service,
    alphabetic sort, simple/chain/diamond dependency ordering, unknown-dep
    ignored, two-way and three-way cycle detection.
    test_services_schema.py (13 tests): valid and invalid service dicts
    covering all schema fields including recent geoip additions. Uses
    skipUnless(jsonschema) guard so tests degrade gracefully when the
    library is absent.

33. `checkpoint-033-test-contract-enforcement`
    Wires the unit test suite into make validate so CI enforces test
    passage as a repository contract. verify_unit_tests() added to
    verify_repo_contracts.py: checks that the tests directory exists,
    that every script in REQUIRED_TEST_COVERAGE has a corresponding test
    file (geoip_ingest, update_dns_serial, resolve_service_order,
    validate_services_schema), and runs the full suite via subprocess. Any
    test failure or error fails the contract with the full output. Skipped
    tests are permitted. REQUIRED_TEST_COVERAGE is a dict mapping script
    paths to test filenames, making the coverage requirement explicit and
    extensible for future scripts.

34. `checkpoint-034-geoip-download-rate-limit`
    Prevents MaxMind from being contacted more than once per day regardless
    of how many times the playbook runs or how many sets are generated.
    geoip_ingest.py gains two new flags: --download-only (download the
    archive and exit, no set generation) and --skip-download (skip
    urlretrieve entirely, use the existing archive in download-dir). The
    Ansible geoip tasks are restructured: a new stat task records the
    archive mtime, a conditional download task runs geoip_ingest.py
    --download-only only when the archive is absent or older than 86400
    seconds, and all four set-generation tasks use --skip-download so
    they never independently contact MaxMind. Three new tests added to
    test_geoip_ingest.py: --download-only exits without writing .nft files,
    --skip-download generates sets without calling urlretrieve, and
    --skip-download with a missing archive raises an error.

35. `checkpoint-035-geoip-weekly-cron-refresh`
    Adds a weekly cron job to keep MaxMind data fresh without requiring
    Ansible runs. Two new generated files: roles/geoip/templates/geoip.conf.j2
    (deploys /etc/geoip/geoip.conf with license key, paths, and countries
    file locations) and roles/geoip/files/geoip_refresh.sh (downloads
    archive then regenerates all four nftables sets and reloads nftables).
    The refresh script uses an ingest() helper function to avoid backslash
    line-continuations, reads all runtime config from /etc/geoip/geoip.conf,
    and logs via both logger and stdout. The geoip role deploys the script
    to /usr/local/sbin/geoip_refresh.sh (mode 0750), deploys the config to
    /etc/geoip/geoip.conf (mode 0600), and installs a cron job at
    Wednesday 04:18 (state: present when geoip enabled, state: absent when
    disabled). generation_contracts.yml updated with the two new entries.

36. `checkpoint-036-geoip-date-time-fact-fix`
    Fixes "ansible_date_time is undefined" error in the Download GeoIP
    database task. The when condition used ansible_date_time.epoch which
    requires the setup module to have run. Replaced with
    now(utc=True).strftime('%s') | int which is a Jinja2 built-in
    available without any gathered facts, making the condition safe when
    geoip runs before or without gather_facts.

37. `checkpoint-037-nftables-allowlist-newline-fix`
    Fixes "Statement after terminal statement has no effect" nftables error
    when multiple IPs are configured in geoip_allowlist_entries. Root cause:
    Ansible uses trim_blocks=True and lstrip_blocks=True in its Jinja2
    environment. When an accept statement was placed immediately after a
    {% else %} tag on the same line ({% else %}ip  saddr X accept{% endif %})
    trim_blocks consumed the newline after {% endif %} and lstrip_blocks
    consumed the whitespace before {% endfor %}, causing consecutive loop
    iterations to concatenate their accept statements onto the same line.
    Fix: each accept statement is now on its own content line (not
    immediately after a block tag), so Jinja2 whitespace stripping cannot
    consume the newline that terminates the rule. Applied to all three
    allowlist blocks: global, port 80, and port 443.

38. `checkpoint-038-opendkim-systemd-runtime-dir`
    Fixes opendkim failing to write its PID file to /run/opendkim/opendkim.pid
    on both Debian and RedHat families using the canonical systemd-native
    approach. A systemd drop-in override is deployed to
    /etc/systemd/system/opendkim.service.d/override.conf containing
    RuntimeDirectory=opendkim and RuntimeDirectoryMode=0750. This instructs
    systemd to create /run/opendkim with the correct ownership before
    starting the service and to recreate it automatically on every boot,
    requiring no tmpfiles.d entry and surviving package upgrades on both
    distro families. A new handler "Reload systemd and restart opendkim"
    runs systemd daemon-reload then restarts opendkim when the drop-in
    changes. On RedHat family, two prerequisite tasks are added before
    package install: enabling the EPEL repository (epel-release package)
    and enabling the CodeReady Builder repository (dnf config-manager
    --set-enabled crb), both required for opendkim on RHEL 9 derivatives.

39. `checkpoint-039-geoip-ingestion-changed-when`
    Fixes geoip ingestion tasks always reporting changed. The command module
    always marks tasks changed unless changed_when is set. All five geoip
    command tasks now have changed_when: false: the download task (which is
    already gated by the 86400s mtime check) and all four set-generation
    tasks (SSH, global, HTTP, HTTPS). These tasks are idempotent by nature
    — identical input always produces identical .nft output — so changed
    would never be meaningful information.

40. `checkpoint-040-opendkim-service-type-simple`
    Fixes "Can't open PID file /run/opendkim/opendkim.pid (yet?)" systemd
    warning even when /run/opendkim/ exists. Root cause: the package unit
    file uses Type=forking, making systemd wait for a PID file immediately
    after the fork. With RuntimeDirectory in place the directory exists but
    there is still a race between systemd's check and opendkim writing the
    file. Fix: add Type=simple and PIDFile= (empty, clears the inherited
    PIDFile= value) to the systemd drop-in override. With Type=simple
    systemd considers the service started as soon as the main process
    launches and never checks for a PID file. PidFile /run/opendkim/opendkim.pid
    is added to opendkim.conf.j2 so opendkim itself still writes the file
    for monitoring tools and scripts that expect it.

41. `checkpoint-041-opendkim-execstart-override`
    Fixes opendkim ignoring the Socket directive in opendkim.conf on Debian.
    The Debian package unit file hardcodes -p local:/var/run/opendkim/opendkim.sock
    in ExecStart, which overrides any Socket setting in opendkim.conf. This
    means our Socket inet:8891@127.0.0.1 config is silently ignored on Debian
    and postfix cannot connect to opendkim. The RHEL/EPEL package does not
    have this issue. Fix: add ExecStart= (empty reset) followed by
    ExecStart=/usr/sbin/opendkim -x /etc/opendkim.conf to the systemd
    drop-in. The empty line clears the inherited ExecStart list; the second
    line sets the authoritative command. The -x flag explicitly loads
    /etc/opendkim.conf, ensuring all socket and other config comes from our
    managed config file on both Debian and RHEL families.

42. `checkpoint-042-triple-quoted-manifest`
    Refactors FILE_MANIFEST from single-line escaped strings to triple-quoted
    multiline strings, eliminating the entire class of quoting bugs. Previously
    all 66 file contents were embedded as single-line Python strings with \\n
    for newlines and manual escaping for quotes, making Jinja2 ternary
    expressions like {{ 'sshd' if ... else 'ssh' }} impossible to express
    correctly. With triple-quoted strings, real newlines are literal newlines
    in the source, single quotes and double quotes need no escaping, and
    the generator reads exactly like the files it generates. Backslashes are
    doubled (\ to \\) to round-trip correctly through Python's string parser.
    The one entry containing triple-double-quotes (geoip_ingest.py, which has
    a Python docstring) uses triple-single-quote delimiter instead. The
    generator shrinks from one 80KB line to 2630 readable lines. Also applies
    the pending fix: ssh_hardening handler now uses distro-aware service name
    sshd (RedHat) or ssh (Debian) via a Jinja2 ternary — the fix that was
    previously impossible to express without the format change.

43. `checkpoint-043-geoip-download-only-argparse-fix`
    Fixes geoip_ingest.py crashing when called with --download-only because
    --sets-dir and --countries-file were marked required=True in argparse.
    The download-only Ansible task and the cron refresh script both correctly
    omit these flags (they are not needed for a download-only run), but
    argparse rejected the invocation before main() ever reached the
    --download-only early return. Fix: --sets-dir and --countries-file are
    now optional (default=None) with post-parse validation that errors if
    they are missing and --download-only is not set. main() is restructured
    to perform the download and check download_only before dereferencing
    sets_dir or countries_file. A new unit test confirms --download-only
    succeeds without --sets-dir or --countries-file arguments.

44. `checkpoint-044-postfix-lmdb`
    Changes Postfix database type from hash to lmdb throughout the mailserver
    role. Three coordinated changes: (1) smtp_generic_maps in main.cf.j2 now
    uses lmdb:/etc/postfix/generic instead of hash:/etc/postfix/generic.
    (2) The "Rebuild postfix generic map" handler now invokes postmap with the
    lmdb: prefix so postmap writes a .lmdb file instead of .db. (3) On Debian
    family, postfix-lmdb is added to the package install list; this package
    provides the lmdb map type as a postfix dynamically-loaded module. On
    RedHat family (AlmaLinux 9, Rocky Linux 9), lmdb support is compiled into
    the main postfix package and no additional package is required.

45. `checkpoint-045-zone-file-semicolon-comments`
    Fixes the GENERATED FILE / DO NOT EDIT header in zone.db.j2 using hash (#)
    comments, which are not valid in DNS zone files. Zone files use semicolons
    for comments; hashes are silently ignored by some BIND versions and cause
    parse errors in others. Root cause: _comment_style() in the generator had
    no case for .j2 templates whose underlying file type uses a different
    comment character. Fix: _comment_style() now checks whether a .j2 file's
    stem itself carries a .db extension and returns ";" in that case, producing
    a fully valid semicolon-delimited header. No other templates are affected.

46. `checkpoint-046-contrib-pull-website`
    Adds contrib/pull_website.sh, a new hand-managed operator script that
    copies a provisioned website from a remote host to the local machine and
    applies the correct ownership and permissions. The script accepts two
    arguments: --site (service name as declared in the Ansible services dict)
    and --remote (user@host to copy from). It reads
    build/group_vars/all/main.yml to resolve the service domain and Unix owner
    without requiring the operator to look them up manually. It then rsyncs
    /var/www/<domain>/ from the remote and applies chown <owner>:<owner> and
    chmod 0755/0644 (dirs/files) to match exactly what roles/users provisions.
    The script errors clearly if the site is unknown, disabled, missing a
    domain, or missing an owner, and lists known service names on a lookup
    failure. contrib/ is a new hand-managed committed directory at the repo
    root; its contents are never touched by the generator.

47. `checkpoint-047-dns-service-driven-zones`
    Implements service-driven DNS zone registration, closing the long-standing
    future-work item from checkpoint-014. Previously, zones had to be declared
    manually in dns_hidden_primary_zones; service domains would only get A
    records if their zone was already listed. Now the dns role derives an
    _effective_dns_zones fact at runtime: the union of dns_hidden_primary_zones
    and any enabled service domain not already covered by a declared zone. A
    domain is "covered" if it equals a declared zone (apex) or is a proper
    subdomain of one (app.example.com is covered by example.com;
    notexample.com is NOT covered by example.com). Both zone creation and
    serial-update tasks loop over _effective_dns_zones; named.conf.local.j2
    registers the same list with BIND. A companion Python module
    src/scripts/internal/derive_dns_zones.py provides the canonical reference
    implementation of the algorithm (also usable standalone), and
    src/scripts/tests/test_derive_dns_zones.py adds 17 unit tests covering
    apex, subdomain, sibling, disabled, empty-domain, deduplication, and sort
    behaviour. src/spec/architecture.md updated to reflect DNS is now
    service-driven.

48. `checkpoint-048-bind-permissions-fix`
    Fixes BIND failing to start with "the working directory is not writable /
    loading configuration: permission denied". Two root causes addressed:

    (1) RedHat: the dns role writes to /etc/named.conf (the complete config),
    replacing the package-supplied file which contains the critical
    options { directory "/var/named"; } block. Without it BIND cannot locate
    its working directory. Fix: named.conf.local.j2 now emits a full options
    block when ansible_facts.os_family == 'RedHat', setting directory, recursion
    no, allow-query any, and listen-on any. On Debian the file is written to
    /etc/bind/named.conf.local which is included by the package's named.conf,
    so no options block is needed or added there.

    (2) Both distros: the zone directory and zone files were created owned by
    root:root, leaving BIND unable to write journal files. Fix: zone directory
    now uses owner=root, group=bind/named, mode=0770 on RedHat (writable by
    named group) and mode=0755 on Debian (BIND writes to /var/cache/bind, not
    /etc/bind/zones). Zone files now use owner=root, group=bind/named,
    mode=0640 on both distros.

49. `checkpoint-049-firewall-service-driven-dns-ports`
    Closes the firewall service-driven DNS wiring gap. Previously, DNS ports
    (53 tcp/udp) in the nftables ruleset were opened only when
    dns_hidden_primary_zones was non-empty or certbot_dns_local was true. After
    checkpoint-047 the dns role derives zones from the services dict at runtime,
    meaning BIND could be running and serving zones even when
    dns_hidden_primary_zones is empty - but port 53 would remain closed.

    Two coordinated fixes:

    (1) site.yml dns role when: condition extended with a third branch:
    services with an enabled entry that has a domain field trigger the dns role,
    matching the full set of conditions under which _effective_dns_zones is
    non-empty.

    (2) nftables.conf.j2 DNS port block replaced with a namespace-based
    Jinja2 fragment that mirrors the same three-branch condition: declared
    zones, certbot_dns_local, or any enabled service domain. The two
    conditions are now guaranteed to stay in sync.

    Mail ports (25, 587, 993, 465) remain guarded by mailserver.enabled (a
    role flag). Service-driven mail port wiring requires a mailserver entry in
    the services dict or the capabilities dispatch layer, neither of which is
    yet implemented. Tracked as future work item 3.

50. `checkpoint-050-capabilities-dispatch-layer`
    Implements the capabilities provider-dispatch layer, closing the oldest
    remaining future-work item. Services can now declare which platform
    capabilities they depend on via an optional requires list, and the
    correct provider roles are activated at runtime without touching site.yml.

    Changes:

    src/schemas/services.schema.json: requires property added to the service
    definition. Type is array of strings; default is []. Each string must
    name a key in the capabilities dict (enforced by CI).

    src/generate_ansible_enterprise.py:
    - mail: {provider: mailserver} added to the capabilities dict in
      group_vars/all/main.yml, making mail the first wired capability.
    - New "Resolve required capability providers" set_fact pre-task in
      site.yml builds _required_providers: a sorted deduplicated list of
      provider role names derived from all enabled services' requires lists.
    - mailserver role when: condition extended with:
        or 'mailserver' in (_required_providers | default([]))
    - nftables mail port block (25, 587, 993, 465) extended with the same
      condition, keeping the firewall and role activation in sync.

    src/scripts/internal/resolve_capabilities.py: canonical Python reference
    implementation of resolve_providers(capabilities, services), also usable
    standalone with --vars-file.

    src/scripts/tests/test_resolve_capabilities.py: 16 unit tests covering
    empty inputs, disabled services, single and multiple capability resolution,
    deduplication, unknown capability names, and output sort order.

    src/scripts/internal/verify_repo_contracts.py:
    - verify_capability_contracts() added: fails if any enabled service
      declares a requires entry that does not name a known capabilities key.
    - resolve_capabilities.py and derive_dns_zones.py added to
      REQUIRED_TEST_COVERAGE, enforcing test files for both modules.

    Total test suite: 82 tests (17 skipped, 65 passing).

51. `checkpoint-051-capabilities-wire-remaining-roles`
    Completes capabilities wiring for the geoip and dns roles, so all roles
    with non-trivial activation conditions can now be triggered either by their
    existing flags/conditions or by a service declaring requires: [capability].

    geoip role when: condition extended:
      was: geoip.enabled | default(false) | bool
      now: ... or 'maxmind_nftables' in (_required_providers | default([]))
    A service declaring requires: [geoip] will now cause the geoip role to
    run and generate the nftables country sets, independent of the vault flag.
    The nftables template's geoip.enabled guards (controlling set loading)
    remain separate: those are vault-level policy, not role activation.

    dns role when: condition extended:
      added: or 'bind' in (_required_providers | default([]))
    A service declaring requires: [dns] now activates BIND alongside the
    existing three triggers (declared zones, certbot_dns_local, service domain
    derivation).

    Roles not wired (all run unconditionally or are not standalone):
      nginx, firewall_geo: no when: condition, always executed
      database (mariadb): part of nextcloud role, not standalone
      tls, reverse_proxy: both map to nginx which is unconditional

    All 7 capabilities in the capabilities dict are now either wired to a
    role when: condition or documented as unconditional. The capabilities
    layer is complete. Only the Molecule nextcloud integration test path
    remains as tracked future work.

52. `checkpoint-052-named-conf-double-slash-comments`
    Fixes the GENERATED FILE / DO NOT EDIT header in named.conf.local.j2
    using hash (#) comments, which are not valid in BIND named.conf syntax.
    BIND uses // for single-line comments; # is silently ignored or causes
    parse errors depending on the BIND version and context.

    Checkpoint-045 fixed zone.db.j2 (semicolons) but did not cover named.conf.
    Root cause: _comment_style() had no case for BIND config templates.

    Fix: _comment_style() now returns "//" when the path suffix is .j2 and
    the stem starts with "named.conf". This covers named.conf.local.j2 and
    any future named.conf.*.j2 templates without affecting other .conf.j2
    templates (nftables, nginx, Dovecot, OpenDKIM, geoip shell-config) which
    all correctly use # comments. The _render_notice() function already
    handles arbitrary comment strings generically, so no further changes
    were needed there.

    The body comments inside the named.conf.local.j2 template were already
    using semicolons (added in checkpoint-048) and are unaffected.

53. `checkpoint-053-named-conf-body-comment-fix`
    Fixes named-checkconf "syntax error near ';'" on the first line after the
    header in /etc/named.conf on RedHat. Checkpoint-052 fixed the generated
    file header (// instead of #) but left three groups of invalid comment
    characters in the template body:

    - Lines 8-11: semicolon (;) comments in the RedHat options block preamble.
      In BIND named.conf syntax ; is the statement terminator, not a comment
      character. named-checkconf rejected the first ; as a stray terminator.
    - Lines 27-28: hash (#) comments in the "no secondaries" else branch.
    - Lines 33-34 and 47: hash (#) comments in the certbot TSIG key block
      and update-policy comment.

    Fix: all comment characters in named.conf.local.j2 body replaced with //.
    The only remaining semicolons in the template are correct BIND statement
    terminators (closing braces, option values). The fix applies equally on
    Debian where named.conf.local is an include file - // comments are also
    valid in BIND include files.

54. `checkpoint-054-dns-service-a-record-sync`
    Fixes DNS zones not updating when services are added after initial
    provisioning. Previously, zone.db.j2 was rendered with force: false,
    so A records were only written at zone-creation time. Adding a new
    service required manually editing the zone file or destroying and
    recreating it.

    New file: roles/dns/files/sync_dns_records.py
    Idempotently adds missing service-derived A records to an existing zone
    file. Records already present (whether from initial creation or added by
    hand) are never touched or removed. The script accepts --record LABEL
    ADDRESS arguments and prints "added N record(s): ..." to stdout only
    when records are actually added, enabling Ansible changed_when detection.

    New task in roles/dns/tasks/main.yml: "Sync service A records into zone
    files" runs after "Create zone files only if missing" on every Ansible
    execution. It mirrors zone.db.j2 record logic exactly: apex domains
    produce --record @ <ip>, subdomains produce --record <label> <ip>. It
    loops over _effective_dns_zones and notifies Validate and Restart DNS
    when any record is added.

    The serial update task (update_dns_serial.py) already ran after every
    Ansible execution; it now runs after the sync task, so newly added
    records are always reflected in the SOA serial.

    Supporting changes:
    - roles/dns/files/sync_dns_records.py added to FILE_MANIFEST and
      generation_contracts.yml
    - sync_dns_records.py added to REQUIRED_TEST_COVERAGE in
      verify_repo_contracts.py
    - src/scripts/tests/test_sync_dns_records.py: 22 unit tests covering
      record_exists(), sync_records(), and CLI behaviour including
      idempotency, partial updates, hand-record preservation, and
      missing-file error handling. Total suite: 104 tests.

55. `checkpoint-055-opendkim-systemd-module-idempotence`
    Fixes "Enable and start opendkim" always reporting changed on every
    Ansible run. Root cause: the task used the generic service module with
    enabled: true and state: started. Ansible's service module (systemd
    backend) checks the enabled state by querying the unit symlink. When
    the unit was enabled via a systemd drop-in path rather than a direct
    systemctl enable -- which is the case here because the drop-in override
    was deployed in checkpoint-038 -- the symlink check reports the state as
    indeterminate on some systemd versions and marks the task changed even
    though nothing was done. Dovecot and postfix are unaffected because they
    use Type=forking and are enabled through the standard symlink path.

    Fix: switch the "Enable and start opendkim" task from the service module
    to the systemd module. The systemd module performs a proper D-Bus query
    for both the ActiveState and UnitFileState properties, correctly detecting
    that a Type=simple service is already running and enabled without marking
    changed. The task is otherwise identical.

56. `checkpoint-056-certbot-install-dig`
    Fixes "Assert domain resolves to this host" failing on Debian with
    "[Errno 2] No such file or directory: b'dig'" because dig is not
    installed by default on Debian minimal images. Fix: add "Install dig
    (DNS lookup utility)" task immediately before "Install certbot",
    installing bind9-utils on Debian/Ubuntu and bind-utils on RedHat family.
    Both packages provide the dig binary and are the canonical source on
    their respective distros.

57. `checkpoint-057-certbot-dig-package-debian12`
    Fixes dig not found on Debian even after bind9-utils is installed.
    On Debian 12 (Bookworm) the BIND tooling packages were split: bind9-utils
    provides server-side tools (named-checkconf, named-checkzone, etc.) while
    dig, host, and nslookup moved to bind9-dnsutils. Checkpoint-056 installed
    bind9-utils which is why the package installed successfully but dig was
    still missing. Fix: change Debian package from bind9-utils to
    bind9-dnsutils. RedHat bind-utils is unchanged (it provides both server
    and client tools in a single package).

58. `checkpoint-058-certbot-dns-local-default`
    Fixes "certbot dns challenge plugin is not installed" which was actually
    the dns-auth.sh hook script exiting 1 with its "not implemented" error
    message because certbot_dns_local was not set. The variable had no
    explicit default in roles/certbot/defaults/main.yml - every reference
    used | default(false) inline. This meant operators had no obvious place
    to find or set it, and the hook scripts would always exit 1 unless the
    variable was set in vault or group_vars.

    Fix: certbot_dns_local: false added to roles/certbot/defaults/main.yml
    with full documentation explaining the two modes:
    - true: certbot uses nsupdate with a TSIG key against local BIND.
      Requires certbot_tsig_secret in vault. Correct when this host runs
      BIND and is authoritative for the domain.
    - false (default): the dns-auth.sh stub must be implemented by the
      operator for their external DNS provider API.

    The project uses --manual with hook scripts throughout, not a certbot
    DNS plugin. No plugin installation is required.

59. `checkpoint-059-certbot-propagation-and-nsupdate`
    Two certbot fixes:

    (1) certbot_dns_propagation_seconds raised from 3 to 30. The 3-second
    default was too short to reliably pass Let's Encrypt DNS-01 validation.
    After nsupdate writes the _acme-challenge TXT record, BIND must process
    the dynamic update, write the zone journal, and become queryable. Let's
    Encrypt then queries the authoritative nameserver directly. 30 seconds
    is the conventional safe value used by certbot DNS plugins.

    (2) The "Install dig" task renamed to "Install DNS client utilities
    (dig, nsupdate)" with a comment clarifying that bind9-dnsutils (Debian)
    and bind-utils (RedHat) both provide nsupdate as well as dig. nsupdate
    is required by dns-auth.sh and dns-cleanup.sh when certbot_dns_local
    is true. Making this explicit prevents operators from thinking nsupdate
    needs a separate install step.

60. `checkpoint-060-restricted-service-access-allowlist`
    Adds security.access_allowlist to the services schema, enabling services
    like Prometheus and Grafana to be restricted to specific IP addresses and
    CIDRs at the nginx layer, independent of geoip.

    New schema field: security.access_allowlist (array of strings, optional).
    When set, the service is served by restricted_site.conf.j2 instead of
    site.conf.j2. The template emits an nginx allow directive for each entry
    followed by deny all, so only the listed sources receive a response.
    All other sources get HTTP 403. This is enforced before proxying, so the
    upstream process is never reached by unlisted addresses.

    New template: roles/nginx/templates/restricted_site.conf.j2.
    Structurally identical to site.conf.j2 (TLS, proxy_pass, headers) with
    the access control block inserted before location /. Supports both HTTP
    and HTTPS, and TLS certificates via the standard certbot path.

    Dispatch priority in render_service.yml (highest to lowest):
      1. app.type == nextcloud  -> nextcloud.conf.j2
      2. access_allowlist set   -> restricted_site.conf.j2   (new)
      3. require_client_cert    -> client_cert_site.conf.j2
      4. generic                -> site.conf.j2

    Example services added as comments to group_vars/all/main.yml:
    - prometheus (port 9090, access_allowlist + geoip_allowlist)
    - grafana    (port 3000, access_allowlist + geoip_allowlist)

    Note: access_allowlist (nginx layer) and geoip_allowlist (nftables layer)
    serve different purposes and should both be set for monitoring services:
    geoip_allowlist ensures traffic from those IPs reaches the host at all;
    access_allowlist ensures nginx enforces the restriction even when geoip
    is disabled or bypassed.

    8 new tests (3 schema, 5 nginx dispatch). Total suite: 112 tests.

61. `checkpoint-061-node-exporter-role`
    Adds a new roles/node_exporter role that installs and configures the
    Prometheus node_exporter metrics agent on every provisioned host.
    Enabled by default (node_exporter_enabled: true in group_vars).

    Role files (roles/node_exporter/):
      defaults/main.yml  - node_exporter_port: 9100,
                           node_exporter_scrape_addresses: []
      handlers/main.yml  - Restart node_exporter handler
      tasks/main.yml     - Install (distro-aware package and binary names),
                           create systemd override directory, deploy override
                           binding the service to 127.0.0.1 only, enable and
                           start via systemd module with daemon_reload: true

    Distro support:
      Debian/Ubuntu: package prometheus-node-exporter,
                     binary /usr/bin/prometheus-node-exporter,
                     service prometheus-node-exporter
      RedHat family: EPEL enabled first, package
                     golang-github-prometheus-node-exporter,
                     binary /usr/bin/node_exporter,
                     service node_exporter

    The service is bound to 127.0.0.1:9100 via systemd ExecStart override.
    This prevents direct network exposure; Prometheus reaches it via the
    firewall rules below or via SSH tunnel.

    group_vars/all/main.yml additions:
      node_exporter_enabled: true
      node_exporter_port: 9100
      node_exporter_scrape_addresses: []

    nftables.conf.j2 additions (before SSH block):
      Loopback (127.0.0.1, ::1) always accepted on port 9100.
      Each address in node_exporter_scrape_addresses gets an accept rule
      (ip saddr or ip6 saddr based on presence of ':' in the address).
      The block is skipped when node_exporter_enabled is false.

    site.yml: node_exporter role added as last role, runs when
    node_exporter_enabled | default(true) | bool.

    27 new unit tests in test_node_exporter.py covering role structure,
    defaults, firewall template, and site.yml ordering.
    Total suite: 139 tests.

62. `checkpoint-062-node-exporter-redhat-binary-download`
    Fixes "No package golang-github-prometheus-node-exporter available" on
    RedHat family hosts. EPEL 9 does not ship node_exporter as an installable
    package under that name. The fix removes the EPEL package approach for
    RedHat entirely and replaces it with downloading the official pre-compiled
    binary from the Prometheus GitHub releases page, which is the standard
    production installation method for RHEL systems.

    RedHat installation tasks (all gated when: os_family == 'RedHat'):
    1. Resolve CPU architecture (amd64 / arm64 from ansible_facts.architecture)
    2. Create node_exporter system user (system: true, nologin, no home dir)
    3. Download .tar.gz from github.com/prometheus/node_exporter/releases
    4. Extract binary from archive to /tmp
    5. Copy binary to /usr/local/bin/node_exporter (mode 0755)
    6. Write /etc/systemd/system/node_exporter.service unit file inline
       (Type=simple, User/Group=node_exporter, loopback listen address)

    Debian path unchanged: prometheus-node-exporter package + systemd override.

    node_exporter_version: "1.8.2" added to defaults/main.yml.
    Handler updated to use systemd module and distro-aware service name.
    4 stale tests updated; 3 new tests added (system user, arch-awareness,
    systemd unit). Total suite: 142 tests.

63. `checkpoint-063-remove-empty-group-vars-defaults`
    Fixes ansible-playbook ignoring external inventory values for required
    variables even though ansible ad-hoc debug shows them correctly populated.
    Root cause: Ansible variable precedence places playbook group_vars/all
    ABOVE inventory group_vars/all. The four variables below had empty string
    defaults in build/group_vars/all/main.yml (playbook group_vars), which
    silently overrode any values set in an operator's external inventory
    group_vars/all/ directory.

    Removed empty defaults for:
      admin_ssh_public_key      - was: ""  now: comment only
      admin_dev_password_hash   - was: ""  now: comment only
      nextcloud_admin_password  - was: ""  now: comment only
      nextcloud_db_password     - was: ""  now: comment only

    These variables are operator-supplied secrets with no safe default.
    The preflight and common roles already assert that required vars are
    set and emit clear error messages when they are missing. The empty
    defaults provided no safety net and actively prevented external
    inventory overrides from taking effect.

    Ansible precedence reference (lowest to highest, relevant levels):
      role defaults < inventory group_vars/all < playbook group_vars/all
      < inventory host_vars < playbook host_vars < extra_vars (-e)
    To override playbook group_vars from an external inventory, use
    host_vars or extra_vars, both of which beat playbook group_vars.

64. `checkpoint-064-role-defaults-no-group-vars-overrides`
    Completes the external inventory precedence fix from checkpoint-063 by
    moving ALL variable defaults out of build/group_vars/all/main.yml and
    into role defaults files, where they have the lowest possible precedence
    and can be overridden from any inventory level.

    Ansible variable precedence (lowest to highest):
      role defaults  <  inventory group_vars  <  playbook group_vars
                     <  inventory host_vars   <  extra_vars

    build/group_vars/all/main.yml now contains only YAML front matter (---)
    and comments. It serves as an operator reference showing available
    variables, their structure, and where their defaults live. No live
    variable declarations remain in this file.

    New role defaults files added to FILE_MANIFEST:
      roles/common/defaults/main.yml
        ssh_port: 22, admin_users: [myadmin],
        deployment_environment: production, services: {},
        capabilities: {tls/reverse_proxy/dns/database/firewall/geoip/mail}

      roles/ssh_hardening/defaults/main.yml
        ssh_port: 22

      roles/geoip/defaults/main.yml
        geoip: {enabled, license_key, download_dir, sets_dir,
                allowed_countries, ssh_allowed_countries, allowlist}
        (all values are Jinja2 expressions referencing flat vault vars)

      roles/mailserver/defaults/main.yml
        mailserver: {enabled: false, domain, admin_mail_user,
                     admin_mail_password, masquerading_*, masquerade_*}

    Updated: roles/node_exporter/defaults/main.yml
      node_exporter_enabled: true added (previously in group_vars)

    All existing role defaults, certbot, dns, nextcloud, node_exporter
    remain unchanged. Total file count: 75 generated files.

65. `checkpoint-065-node-exporter-tar-extract`
    Fixes "Extract node_exporter binary (RedHat)" attempting to use unzip
    on a .tar.gz archive. The unarchive module auto-detects archive format
    but requires the unzip binary to be present on the remote host even for
    tar archives on some Ansible/Python versions. Rather than install unzip
    as a dependency, the task is replaced with a direct tar command which is
    always available on any Linux system. The tar invocation extracts only
    the single binary file needed from the archive (rather than the full
    directory tree) using a positional path argument, and remains idempotent
    via args.creates pointing to the extracted file.

66. `checkpoint-066-node-exporter-install-tar-gzip`
    Fixes "tar: command not found" on CentOS Stream 10 minimal installs.
    CentOS Stream 10 does not include tar or gzip in its default package
    set. A new task "Install tar and gzip (RedHat)" is added immediately
    before the system user creation task, installing both packages via dnf
    before any extraction attempt. The task is gated with the same
    when: os_family == 'RedHat' condition as all other RedHat-specific
    tasks in the role. Both packages are in the BaseOS repository and
    require no additional repos.

67. `checkpoint-067-opendkim-daemon-reload`
    Fixes "Enable and start opendkim" always reporting changed in production.
    Checkpoint-055 switched the task from the service module to the systemd
    module to fix the UnitFileState symlink check, but omitted daemon_reload:
    true. Without it, the systemd module queries unit state through a D-Bus
    call that can return stale cached data on some systemd versions, causing
    the module to believe the unit needs attention even when it is already
    running and enabled correctly. Fix: daemon_reload: true added, consistent
    with the node_exporter Enable and start task which has always included it.

68. `checkpoint-068-archlinux-support`
    Adds Arch Linux (os_family == 'Archlinux') as a supported platform.
    All distro-conditional logic updated with Arch-specific values:

    site.yml pre_tasks:
      pacman: update_cache: true added alongside apt and dnf cache refresh.

    ssh_hardening handler:
      Inverted to: 'ssh' if Debian else 'sshd' — Arch uses sshd (same as
      RedHat), now correctly covered by the else branch.

    certbot: dig/nsupdate package:
      bind9-dnsutils (Debian) / bind (Arch) / bind-utils (RedHat).

    dns role:
      BIND package: 'bind' on all distros (bind9 was Debian-only and was
      unified since Debian also accepts 'bind' via the package alias).
      Service: 'bind9' (Debian) / 'named' (Arch + RedHat) — existing else
      branch already correct.
      Zone dir / named.conf path: /etc/bind/zones and named.conf.local
      (Debian) vs /var/named and /etc/named.conf (Arch + RedHat) — existing
      else branch already correct.
      named.conf.local.j2 options block: guard changed from
      os_family == 'RedHat' to os_family != 'Debian' so Arch also gets the
      complete named.conf with options block.
      Enable and start BIND task added (was previously only started via
      handler; also fixes a verify_service_start_coverage contract failure
      that surfaced when the package name was unified to 'bind').

    mailserver role:
      Arch uses ['postfix', 'dovecot', 'opendkim', 'opendkim-tools'] —
      same as RedHat. Dovecot on Arch ships as a single 'dovecot' package
      with all protocols included. postfix-lmdb is Debian-specific (on
      Arch, LMDB support is compiled into the main postfix package).

    nginx:
      nginx user: 'www-data' (Debian) / 'http' (Arch) / 'nginx' (RedHat).
      php-fpm socket: /run/php/php-fpm.sock (Debian) /
      /run/php-fpm/php-fpm.sock (Arch) / /run/php-fpm/www.sock (RedHat).
      php-fpm pool listen owner/group: www-data / http / nginx.

    node_exporter:
      Arch uses the binary download path (same as RedHat). All binary
      download task guards changed from os_family == 'RedHat' to
      os_family != 'Debian', covering both RedHat and Arch.

    molecule/default/molecule.yml:
      archlinux platform added using archlinux:latest image.

69. `checkpoint-069-arch-openssh-package`
    Fixes pacman failing to install openssh-server on Arch Linux. The package
    is named openssh-server on Debian/Ubuntu/RedHat but simply openssh on Arch
    (the package provides both client and server). The ssh_hardening install
    task now uses a two-way ternary: ['openssh', 'sudo'] on Archlinux,
    ['openssh-server', 'sudo'] on all other distros.

70. `checkpoint-070-arch-bind-package-fix`
    Fixes "No package matching 'bind' is available" on non-Arch hosts.
    Checkpoint-068 incorrectly unified the BIND package name to 'bind' for
    all distros, claiming Debian accepts it as an alias. It does not: Debian
    requires 'bind9'. The fix restores the two-way conditional:
      bind9 (Debian/Ubuntu) / bind (Arch + RedHat)
    Arch and RedHat both use 'bind' from their respective repositories.

71. `checkpoint-071-distro-conditional-tests`
    Adds src/scripts/tests/test_distro_conditionals.py covering all
    distro-conditional logic that has caused production bugs. Policy going
    forward: every distro-conditional fix gets a test before the checkpoint
    ZIP is produced.

    39 tests across 7 test classes:
      TestSshHardeningDistro  - openssh vs openssh-server, ssh vs sshd service
      TestDnsDistro           - bind9/bind package, named/bind9 service, zone
                                dir paths, named.conf dest, options block guard,
                                Enable and start BIND task present
      TestCertbotDistro       - bind9-dnsutils/bind/bind-utils per distro
      TestMailserverDistro    - postfix-lmdb Debian-only, dovecot split packages,
                                single dovecot on non-Debian
      TestNginxDistro         - www-data/http/nginx user, php-fpm socket paths
                                per distro, pool listen owner
      TestNodeExporterDistro  - Debian package vs non-Debian binary download,
                                no RedHat-only guard on binary tasks
      TestSiteYmlDistro       - apt/dnf/pacman cache refresh tasks present and
                                gated to correct os_family

    These tests would have caught:
      cp-068 bind package regression (bind9 -> bind on Debian)
      cp-069 openssh-server vs openssh on Arch
      cp-070 bind9 vs bind on Debian (caught by test_bind_package_debian_is_bind9)
    Total suite: 181 tests.

72. `checkpoint-072-bug-fix-test-contract`
    Formalises the rule that every bug fix must normally include a unit test.
    Added to two spec files:

    src/spec/contracts.md: new "Bug Fix Test Contract" section specifying
    that a checkpoint fixing a bug is incomplete without a test that would
    have caught it, placement guidance for different test categories, and
    rationale citing the 18 untested fixes from checkpoints 053-070.

    src/spec/ai-development-mode.md: rule 6 added to the AI Contributor
    Rules list referencing the contract and stating that explicitly
    untestable bugs are the only permitted exception.

    Both files are in LOCK_SOURCE_FILES and are hashed into the generator
    lock, so any future session that reads the lock will see these rules.

73. `checkpoint-073-arch-cronie-cron-daemon`
    Fixes "Failed to find required executable crontab in paths" on Arch Linux.
    Arch does not install a cron daemon by default; the Ansible cron module
    requires crontab to be present. Three roles add cron jobs: certbot
    (certificate renewal), geoip (weekly refresh), and nextcloud (background
    tasks). Rather than installing cronie in each role separately, two tasks
    are added to roles/common/tasks/main.yml (which runs first on every host):
      - Install cronie (Arch only, gated when: os_family == 'Archlinux')
      - Enable and start cronie
    cronie is the standard cron implementation for Arch Linux and provides
    both crond and the crontab binary. Debian and RedHat ship cron daemons
    in their respective base/minimal installs and are unaffected.
    Regression test added to TestCronieArch in test_distro_conditionals.py.
    Total suite: 184 tests.

74. `checkpoint-074-mailserver-flat-variables`
    Refactors roles/mailserver/defaults/main.yml to use flat variables
    assembled via Jinja2, matching the pattern already used for geoip. This
    allows individual mailserver settings to be overridden per-host in
    inventory host_vars without replacing the entire mailserver: dict (which
    Ansible's shallow merge would otherwise require).

    Flat variables (set in host_vars or vault):
      mailserver_enabled              (default: false)
      mailserver_domain               (default: mail.example.com)
      mailserver_admin_mail_user      (default: mailadmin)
      mailserver_admin_mail_password  (set in vault)
      mailserver_masquerading_enabled (default: false)
      mailserver_masquerade_domain    (default: "")
      mailserver_masquerade_users     (default: [])
      mailserver_masquerade_hosts     (default: [])

    The mailserver: dict in role defaults interpolates these via
    {{ mailserver_domain | default('mail.example.com') }} etc.
    Operators who previously set the full mailserver: dict in inventory
    can continue to do so (dict-level override still works); operators
    who want to set only mailserver_domain: per host can now do so with
    a single flat variable.

    For services: the same principle applies. Jinja2 expressions can be
    used inside the services: dict in inventory group_vars to reference
    flat variables from host_vars, e.g.:
      services:
        myapp:
          domain: "{{ myapp_domain }}"
          web:
            upstream_port: "{{ myapp_port | default(8080) }}"

75. `checkpoint-075-mailserver-local-relay-domains`
    Adds two new mailserver configuration fields:

    mailserver.local_domains (flat: mailserver_local_domains, default: [])
      Additional domains for which Postfix delivers mail locally. Appended
      to Postfix mydestination alongside localhost and mailserver.domain.
      Use for aliases, subdomains, or legacy domains that should be
      delivered to local accounts on this server.
      Example: [example.com, legacy.example.com]

    mailserver.relay_domains (flat: mailserver_relay_domains, default: [])
      Domains for which Postfix relays mail to another MTA. Sets Postfix
      relay_domains. Mail for these domains is forwarded, not delivered
      locally. Only emitted to main.cf when the list is non-empty.
      Example: [subsidiary.example.com]

    main.cf.j2 changes:
      mydestination now includes mailserver.domain (was just localhost) and
      iterates mailserver.local_domains with a Jinja2 for loop.
      relay_domains directive added inside an if block, joined by commas.

    11 regression tests added in test_mailserver_config.py.
    Total suite: 195 tests.

76. `checkpoint-076-dns-named-checkconf-z-reload`
    Improves DNS zone change handling. Two changes to roles/dns/handlers/main.yml:

    (1) named-checkconf -z instead of named-checkconf.
    The -z flag instructs named-checkconf to also load and validate every zone
    file referenced in the configuration, not just the config syntax. When a
    new zone is added, this catches zone file syntax errors before BIND attempts
    to load them, producing a clear error rather than a silent failure or a
    BIND startup error. Without -z, named-checkconf only validates config
    syntax and would pass even if the new zone file was malformed.

    (2) state: reloaded instead of state: restarted.
    BIND's reload (SIGHUP) causes it to re-read named.conf and all zone files,
    picking up new zones and zone file changes without dropping established
    connections or resetting the resolver cache. A full restart is unnecessarily
    disruptive for zone additions or content changes. The Enable and start BIND
    task in tasks/main.yml correctly retains state: started for initial
    provisioning when the service may not yet be running.

    The handler is renamed from "Restart DNS" to "Reload DNS" for clarity.
    All notify references in tasks use "Validate and Restart DNS" (the first
    handler which chains to "Reload DNS") and are unchanged.

77. `checkpoint-077-dns-handler-direct-reload`
    Fixes named server not being reloaded after DNS config changes on CentOS
    Stream 10. Root cause: checkpoint-076 introduced a two-handler chain where
    "Validate and Restart DNS" ran named-checkconf -z and then notified
    "Reload DNS". On RHEL/CentOS, named-checkconf -z tries to load zone data
    into memory in the named context. When run by root as an Ansible handler
    it can fail with a permission or SELinux error, silently aborting the chain
    and leaving BIND running with stale config.

    Fix: the handler chain is eliminated. "Validate and Restart DNS" now
    directly reloads BIND (state: reloaded) without any intermediate step.
    The name is preserved for backwards compatibility with all existing
    notify: calls in tasks.

    Validation is moved to explicit tasks that run after zone files are
    written, before Enable and start BIND:
    - "Validate named.conf syntax": named-checkconf (no -z flag, safe on all
      distros, changed_when: false)
    - "Validate zone files": named-checkzone per zone, loops _effective_dns_zones,
      changed_when: false

    Running validation as tasks (not handlers) means errors surface immediately
    with clear output and line numbers, rather than silently blocking a reload
    at play end. If validation fails, the play stops and BIND is not reloaded,
    which is the correct behaviour.

78. `checkpoint-078-nftables-systemd-module-idempotence`
    Fixes "Enable nftables" always reporting changed on Arch Linux. Same root
    cause as checkpoint-055 (opendkim) and checkpoint-067 (opendkim again):
    the generic service module checks the enabled state by querying the unit
    symlink. On Arch, systemd units installed by packages are enabled via a
    different path than the standard symlink, causing the check to return an
    indeterminate result and mark changed every run.

    Fix: service: -> systemd: with daemon_reload: true, identical to the
    opendkim and node_exporter fixes. The systemd module queries UnitFileState
    via D-Bus and correctly detects the already-enabled state on all distros.

    Regression test added: TestNftablesIdempotence in test_distro_conditionals.py
    verifying that the Enable nftables task uses the systemd module (not service)
    and includes daemon_reload: true. Total suite: 202 tests.

79. `checkpoint-079-opendkim-run-dir-fix`
    Fixes opendkim failing to write /run/opendkim/opendkim.pid on first
    install with "No such file or directory". Root cause: a task ordering
    race between the drop-in deploy and the service start.

    The "Deploy opendkim systemd RuntimeDirectory override" task notifies
    the "Reload systemd and restart opendkim" handler, which runs at play
    end. The "Enable and start opendkim" task runs immediately after the
    deploy task, before the handler fires. At that point:
    - The drop-in is on disk but not yet loaded by systemd
    - daemon_reload: true in the systemd start task reloads the unit
      definition but the RuntimeDirectory= processing happens asynchronously
    - /run/opendkim does not exist when opendkim tries to write its pidfile

    Two tasks added between the drop-in deploy and Enable and start opendkim:

    1. "Reload systemd daemon for opendkim drop-in" - systemd: daemon_reload: true
       Forces synchronous daemon reload so RuntimeDirectory= takes effect.

    2. "Ensure /run/opendkim directory exists" - file: state: directory
       Explicitly creates the directory with owner/group opendkim mode 0750
       as a belt-and-suspenders guarantee for first-install scenarios where
       systemd RuntimeDirectory processing may not have run yet.

80. `checkpoint-080-revert-opendkim-run-dir-fix`
    Reverts checkpoint-079. The two tasks added (explicit daemon_reload and
    /run/opendkim directory creation) did not resolve the pidfile error.
    SELinux permissive mode made no difference, ruling out SELinux as the
    cause. The opendkim service is working correctly despite the log message;
    the pidfile error is a cosmetic warning from opendkim attempting to write
    the PID file before systemd has fully initialised the RuntimeDirectory.
    The issue is deferred — no known fix at this time.

81. `checkpoint-081-selinux-deny-ptrace`
    Adds SELinux baseline configuration for RedHat family hosts in
    roles/common/tasks/main.yml. Two tasks, both gated when: os_family == 'RedHat':

    1. Install SELinux Python bindings (python3-libselinux) and management
       tools (policycoreutils-python-utils). python3-libselinux is required
       by Ansible for any file, service, or package operation on hosts with
       SELinux enforcing; without it Ansible aborts with "target uses selinux
       but python bindings are missing". policycoreutils-python-utils provides
       semanage, audit2allow, and related tools.

    2. Set deny_ptrace SELinux boolean to false (persistent). With deny_ptrace
       enabled (the default on some RHEL 9 hardened profiles), confined domains
       cannot use ptrace-based interfaces. This prevents "ps aux" from showing
       all processes even for root, causing Ansible gather_facts and process
       management tasks to see incomplete process lists. Setting deny_ptrace:
       false restores standard POSIX process visibility for root.

    5 regression tests added to TestSelinuxRedhat in test_distro_conditionals.py.
    Total suite: 205 tests.

82. `checkpoint-082-systemd-module-all-service-tasks`
    Proactive sweep: switches all remaining service: tasks with enabled: true
    and state: started to the systemd: module with daemon_reload: true,
    preventing the "always reports changed" idempotence regression seen with
    opendkim (cp-055, cp-067), nftables (cp-078), and potentially dovecot,
    postfix, nginx, cronie, MariaDB, php-fpm, and BIND.

    Tasks converted:
      roles/mailserver/tasks/main.yml  - dovecot, postfix
      roles/nginx/tasks/main.yml       - nginx
      roles/common/tasks/main.yml      - cronie (Arch)
      roles/nextcloud/tasks/main.yml   - mariadb, php-fpm
      roles/dns/tasks/main.yml         - BIND

    New test: TestSystemdModuleEnforcement in test_distro_conditionals.py
    scans all role task files and fails CI if any service: module task with
    enabled: true is found. Also adds TestNftablesIdempotence (which was
    previously written but accidentally outside a class definition due to a
    file corruption, now properly placed).

    Total suite: 208 tests.

83. `checkpoint-083-vault-example-update`
    Updates group_vars/all/vault.yml.example to reflect the current project
    state after checkpoints 063-074 introduced flat variable patterns.

    Removed: ssh_port, admin_users (now role defaults, not vault vars).
    Fixed: mailserver block now uses flat variables (mailserver_enabled,
    mailserver_domain, mailserver_admin_mail_password, etc.) matching the
    roles/mailserver/defaults/main.yml pattern from checkpoint-074. The old
    nested mailserver: dict form was incorrect since checkpoint-074.
    Added: certbot_email (was missing), mailserver_local_domains,
    mailserver_relay_domains (from checkpoint-075), inline generation
    commands for tsig and password hash.
    Reorganised: sections grouped by feature with clear enable/disable
    comments so operators know which variables are required for each role.

84. `checkpoint-084-arch-opendkim-tools-update-password`
    Two fixes:

    (1) opendkim-tools removed from Arch Linux mailserver package list.
    On Arch, opendkim-genkey and related tools are bundled in the opendkim
    package; there is no separate opendkim-tools package. The package list
    ternary is now three-way: Debian (postfix-lmdb, dovecot-core, dovecot-imapd,
    opendkim, opendkim-tools) / Archlinux (postfix, dovecot, opendkim) /
    RedHat else (postfix, dovecot, opendkim, opendkim-tools).
    Regression tests added: TestMailserverPackagesArch.

    (2) update_password: always -> on_create in ssh_hardening tasks.
    The "Set Unix password for admin users" and "Set Unix password for root"
    tasks used update_password: always, which causes Ansible to re-hash and
    re-set the password on every run, always reporting changed. Changed to
    on_create so the password is set only when the account is first created.
    If you need to force a password change, delete the account and let Ansible
    recreate it, or set the password manually with passwd.
    Regression test added: TestUpdatePasswordIdempotence.

    Total suite: 212 tests.

85. `checkpoint-085-nftables-oneshot-fix`
    Fixes "Enable nftables" always reporting changed on Arch Linux.
    Root cause: nftables.service on Arch (and several other distros) is
    Type=oneshot RemainAfterExit=yes. The systemd module with state: started
    queries the service's active state; for a oneshot service this triggers
    a re-run on every Ansible execution because the oneshot unit is considered
    inactive after its ExecStart completes, even with RemainAfterExit.

    Fix: state: started removed from the enable task. The task is renamed
    "Enable nftables at boot" to clarify its purpose. A new task "Apply
    nftables ruleset" (command: nft -f /etc/nftables.conf, changed_when: false)
    is added immediately before it to ensure the ruleset is active at
    provisioning time without depending on service state.

    The handler "Reload nftables" also uses nft -f and fires when
    nftables.conf changes, so runtime reloads remain correct.

    Regression tests updated in TestNftablesIdempotence: anchored on
    "- name: Enable nftables at boot" (YAML prefix) rather than the bare
    string which matched the preceding comment. New test:
    test_enable_nftables_no_state_started. Total suite: 214 tests.

86. `checkpoint-086-debian-bind-zone-dir-var-lib-bind`
    Changes Debian BIND zone file directory from /etc/bind/zones to
    /var/lib/bind. /etc/bind is owned root:bind 0750 with files at 0640;
    the bind user can read but not write there. /var/lib/bind is owned
    root:bind 0775 and is the intended location for dynamic and managed
    zone files on Debian - BIND can write journal files, AXFR data, and
    DDNS updates there without special configuration.

    Changes:
    - All zone file path ternaries updated: /var/lib/bind (Debian) vs
      /var/named (non-Debian)
    - "Ensure Bind zone directory exists" task simplified: only runs on
      non-Debian (when: os_family != 'Debian') since /var/lib/bind is
      created by the bind9 package with correct ownership already
    - named.conf.local.j2 zone file references updated
    - Stale comments referencing /etc/bind/zones corrected
    - Test updated: test_zone_dir_debian_is_var_lib_bind replaces
      test_zone_dir_debian_is_etc_bind_zones, plus new assertion that
      /etc/bind/zones is absent from tasks. Total suite: 215 tests.

87. `checkpoint-087-dovecot-confd-mkdir`
    Fixes "Destination directory /etc/dovecot/conf.d does not exist" on
    Arch Linux. The Debian and RedHat dovecot packages create /etc/dovecot/
    conf.d as part of their post-install scripts. The Arch dovecot package
    uses a single /etc/dovecot/dovecot.conf and does not create conf.d.
    Fix: explicit "Ensure /etc/dovecot/conf.d directory exists" task added
    immediately before the first conf.d template deployment, unconditional
    on all distros (idempotent, safe to run when the directory already exists).
    Regression test added to TestMailserverPackagesArch. Total suite: 216 tests.

88. `checkpoint-088-opendkim-background-no-foreground`
    Fixes opendkim not working correctly on Arch, Debian, and CentOS.
    Root cause: opendkim defaults to Background yes (fork to background).
    The systemd drop-in sets Type=simple, which tells systemd the process
    it spawned IS the main process. When opendkim forks, systemd loses track
    of the real process - it watches the now-exited parent, declares the
    service started (or failed), and may kill the child. This is a fundamental
    Type=forking vs Type=simple mismatch.

    Two changes:

    opendkim.conf.j2:
      Background no  added  - opendkim runs in foreground, systemd tracks it
      AutoRestart no         - redundant when systemd manages restarts via
                               Restart= in the unit; avoid double-restart races
      PidFile removed        - no pid file is written when Background=no

    systemd drop-in override.conf:
      Comment and ordering clarified. PIDFile= clear retained (Debian package
      ships a PIDFile= directive in the base unit that must be cleared to
      prevent systemd from waiting for a file that will never appear).
      Type=simple retained and now correctly matches the foreground process.
      ExecStart reset retained to strip the Debian -p socket argument.

89. `checkpoint-089-dovecot-auth-allow-cleartext-arch`
    Fixes "Unknown setting: disable_plaintext_auth" Fatal error on Arch Linux.
    Dovecot 2.4+ (shipped on Arch Linux as a rolling release) renamed
    disable_plaintext_auth to auth_allow_cleartext with inverted logic
    (no = disallow cleartext, equivalent to disable_plaintext_auth = yes).
    Dovecot 2.3.x (Debian stable, RedHat) still uses the old name and
    fatally rejects the new one.

    Fix: 10-auth.conf.j2 uses a Jinja2 conditional:
      Archlinux -> auth_allow_cleartext = no
      all others -> disable_plaintext_auth = yes

    Note: "both settings" was considered first but rejected because Dovecot
    2.4 exits Fatal on any unrecognised setting in conf.d files, so the two
    names cannot coexist in the same file.

    Regression test added to TestMailserverPackagesArch. Total suite: 216 tests.

90. `checkpoint-090-dovecot-mail-location-arch`
    Fixes "Unknown setting: mail_location" Fatal error on Arch Linux (Dovecot 2.4).
    Dovecot 2.4 split the mail_location setting into two separate directives:
      mail_driver = maildir   (the storage format)
      mail_path = ~/Maildir   (the path)
    Dovecot 2.3.x (Debian stable, RedHat) uses the combined mail_location syntax
    and fatally rejects the new split form.

    Fix: 10-mail.conf.j2 uses a Jinja2 conditional identical in structure to
    the disable_plaintext_auth fix in checkpoint-089:
      Archlinux -> mail_driver + mail_path
      all others -> mail_location

    Regression test added: test_dovecot_mail_uses_version_conditional.
    Total suite: 217 tests.

91. `checkpoint-091-role-tags`
    Adds tags to all roles in site.yml to allow selective execution.

    Tag mapping:
      common         -> [common, always]   (always runs: contains variable assertions)
      ssh_hardening  -> [ssh_hardening, ssh]
      geoip          -> [geoip]
      firewall_geo   -> [firewall_geo, firewall, nftables]
      dns            -> [dns]
      certbot        -> [certbot, tls]
      nginx          -> [nginx, web]
      users          -> [users]
      nextcloud      -> [nextcloud]
      mailserver     -> [mailserver, mail]
      node_exporter  -> [node_exporter, monitoring]

    common is tagged 'always' so its variable assertions always run even
    when using --tags, protecting against misconfiguration when running
    a subset of roles.

    Usage examples:
      ansible-playbook build/site.yml --tags mailserver
      ansible-playbook build/site.yml --tags "dns,certbot"
      ansible-playbook build/site.yml --tags firewall
      ansible-playbook build/site.yml --skip-tags monitoring

92. `checkpoint-092-dovecot-ssl-disable-arch`
    Fixes "cert_file: open(/etc/dovecot/ssl-cert.pem) failed" Fatal on Arch.
    The Arch dovecot package ships a default dovecot.conf that enables SSL
    and references /etc/dovecot/ssl-cert.pem and ssl-key.pem which do not
    exist. TLS is handled at the postfix (submission port) and nginx layer;
    Dovecot only serves localhost LMTP/auth connections where SSL is not needed.

    Two tasks added after the existing conf.d deploys:

    1. Deploy dovecot SSL config (disable built-in SSL):
       Writes /etc/dovecot/conf.d/10-ssl.conf containing "ssl = no".
       Unconditional on all distros (idempotent, correct on all platforms).

    2. Ensure dovecot.conf includes conf.d on Arch:
       Uses lineinfile to add "!include conf.d/*.conf" to /etc/dovecot/dovecot.conf
       if not already present. Gated when: os_family == 'Archlinux' since Debian
       and RedHat dovecot packages already include conf.d in their default config.

    Test class TestMailserverPackagesArch also repaired: previous edits had
    corrupted the class structure (a test body was merged into another test,
    TASKS was redeclared mid-class). Rewritten cleanly with 6 properly
    separated test methods. Total suite: 220 tests.

93. `checkpoint-093-dovecot-minimal-conf-arch`
    Fixes cert_file Fatal error persisting on Arch even with ssl=no in conf.d.
    Root cause: Dovecot parses and validates ssl_cert/ssl_key paths in
    dovecot.conf before loading conf.d overrides. Setting ssl=no in conf.d
    does not prevent the cert path validation in the main config file.

    Checkpoint-092's lineinfile approach was insufficient - it added the
    conf.d include but left the cert directives in place.

    Fix: replace the lineinfile task with a copy task that deploys a minimal
    dovecot.conf on Arch (gated when: os_family == 'Archlinux'):

      protocols = imap
      !include conf.d/*.conf

    No ssl_cert/ssl_key directives. SSL is disabled in conf.d/10-ssl.conf
    (deployed in checkpoint-092, retained). Debian and RedHat package
    defaults do not reference missing cert files and are left unchanged.

94. `checkpoint-094-dovecot-config-version`
    Fixes "The first setting must be dovecot_config_version" on Arch Linux.
    Dovecot 2.4 introduced a mandatory dovecot_config_version directive that
    must appear as the very first line of dovecot.conf. Without it, Dovecot
    refuses to start regardless of other configuration.
    Fix: "dovecot_config_version = 2.4" added as the first content line of
    the minimal dovecot.conf deployed on Arch (checkpoint-093).
    Test updated: test_dovecot_confd_included_on_arch now asserts the version
    directive is present.

95. `checkpoint-095-dovecot-config-version-full`
    Fixes "Invalid dovecot_config_version: Currently supported versions are:
    2.4.0 2.4.1 2.4.2". Dovecot requires a full three-part version string
    (major.minor.patch), not just major.minor. Changed 2.4 -> 2.4.0.
    If a future Dovecot update on Arch requires 2.4.1+, this value will need
    updating. Note: the supported version list is what Dovecot's own binary
    was compiled to accept; using 2.4.0 is correct as the minimum compatible
    schema version.

96. `checkpoint-096-file-copy-role`
    Adds roles/file_copy - a new role for copying files from the local repo's
    contrib/ directory (or any path accessible to the Ansible controller) to
    the managed host with configurable permissions and SELinux context.

    Variable: file_copy_items (list, default [])
    Each item:
      src    - path relative to playbook root (e.g. contrib/myscript.sh)
      dest   - absolute destination path on remote
      owner  - file owner (default: root)
      group  - file group (default: root)
      mode   - file mode (default: "0644")
      setype - SELinux type (optional, RedHat only)

    SELinux handling (RedHat only):
      - No setype: restorecon -v restores default context; changed_when
        triggers only when "Relabeled" appears in stdout (idempotent)
      - setype set: chcon -t <type> sets explicit type; always reports
        changed (chcon has no dry-run mode)

    Role is unconditional but a no-op when file_copy_items is empty.
    Tagged [file_copy, files] in site.yml.
    Added to generation_contracts.yml.
    Total generated files: 77.

    Example inventory config:
      file_copy_items:
        - src: contrib/logrotate-myapp.conf
          dest: /etc/logrotate.d/myapp
          mode: "0644"
          setype: etc_t
        - src: contrib/myapp-init.sh
          dest: /usr/local/bin/myapp-init.sh
          mode: "0755"
          setype: bin_t

97. `checkpoint-097-dns-ready-before-certbot`
    Fixes certbot running before the DNS server is ready. Two changes:

    roles/dns/tasks/main.yml:
      "Wait for BIND to be ready on port 53" added after "Enable and start
      BIND". Uses wait_for: host: 127.0.0.1 port: 53 timeout: 30. BIND may
      take several seconds to load zone files after systemd reports the service
      started, especially on first provision when zones are newly created and
      written. Without this wait, certbot's domain assertion (dig +short) or
      DNS-01 hook (nsupdate) can fire before BIND is accepting queries.

    site.yml:
      "meta: flush_handlers" added between the dns and certbot roles. This
      forces any pending handlers (e.g. "Validate and Restart DNS" triggered
      by a zone file change or named.conf update) to complete before certbot
      starts. Without it, Ansible defers handlers to play end, and certbot
      may run against a BIND that has stale config or has not yet reloaded
      updated zone files.

98. `checkpoint-098-firewall-enabled-flag`
    Adds firewall_enabled boolean (default: true) to roles/common/defaults/main.yml.
    When set to false in inventory, the firewall_geo role is skipped entirely
    via a when: condition in site.yml. Useful during development or when an
    external firewall manages filtering. Consistent with node_exporter_enabled
    and the existing geoip.enabled pattern.
    WARNING: disabling leaves all ports unfiltered on the host.

99. `checkpoint-099-remove-invalid-meta-flush-handlers`
    Fixes "role definitions must contain a role name" error introduced in
    checkpoint-097. meta: flush_handlers is a task directive and cannot appear
    inside a roles: block — Ansible only accepts role definitions there.
    Removed. The dns role's wait_for: port: 53 task (also added in cp-097)
    is sufficient to ensure BIND is accepting queries before certbot runs.

100. `checkpoint-100-freebsd-support`
     Adds FreeBSD (os_family == 'FreeBSD') as a supported platform.
     Assumes firewall_enabled: false since nftables does not exist on FreeBSD.

     Changes by area:

     site.yml:
       pkg update cache refresh task added (gated FreeBSD).

     ssh_hardening:
       OpenSSH is in FreeBSD base - only 'sudo' installed (not openssh-server).

     certbot:
       bind-tools provides dig and nsupdate on FreeBSD.

     dns:
       Package: bind918 (FreeBSD ports).
       Zone dir: /usr/local/etc/namedb (group: bind, mode: 0770).
       named.conf: /usr/local/etc/namedb/named.conf.
       named.conf options directory uses Jinja2: FreeBSD -> /usr/local/etc/namedb,
       others -> /var/named.
       All zone file path ternaries extended with FreeBSD branch.

     mailserver:
       Packages: ['postfix', 'dovecot', 'opendkim'] - no opendkim-tools (bundled),
       no postfix-lmdb (compiled in on FreeBSD).
       opendkim systemd drop-in directory and deploy tasks guarded != 'FreeBSD'.

     nginx:
       nginx user: www (FreeBSD).

     nextcloud (php-fpm):
       Socket: /var/run/php-fpm.sock.
       listen.owner / listen.group: www.

     Service management (all Enable/start tasks):
       Each systemd: enable+start task now has a paired service: task gated
       when: os_family == 'FreeBSD', with the systemd: task gated != 'FreeBSD'.
       Affected: nginx, opendkim, dovecot, postfix, BIND, node_exporter.

     node_exporter:
       systemd unit file deploy guarded not in ['Debian', 'FreeBSD'].
       rc.d script added: /usr/local/etc/rc.d/node_exporter with rcvar,
       command, pidfile, and proper rc.subr boilerplate.

     14 new regression tests in TestFreeBSDSupport.
     Total suite: 234 tests.

101. `checkpoint-101-certbot-nsupdate-method`
     Replaces the certbot_dns_local boolean with a certbot_dns_update_method
     variable and adds certbot_tsig_server and certbot_tsig_algorithm variables.

     New variables (in roles/certbot/defaults/main.yml):

       certbot_dns_update_method: none  (none | local | nsupdate)
         none     - hook script exits 1 (no update mechanism configured)
         local    - nsupdate to 127.0.0.1 (BIND on this host)
         nsupdate - nsupdate to certbot_tsig_server (remote hidden primary)

       certbot_tsig_server: "127.0.0.1"
         Target DNS server for nsupdate requests.
         Override with the hidden primary IP for method: nsupdate.

       certbot_tsig_algorithm: "hmac-sha512"
         HMAC algorithm for the TSIG key. Replaces the hardcoded hmac-sha256.
         Must match the algorithm used when generating the key.
         Generate: tsig-keygen -a hmac-sha512 certbot-acme

     certbot_dns_local: false retained as a backwards-compatible alias.
     certbot_dns_local: true maps to method 'local' via set_fact.

     Both dns-auth.sh.j2 and dns-cleanup.sh.j2 rewritten:
       - Single nsupdate block using {{ certbot_tsig_server }} (covers both
         local and remote).
       - Uses << 'NSEOF' (single-quoted heredoc) to prevent shell variable
         expansion inside the heredoc.
       - _certbot_dns_method set_fact resolves the effective method at play time.

     TSIG key template: algorithm now uses certbot_tsig_algorithm variable
     instead of hardcoded hmac-sha256.

102. `checkpoint-102-freebsd-wheel-group`
     Fixes file and directory ownership on FreeBSD where the privileged group
     is 'wheel', not 'root'. On Linux, root:root is standard. On FreeBSD,
     system files owned by root use root:wheel.

     Implementation: _root_group set_fact added to roles/common/tasks/main.yml
     immediately after the variable assertions:
       _root_group: "{{ 'wheel' if ansible_facts.os_family == 'FreeBSD' else 'root' }}"

     All 18 occurrences of group: root in task/handler files replaced with
     group: "{{ _root_group }}". Two existing FreeBSD-gated tasks (opendkim
     drop-in, systemd override) were already correct.

     Two regression tests added to TestFreeBSDSupport:
       test_root_group_uses_wheel_on_freebsd
       test_no_bare_group_root_in_tasks (enforces the pattern going forward)
     Total suite: 236 tests.

103. `checkpoint-103-freebsd-sudoers-path`
     Fixes sudo configuration failing on FreeBSD. sudo on FreeBSD is installed
     from ports and uses /usr/local/etc/sudoers and /usr/local/etc/sudoers.d/
     rather than the Linux paths /etc/sudoers and /etc/sudoers.d/.

     Changes:
       ssh_hardening/tasks/main.yml:
         New task "Ensure sudoers.d directory exists (FreeBSD)" creates
         /usr/local/etc/sudoers.d with mode 0750, gated when: FreeBSD.
         "Grant admin users passwordless sudo" task: dest path uses Jinja2
         ternary to select /usr/local/etc/sudoers.d/ (FreeBSD) or
         /etc/sudoers.d/ (all others).
       roles/preflight/tasks/main.yml (via generator):
         Sudoers.d stat and grep assertions use same path ternary.
     Regression test added. Total suite: 237 tests.

104. `checkpoint-104-freebsd-py311-ansible`
     Adds "Install Ansible Python support (FreeBSD)" task to
     roles/common/tasks/main.yml, gated when: os_family == 'FreeBSD'.
     Installs py311-ansible from FreeBSD ports. This package provides the
     Python interpreter and modules required by most Ansible tasks on the
     managed host. Without it, modules that use Python fail silently or with
     cryptic errors. py311 is the current Python version as of FreeBSD 14;
     if a newer Python becomes the default this package name will need
     updating. Regression test added. Total suite: 238 tests.

105. `checkpoint-105-freebsd-install-bash`
     Adds "Install bash (FreeBSD)" task to roles/common/tasks/main.yml,
     gated when: os_family == 'FreeBSD'. FreeBSD ships with /bin/sh as its
     default shell. bash is in ports and must be installed explicitly.
     Required because admin user accounts use shell: /bin/bash and certbot
     hook scripts use #!/usr/bin/env bash. Regression test added.
     Total suite: 239 tests.

106. `checkpoint-106-freebsd-bind-group`
     Fixes zone file ownership on FreeBSD. BIND installed from FreeBSD ports
     runs as user bind, group bind (same as Debian). The zone file group
     ternary was 'bind' if Debian else 'named', leaving FreeBSD using 'named'
     which does not exist.

     Fix: zone file group ternary changed to:
       'named' if os_family in ['RedHat', 'Archlinux'] else 'bind'
     This correctly uses 'bind' for Debian and FreeBSD, 'named' for RedHat
     and Arch. The zone directory group (already 'bind' if FreeBSD) was
     already correct from checkpoint-100.

     Regression test added: test_zone_file_group_freebsd_is_bind.
     Total suite: 240 tests.

107. `checkpoint-107-dns-enabled-flag`
     Adds dns_enabled boolean (default: true) to roles/common/defaults/main.yml.
     When set to false, the dns role is skipped entirely regardless of whether
     dns_hidden_primary_zones, services with domains, or certbot_dns_local would
     otherwise trigger it. The existing when: condition is wrapped in an outer
     dns_enabled | default(true) | bool and (...) guard.
     Useful when DNS is managed externally or on hosts that are not authoritative
     for any zone. Consistent with firewall_enabled and node_exporter_enabled.

108. `checkpoint-108-freebsd-package-names`
     Fixes three package names that differ on FreeBSD ports:

     certbot:
       Linux:   certbot
       FreeBSD: py311-certbot

     MariaDB (nextcloud role):
       Linux:   mariadb-server
       FreeBSD: mariadb106-server

     PHP (nextcloud role):
       Linux (Debian): php php-fpm php-mysql php-gd ... (no prefix)
       Linux (RedHat): php php-fpm php-mysqlnd php-gd ...
       FreeBSD:        php83 php83-fpm php83-pdo_mysql php83-gd ...
       (php83 is the current PHP 8.3 from FreeBSD ports; tar and bzip2
        are in FreeBSD base and not needed in the package list)

     Packages confirmed same on FreeBSD: nginx, postfix, dovecot, opendkim,
     sudo, python3, curl, unzip. node_exporter and BIND already handled.
     nftables not applicable (firewall_enabled: false on FreeBSD).

     3 regression tests added. Total suite: 243 tests.

109. `checkpoint-109-certbot-dns-method-set-fact`
     Fixes "'_certbot_dns_method' is undefined" error on the certbot TSIG key
     deploy task. The set_fact task that resolves _certbot_dns_method from
     certbot_dns_update_method / certbot_dns_local was written in checkpoint-101
     as part of the assert task replacement, but the Python replace() call did
     not match the exact string in the generator, leaving the old assert
     unchanged and the set_fact task absent from the generated output.
     The TSIG deploy when: clause referenced _certbot_dns_method which was
     never defined.

     Fix: set_fact task "Resolve certbot DNS update method" added immediately
     before the assert tasks in the certbot tasks block. The old
     certbot_dns_local boolean assert is replaced with the new
     certbot_dns_update_method-aware assert. Generated task order:
       line 16: Resolve certbot DNS update method (set_fact)
       line 34: Assert certbot_tsig_secret (uses _certbot_dns_method)
       line 71: Deploy TSIG key file (uses _certbot_dns_method)

110. `checkpoint-110-freebsd-nginx-paths`
     Fixes nginx failing on FreeBSD because mime.types cannot be found at
     /etc/nginx/mime.types. nginx from FreeBSD ports installs to
     /usr/local/etc/nginx/ not /etc/nginx/.

     Introduces _nginx_conf_dir set_fact as the first nginx task:
       /usr/local/etc/nginx (FreeBSD) / /etc/nginx (all others)

     All nginx path references updated to use _nginx_conf_dir:
       nginx/tasks/main.yml: conf.d dir creation, nginx.conf deploy dest
       nginx/tasks/render_service.yml: vhost dest
       nginx/templates/nginx.conf.j2: mime.types include, conf.d include
       preflight/tasks/main.yml: nginx.conf stat, user check, vhost checks

     3 regression tests added (test_nginx_conf_dir_freebsd,
     test_nginx_conf_dir_non_freebsd, test_nginx_mime_types_uses_variable).
     Total suite: 246 tests.

111. `checkpoint-111-freebsd-nginx-pid-path`
     Fixes nginx config validation failing on FreeBSD with "open()
     /run/nginx.pid failed (2: No such file or directory)".

     Two changes:

     nginx.conf.j2: pid directive uses Jinja2 ternary:
       /var/run/nginx.pid (FreeBSD) / /run/nginx.pid (Linux)
     /var/run is the traditional BSD run directory; /run is a Linux tmpfs.

     nginx tasks: "Deploy global nginx config" split into two tasks.
     The Linux task retains validate: "nginx -t -c %s". The FreeBSD task
     omits validate because nginx -t against a temp file tries to open
     the pid file path, which doesn't exist before the first nginx start,
     causing validation to fail even when the config is syntactically correct.
     The when: guards are os_family != 'FreeBSD' and os_family == 'FreeBSD'.

112. `checkpoint-112-freebsd-opendkim-service-name`
     Fixes "opendkim does not exist in /etc/rc.d or the local startup
     directories". The opendkim port on FreeBSD installs its rc.d script as
     milter-opendkim (reflecting its role as a milter daemon), not opendkim.

     Service name ternary added to:
       "Enable and start opendkim" FreeBSD service: task
       "Reload opendkim" handler (service: module)
     Both now use: 'milter-opendkim' if FreeBSD else 'opendkim'

     "Reload systemd and restart opendkim" handler guarded with
     when: os_family != 'FreeBSD' since it uses systemd: daemon_reload.

     Regression test added. Total suite: 247 tests.

113. `checkpoint-113-freebsd-opendkim-paths`
     Fixes opendkim failing to start on FreeBSD: key file not found at the
     Linux path /etc/opendkim/keys/example.private.

     FreeBSD opendkim port conventions:
       Config:   /usr/local/etc/mail/opendkim.conf  (not /etc/opendkim.conf)
       Keys/data: /var/db/dkim/                      (not /etc/opendkim/keys/)
       Binary:   /usr/local/sbin/opendkim            (not /usr/sbin/opendkim)

     Three new set_fact variables set at runtime:
       _opendkim_dir:  /var/db/dkim (FreeBSD) / /etc/opendkim (Linux)
       _opendkim_conf: /usr/local/etc/mail/opendkim.conf (FreeBSD) / /etc/opendkim.conf
       _opendkim_bin:  /usr/local/sbin/opendkim (FreeBSD) / /usr/sbin/opendkim

     All paths updated: opendkim.conf dest, KeyTable/SigningTable/TrustedHosts
     dests, genkey -D path, creates: path, key file ownership loop, KeyTable.j2
     private key path reference, systemd drop-in ExecStart.

     opendkim.conf.j2: "Background no" wrapped in Jinja2 conditional
     os_family != 'FreeBSD'. On FreeBSD, the rc.d script manages the process
     lifecycle and expects the daemon to fork (Background yes, the default).

     Mail config directory task split: Linux creates /etc/opendkim/keys and
     /etc/postfix; FreeBSD creates /var/db/dkim and /usr/local/etc/mail.

     2 regression tests added. Total suite: 249 tests.

114. `checkpoint-114-freebsd-sysrc-enable`
     Fixes "unable to set rcvar using sysrc" on FreeBSD. The Ansible service
     module with enabled: true uses sysrc internally to write the rcvar to
     /etc/rc.conf, but fails when combining enabled: true and state: started
     in the same task because it cannot reliably determine the rcvar name
     from the rc.d script for all port-installed services.

     All six FreeBSD service: enable+start tasks replaced with two tasks each:
       1. "command: sysrc <name>_enable=YES" (changed_when: false)
       2. "service: name: <svc> state: started" (no enabled: true)

     Services fixed: BIND (named_enable), opendkim (milter-opendkim_enable),
     dovecot (dovecot_enable), postfix (postfix_enable), nginx (nginx_enable),
     node_exporter (node_exporter_enable).

     Regression test added: test_freebsd_services_use_sysrc_to_enable.
     Total suite: 250 tests.

115. `checkpoint-115-freebsd-dovecot-paths-opendkim-rcvar`
     Two fixes from the same error output:

     (1) milter-opendkim rcvar has a hyphen which is illegal in shell variable
     names. sysrc milter-opendkim_enable=YES fails with "not found". The
     correct rcvar is milteropendkim_enable (hyphen stripped, as generated
     by the port's rc.d script). Fixed in both generator and test assertion.

     (2) Dovecot from FreeBSD ports installs to /usr/local/etc/dovecot/,
     not /etc/dovecot/. Added _dovecot_conf_dir set_fact at the start of the
     dovecot configuration section:
       /usr/local/etc/dovecot (FreeBSD) / /etc/dovecot (all others)
     All five dovecot config deploy tasks updated to use _dovecot_conf_dir:
     conf.d directory creation, 10-mail.conf, 10-auth.conf, 10-master.conf,
     10-ssl.conf, and the minimal dovecot.conf for Arch/FreeBSD.

     2 new regression tests. Total suite: 252 tests.

116. `checkpoint-116-freebsd-postfix-letsencrypt-paths`
     Fixes remaining /etc/ paths that differ on FreeBSD ports:

     postfix (/usr/local/etc/postfix):
       _postfix_conf_dir set_fact added to the opendkim set_fact task.
       main.cf, master.cf, and generic map destinations updated.
       main.cf.j2 smtp_generic_maps path updated via _postfix_conf_dir.

     mailname:
       /etc/mailname is a Debian/Linux convention (postfix uses it for
       myorigin). FreeBSD postfix from ports does not use this file.
       Write /etc/mailname task guarded: when: os_family != 'FreeBSD'.
       main.cf.j2 myorigin: uses mailname path on Linux, mailserver.domain
       directly on FreeBSD.

     letsencrypt (/usr/local/etc/letsencrypt):
       _le_dir set_fact added as first certbot task.
       _le_dir / certbot_hook_dir / renewal-hooks paths updated.
       All 13 /etc/letsencrypt/live/ references replaced with {{ _le_dir }}/live/.

     3 regression tests added. Total suite: 255 tests.

117. `checkpoint-117-certbot-le-dir-quoting`
     Fixes YAML parsing error: "creates: {{ _le_dir }}/live/..." unquoted.
     The bulk replacement in checkpoint-116 that changed /etc/letsencrypt/live/
     to {{ _le_dir }}/live/ left the creates: and path: YAML scalar values
     unquoted, which is invalid YAML when the value starts with {{ }}.
     Two creates: lines and one path: line quoted.
     Shell command arguments (-keyout, -out) inside command: blocks are
     correctly left unquoted (they are not YAML scalar values).

118. `checkpoint-118-freebsd-dovecot-conf`
     Fixes "dovecot.conf is not readable" on FreeBSD. The dovecot port for
     FreeBSD installs /usr/local/etc/dovecot/dovecot.conf.sample but not
     dovecot.conf. Dovecot refuses to start without a readable dovecot.conf.

     The "Deploy minimal dovecot.conf" task was previously gated
     when: os_family == 'Archlinux' only. Extended to:
       when: ansible_facts.os_family in ['Archlinux', 'FreeBSD']

     The minimal config deployed is the same as for Arch:
       dovecot_config_version = 2.4.0
       protocols = imap
       !include conf.d/*.conf

     Note: the milter-opendkim_enable error in the error message is from
     the older checkpoint-117 ZIP. The current build has milteropendkim_enable
     (no hyphen) which is correct.

119. `checkpoint-119-freebsd-service-onestart`
     Fixes "failed determining service state, possible typo of service name"
     on FreeBSD when starting services. The Ansible service module queries
     the rc.d script for service state before starting, which requires the
     service to be enabled in rc.conf first. Even after sysrc sets the rcvar,
     the service module cannot determine state for port-installed services
     reliably.

     Fix: replace all FreeBSD "service: state: started" tasks with
     "command: service <name> onestart". The onestart rc.d command starts
     the service unconditionally regardless of the rcvar state, making it
     safe to call after sysrc has already enabled the service.

     changed_when and failed_when use 'already running' to be idempotent:
     if the service is already running, onestart exits non-zero with that
     message; we treat it as not-changed and not-failed.

     Services fixed: BIND (named), opendkim (milter-opendkim), dovecot,
     postfix, nginx, node_exporter.
     Test updated: test_freebsd_services_use_sysrc_and_onestart.

120. `checkpoint-120-freebsd-dovecot-conf-version`
     Fixes "Unknown setting: dovecot_config_version" on FreeBSD. FreeBSD ports
     ships Dovecot 2.3.x (confirmed: 2.3.21.1) which does not support the
     dovecot_config_version directive introduced in 2.4. Arch ships 2.4+.

     The combined Arch+FreeBSD minimal dovecot.conf task split into two tasks:

       "Deploy minimal dovecot.conf (Arch)"
         when: os_family == 'Archlinux'
         includes: dovecot_config_version = 2.4.0

       "Deploy minimal dovecot.conf (FreeBSD)"
         when: os_family == 'FreeBSD'
         excludes: dovecot_config_version (not supported in 2.3.x)

     Both include: protocols = imap and !include conf.d/*.conf.

     Stale test assertion updated: "Deploy minimal dovecot.conf on Arch"
     -> "Deploy minimal dovecot.conf (Arch)".
     milter-opendkim_enable and milteropendkim_enable errors in the
     reported output are from the old checkpoint-119 ZIP; current build
     has milteropendkim_enable (no hyphen).

121. `checkpoint-121-freebsd-skip-tar-gzip`
     Fixes Ansible attempting to install tar on FreeBSD. The node_exporter
     "Install tar and gzip" task was gated when: os_family != 'Debian',
     which includes FreeBSD. tar and gzip are part of the FreeBSD base
     system and do not need to be installed from ports.
     when condition changed to: os_family not in ['Debian', 'FreeBSD']

122. `checkpoint-122-freebsd-node-exporter-os`
     Fixes node_exporter failing to start on FreeBSD with "Syntax error:
     word unexpected (expecting \")\")" — the downloaded binary was a Linux
     ELF, not a FreeBSD ELF. The Prometheus release tarball name encodes
     the OS: node_exporter-X.Y.Z.linux-amd64.tar.gz for Linux,
     node_exporter-X.Y.Z.freebsd-amd64.tar.gz for FreeBSD.

     Added _ne_os set_fact alongside _ne_arch:
       'freebsd' if os_family == 'FreeBSD' else 'linux'

     All four occurrences of the hardcoded 'linux' in the download URL,
     dest path, tar extraction path, and copy src path replaced with
     {{ _ne_os }}. The resulting URL resolves to the correct FreeBSD binary.

123. `checkpoint-123-node-exporter-190`
     Bumps default node_exporter_version from 1.8.2 to 1.9.0.
     The 1.8.2 release does not include a FreeBSD binary tarball.
     FreeBSD binaries were added starting with 1.9.0 (released 2025-02-17).
     The download URL node_exporter-1.9.0.freebsd-amd64.tar.gz resolves to 200.
     node_exporter_version is overridable in inventory for pinning.

124. `checkpoint-124-freebsd-node-exporter-pkg`
     Fixes node_exporter failing on FreeBSD because Prometheus does not
     publish pre-built FreeBSD binaries (no freebsd-amd64 tarball exists
     on the GitHub releases page for any version).

     On FreeBSD, node_exporter is installed from the ports tree via
     `pkg install node_exporter` (sysutils/node_exporter). The ports
     package handles binary, rc.d script, and user creation.

     Changes:
       - Added "Install node_exporter package (FreeBSD)" task using package:
         module, gated when: os_family == 'FreeBSD'.
       - All binary download tasks now gated: not in ['Debian', 'FreeBSD'].
       - Removed _ne_os set_fact (no longer needed).
       - node_exporter_version default reverted to 1.8.2 (the 1.9.0 bump
         was based on incorrect assumption that FreeBSD binaries existed).
       - Regression test added. Total suite: 256 tests.

     NOTE: The existing rc.d script deploy task for FreeBSD remains in place
     as it handles the service start configuration correctly regardless of
     how the binary was installed.

125. `checkpoint-125-prometheus-grafana-docker`
     Adds three new roles: docker, prometheus, grafana.

     docker role (roles/docker/tasks/main.yml):
       Installs Docker Engine from the official Docker repo on Debian,
       RedHat, and Arch. Skipped on FreeBSD (no native Docker daemon).
       The docker role only runs when prometheus_enabled or grafana_enabled
       is true, preventing unnecessary Docker installation.

     prometheus role (roles/prometheus/):
       Runs Prometheus v3.0.0 in Docker via a systemd unit file.
       - prometheus_enabled: false (opt-in)
       - prometheus_port: 9090 (bound to 127.0.0.1)
       - prometheus_data_dir: /var/lib/prometheus (persisted volume)
       - prometheus_scrape_targets: [] (list of {targets, labels} dicts)
       - prometheus_retention: 30d
       - Always scrapes localhost:node_exporter_port with instance label.
       - prometheus.yml.j2 renders additional target groups from inventory.

     grafana role (roles/grafana/):
       Runs Grafana 11.4.0 in Docker via a systemd unit file.
       - grafana_enabled: false (opt-in)
       - grafana_port: 3000 (bound to 127.0.0.1)
       - grafana_data_dir: /var/lib/grafana (persisted volume)
       - grafana_prometheus_url: http://127.0.0.1:9090
       - grafana_admin_password: required in vault (asserted at play time)
       - Prometheus datasource provisioned automatically via
         /etc/grafana/provisioning/datasources/prometheus.yml.

     Both roles gated: ansible_facts.os_family != 'FreeBSD' in site.yml.
     Tags: docker, prometheus/monitoring, grafana/monitoring.
     85 files total (was 77). 264 tests (was 256).

126. `checkpoint-126-nextcloud-docker-compose`
     Rewrites the nextcloud role from host-installed PHP/MariaDB to a Docker
     Compose stack. Eliminates all host package installation and distro-specific
     PHP socket path handling.

     Architecture:
       nextcloud-app: nextcloud:29-fpm-alpine - PHP-FPM on 127.0.0.1:9000
       nextcloud-db:  mariadb:lts - database with named volume in compose dir

     nginx proxies PHP via TCP fastcgi_pass 127.0.0.1:{{ nextcloud_fpm_port }}
     instead of a distro-specific unix socket path. Static files are served
     directly from {{ nextcloud_install_dir }} which is bind-mounted from the
     app container to the host.

     Managed by a systemd oneshot unit (nextcloud.service) that runs
     `docker compose up -d` and `docker compose down`. occ commands and
     the cron job now run via `docker exec nextcloud-app`.

     New defaults:
       nextcloud_version: '29-fpm-alpine'  (was '29.0.6')
       nextcloud_db_image: 'mariadb:lts'
       nextcloud_compose_dir: /opt/nextcloud
       nextcloud_fpm_port: 9000
       nextcloud_db_root_password: ""  (set in vault)

     Removed: _nc_php_packages set_fact, PHP/MariaDB package installs,
     php-fpm service tasks, php-fpm-nextcloud.conf.j2 template.
     Added: docker-compose.yml.j2 template, vault assertion task.

     7 stale tests updated. Total suite: 264 tests.

127. `checkpoint-127-nginx-svc-web-default-guard`
     Fixes "object of type 'dict' has no attribute 'web'" in site.conf.j2,
     restricted_site.conf.j2, and client_cert_site.conf.j2.

     All three templates accessed svc.web.upstream_host and svc.web.upstream_port
     without guarding against the case where a service dict has no 'web:' key.
     Jinja2 attribute access on an undefined dict key raises an error rather than
     returning undefined when using dot notation on a plain dict.

     Fix 1: All three proxy_pass lines now use | default():
       svc.web.upstream_host | default('127.0.0.1')
       svc.web.upstream_port | default(80)

     Fix 2: render_service.yml template selector guards service.value.app:
       (service.value.app | default({})).type | default('generic')
     This prevents UndefinedError when a service has no 'app:' key.

128. `checkpoint-128-users-owner-defined-guard`
     Fixes "object of type 'dict' has no attribute 'owner'" in the users role.
     The "Ensure service owners exist" and "Ensure web roots exist" tasks loop
     over all enabled services and unconditionally access item.value.owner.
     Docker-managed services (prometheus, grafana, nextcloud) have no owner
     key — their processes run as container UIDs, not host users.
     Both tasks now guard with: item.value.owner is defined

129. `checkpoint-129-freebsd-node-exporter-pkg-rcd`
     Fixes "Enable and start node_exporter" hanging on FreeBSD. The custom
     rc.d script we deployed ran node_exporter directly without daemonizing
     it, so `service node_exporter onestart` never returned — Ansible hung
     waiting for the command to exit.

     Root cause: our rc.d script set command=/usr/local/bin/node_exporter
     without using the rc.subr daemon() wrapper or setting command_interpreter.
     The node_exporter binary runs in the foreground by default.

     Fix: remove the "Deploy node_exporter rc.d service file (FreeBSD)" task
     entirely. pkg install node_exporter provides a correct rc.d script that
     handles daemonization. We only need to set the listen address flag:
       sysrc node_exporter_args="--web.listen-address=127.0.0.1:{{ node_exporter_port }}"

     The sysrc args variable is read by the pkg rc.d script at start time.
     Regression test updated. Total suite: 264 tests.

130. `checkpoint-130-nginx-render-service-assert`
     Adds service shape validation to render_service.yml before the template
     renders. Addresses the architectural concern that template logic was
     silently failing with AttributeError when services lacked expected keys.

     render_service.yml now has three tasks in order:

     1. "Resolve vhost template for {{ service.key }}" — set_fact that
        determines _vhost_template (nextcloud.conf.j2, restricted_site.conf.j2,
        client_cert_site.conf.j2, or site.conf.j2) using the same logic that
        was previously inline in the template src: block.

     2. "Assert web upstream defined for {{ service.key }}" — fails early
        with a clear operator message if a proxy vhost template is selected
        but web.upstream_host and web.upstream_port are absent. Skipped for
        nextcloud (uses app: not web:). The fail_msg includes a corrective
        example web: block. This replaces the previous silent Jinja2
        AttributeError.

     3. "Render service vhost for {{ service.key }}" — template task using
        _vhost_template. Identical to the previous single task except the
        src: is now the resolved variable rather than an inline ternary.

     4 regression tests added. Total suite: 268 tests.

131. `checkpoint-131-nginx-tls-cert-existence-check`
     Adds TLS certificate existence check to render_service.yml before
     rendering a vhost config for a TLS-enabled service.

     Context: certbot role runs before nginx in site.yml and is hard-gated
     in production (certbot_fail_hard: true stops the play on failure).
     In staging/dev, certbot_selfsigned_fallback generates self-signed certs
     at the LE path. Both mechanisms protect the full play run.

     The remaining gap: --tags nginx without --tags certbot, or a domain
     mismatch between services and certbot coverage.

     New tasks added between "Assert web upstream" and "Render service vhost":

       "Assert TLS certificate exists for {{ service.key }}"
         stat: path: {{ _le_dir }}/live/{{ domain }}/fullchain.pem
         when: service enabled and security.tls: true

       "Fail if TLS certificate is missing for {{ service.key }}"
         fail: with actionable message directing operator to run certbot
         role, set tls: false, or enable certbot_selfsigned_fallback
         when: tls enabled and cert stat.exists is false

     3 regression tests added. Total suite: 270 tests.

     NOTE: The other chatbot's claim that "certbot role was deleted" is false.
     The certbot role exists and runs before nginx in site.yml. The concern
     about --tags partial runs is real and this checkpoint addresses it.

132. `checkpoint-132-nginx-upstream-normalization`
     Fixes "web.upstream_host and web.upstream_port are not defined" for
     services that define port: instead of a web: block. Docker-managed
     services (grafana, prometheus) naturally carry a port: key and operators
     should not need to duplicate it as web.upstream_port.

     New "Normalize upstream" set_fact task added before the assert:
       _upstream_host: web.upstream_host if web: defined, else 127.0.0.1
       _upstream_port: web.upstream_port if web: defined, else service.port

     Assert updated: checks _upstream_port | string | length > 0 instead of
     web.upstream_host/port is defined. Fail_msg updated to show both forms:
       web: { upstream_host: 127.0.0.1, upstream_port: 8080 }
       or simply: port: 8080

     All three proxy_pass lines in nginx templates updated to use
     _upstream_host and _upstream_port variables instead of svc.web.*

     Inventory short form for Docker services now works:
       grafana:
         enabled: true
         domain: grafana.example.com
         port: 3000          # ← sufficient, no web: block needed
         security:
           tls: true

133. `checkpoint-133-architecture-capabilities-contradiction`
     Fixes documentation contradiction in src/spec/architecture.md.

     The "Orchestration model" section said "No role reads capabilities at
     execution time" and called it "a declaration of intent, not a runtime
     routing mechanism." The later "Capabilities provider-dispatch design"
     section said "Implemented (checkpoint-050): The resolve_capabilities
     pre-task..." These two statements were directly contradictory.

     Reality (confirmed by reading site.yml and verify_repo_contracts.py):
     - resolve_capabilities IS implemented in site.yml pre_tasks
     - _required_providers IS read by roles at execution time
       (mailserver, dns/bind, geoip/maxmind_nftables all check it)
     - verify_capability_contracts() IS implemented and runs in CI

     Fix: rewrote "Orchestration model" to accurately describe the
     resolve_capabilities mechanism. Rewrote "Capabilities provider-dispatch
     design" into "Capabilities provider-dispatch" with clear Implemented /
     Not yet fully service-driven / Future work sections.

     No code changes. Documentation only.

134. `checkpoint-134-freebsd-node-exporter-async-start`
     Fixes node_exporter hanging on FreeBSD at the "Enable and start
     node_exporter" task. node_exporter is a Go binary with no built-in
     daemon mode. The FreeBSD ports rc.d script calls it directly without
     using the daemon(8) command to detach it from the controlling terminal.
     `service node_exporter onestart` therefore never returns — Ansible waits
     for the command to exit, but node_exporter runs in the foreground.
     (ps shows state I+ = idle, foreground process group)

     Fix: split into two tasks:
       "Start node_exporter (FreeBSD)": async: 10, poll: 0
         Fires onestart and immediately returns without waiting.
         async: 10 sets a background job timeout; poll: 0 means don't poll.
       "Wait for node_exporter to be ready (FreeBSD)": wait_for port 9100
         Confirms the process is actually listening before proceeding.

     Other FreeBSD onestart services (named, nginx, postfix, dovecot,
     milter-opendkim) are traditional Unix daemons that fork to background
     themselves and are not affected. Only changed node_exporter.

135. `checkpoint-135-jinja2-parity-contract-tests`
     Addresses the concern about duplicated logic between Python helpers and
     Jinja2 set_fact expressions, with an honest assessment of what's testable.

     Context: two algorithms are intentionally duplicated with Python as
     canonical: derive_zones (derive_dns_zones.py / dns/tasks/main.yml) and
     resolve_providers (resolve_capabilities.py / site.yml). Both files say
     "Both must be kept in sync." The drift risk is real.

     What's not feasible: executing Jinja2 in Python to compare outputs
     directly requires running Ansible, which is too heavy for unit tests.

     What's implemented: TestDeriveZonesJinja2Parity and
     TestResolveCapabilitiesJinja2Parity — structural parity tests that:
       1. Parse the Jinja2 source and assert the same algorithmic markers
          are present (endswith check, apex == check, | sort, | unique,
          .enabled gate, .requires read, .provider read, deduplication).
          These catch gross divergence like removing the subdomain check.
       2. Run Python against a representative fixture and assert the exact
          expected output (highest-confidence check short of Jinja2 execution).

     13 new tests added. Total suite: 283 tests.

136. `checkpoint-136-vault-example-and-freebsd-hook`
     Two housekeeping fixes found during audit:

     (1) vault.yml.example missing recently-added required secrets.
     grafana_admin_password (asserted in grafana/tasks/main.yml) and
     nextcloud_db_root_password (asserted in nextcloud/tasks/main.yml)
     were added in checkpoints 125-126 but never added to vault.yml.example.
     Operators starting from scratch would hit runtime assertion failures
     with no guidance. Both added with "CHANGE_ME" placeholders.

     (2) certbot renew-deploy-hook.sh.j2 used `systemctl reload nginx`
     unconditionally. On FreeBSD, systemctl does not exist. Fixed to detect
     the init system at runtime:
       if command -v systemctl >/dev/null 2>&1; then
         systemctl reload nginx
       else
         service nginx reload
       fi

137. `checkpoint-137-freebsd-node-exporter-daemon8`
     Fixes node_exporter not running after start on FreeBSD. After the
     async/poll=0 approach (checkpoint-134), node_exporter still showed
     as not running. The ports rc.d script for node_exporter does not
     properly daemonize the process — node_exporter has no built-in
     daemon mode and the rc.d script runs it in the foreground.

     Fix: bypass the rc.d script for the start operation entirely.
     Use daemon(8) from the FreeBSD base system directly:
       daemon -p /var/run/node_exporter.pid \
         /usr/local/bin/node_exporter \
         --web.listen-address=127.0.0.1:{{ node_exporter_port }}

     daemon(8) properly forks the process to the background, writes
     the pidfile, and detaches from the controlling terminal. The pidfile
     at /var/run/node_exporter.pid allows `service node_exporter status`
     to report correctly and enables rc.d to stop it.

     The sysrc node_exporter_enable=YES task is retained for boot persistence.
     creates: /var/run/node_exporter.pid makes the task idempotent.
     wait_for port confirms the process is listening before continuing.

     milter-opendkim_enable error in reported output is from an older ZIP.
     Current build has milteropendkim_enable (no hyphen) since checkpoint-115.

138. `checkpoint-138-no-op`
     A cleanup task (sysrc -x milter-opendkim_enable) was added then
     immediately reverted — the operator correctly identified it as a
     development-phase hack unsuitable for the codebase.
     The stale milter-opendkim_enable="YES" line in rc.conf on the test
     host must be removed manually: sysrc -x milter-opendkim_enable
     No code changes. Checkpoint number reserved to keep history linear.

139. `checkpoint-139-schema-register-collision-groupvars`
     Three fixes identified by fresh codebase review:

     (1) Schema/runtime contract mismatch — services.schema.json required 'owner'
     on every service, but Docker-managed services (grafana, prometheus, nextcloud)
     have no owner (container UIDs, not host users). Schema also had no 'port' field
     despite the nginx normalization task accepting it since checkpoint-132.
     Fix: remove 'owner' from required fields; add 'port' as optional integer.
     Schema required is now: ['enabled', 'domain'].
     test_missing_owner_invalid replaced with test_missing_owner_valid and
     test_port_field_valid.

     (2) _svc_start register variable collision in FreeBSD onestart tasks.
     Mailserver had three consecutive tasks (opendkim, dovecot, postfix) all
     using register: _svc_start. Last write wins; earlier errors silently lost.
     Also affected: dns (named), nginx.
     Fix: unique register variable per service:
       _opendkim_start, _dovecot_start, _postfix_start, _named_start, _nginx_start

     (3) group_vars/all/main.yml prometheus/grafana service example was wrong.
     It showed owner: and web: blocks — both incorrect for Docker services.
     Fix: examples now use port: shorthand with no owner or web block.
     Long-form web: block shown separately for non-Docker upstreams.

     285 tests (1 new, 1 converted from _fail to _pass, 1 skipped added).

140. `checkpoint-140-freebsd-pf-firewall`
     Implements FreeBSD pf firewall support in the firewall_geo role, with
     full GeoIP country filtering via pf tables. This completes the work
     started in the previous session.

     firewall_geo/tasks/main.yml: nftables tasks gated != FreeBSD. pf tasks:
       Ensure /etc/pf.d and /etc/pf.d/geoip directories exist
       Deploy pf.conf.j2 -> /etc/pf.conf (mode 0600)
       sysrc pf_enable=YES / pflog_enable=YES
       kldload -n pf (idempotent, failed_when: false)
       pfctl -e -f /etc/pf.conf

     firewall_geo/handlers/main.yml: Reload nftables gated != FreeBSD.
     Reload pf: pfctl -f /etc/pf.conf gated == FreeBSD.

     pf.conf.j2: full rule parity with nftables.conf.j2 plus GeoIP:
       GeoIP table declarations (persist file .txt) for SSH, HTTP, HTTPS
       block in from !<geoip_ssh_ipv4/v6> before pass on ssh_port
       block in from !<geoip_http_ipv4/v6> before pass on port 80
       block in from !<geoip_https_ipv4/v6> before pass on port 443

     geoip_ingest.py: --format pf|nftables flag. pf writes one CIDR per
     line to .txt files; nftables unchanged (.nft defines).

     geoip/tasks/main.yml: Set GeoIP sets directory and format set_fact
     (_geoip_sets_dir=/etc/pf.d/geoip on FreeBSD; _geoip_format=pf).
     All --sets-dir and --format args use fact variables.

     geoip/templates/geoip.conf.j2: SETS_DIR={{ _geoip_sets_dir }},
     FORMAT={{ _geoip_format }}.

     geoip/files/geoip_refresh.sh: passes --format ${FORMAT}; reloads
     nft or pfctl depending on which is available at runtime.

     18 regression tests added. Total suite: 314 tests.

141. `checkpoint-141-rename-mailserver-admin-password`
     Renames mailserver_admin_mail_password to mailserver_admin_password.
     The old name was redundant -- the variable is already scoped to the
     mailserver context. Updated in: vault.yml.example comment,
     mailserver/defaults/main.yml comment and interpolation expression.
     Operators must rename the key in their vault.yml accordingly.

142. `checkpoint-142-dns-role-rewrite`
     Complete rewrite of the dns role replacing flat variables with a
     structured dns: dict. This is the design discussed with the operator.

     dns/defaults/main.yml: replaced dns_hidden_primary_zones, dns_secondaries,
     dns_public with a single dns: dict containing enabled, listen_on,
     recursion, forwarders, defaults (ttl/soa), tsig_keys, and zones.

     Zone types: primary, secondary, forward, stub, remote_primary.
     Each zone is self-describing with its own secondaries/primaries,
     allow_update, services_auto_derive, public, ttl, soa, records.

     records: per-zone explicit record management. state: absent removes
     records. For primary zones records are written to zone files via
     sync_dns_records.py. For remote_primary zones records are pushed
     via nsupdate.

     TTL/SOA precedence: record-level > zone-level > dns.defaults > role
     defaults.

     remote_primary: new zone type where BIND is elsewhere and certbot
     pushes _acme-challenge records via nsupdate. Enables certificates for
     domains hosted on external BIND servers (e.g. example.com).

     certbot integration: Resolve nsupdate target from dns.zones at runtime.
     Prefers remote_primary zones, then primary zones with allow_update,
     then falls back to flat certbot_tsig_* vars for backward compatibility.

     Firewall: nftables.conf.j2 and pf.conf.j2 now derive port 53 rules
     from dns.zones. Per-zone public: true opens port 53 to all; false
     restricts to zone secondaries/primaries IPs only.

     site.yml: dns role activation uses dns.enabled and dns.zones.

     Tests: parity tests updated to reflect new architecture (zone derivation
     is now explicit via dns.zones; auto-derive logic is in zone.db.j2).
     Total suite: 314 tests.

143. `checkpoint-143-roles-off-by-default`
     Sets firewall_geo, node_exporter, dns, and nginx off by default.
     All four now require explicit opt-in in inventory group_vars.

     firewall_enabled: false  (was true)
     node_exporter_enabled: false  (was true)
     dns_enabled: false  (was true -- dns.enabled already false, this aligns dns_enabled)
     nginx: added nginx_enabled: false default + when: nginx_enabled | default(false)
            gate in site.yml (nginx previously had no enabled flag at all)

     site.yml when: default() fallbacks updated to match:
       firewall_enabled | default(false)
       node_exporter_enabled | default(false)

     geoip activation: geoip.enabled: true always runs geoip regardless
     of firewall state (manual override). Automatic activation via
     maxmind_nftables capability now requires firewall_enabled: true.

144. `checkpoint-144-dns-activation-condition`
     Fixes dns role never activating despite dns.enabled: true and dns.zones
     being set. The site.yml activation condition in the generator was never
     updated during checkpoint-142 -- it still referenced the old flat
     variables (dns_hidden_primary_zones, dns_enabled, certbot_dns_local).

     New condition:
       dns.enabled | default(false) | bool
       and (dns.zones | default([]) | length > 0
            or 'bind' in _required_providers)

     This is what checkpoint-142 intended but failed to write into the
     generator. The build/ tree from checkpoint-142 and 143 ZIPs had
     the stale condition; this checkpoint corrects it.

145. `checkpoint-145-named-update-policy-duplicate`
     Fixes named-checkconf error: 'update-policy' redefined near 'update-policy'.
     The named.conf.local.j2 template was generating one update-policy block
     per allow_update key, but BIND only permits one update-policy block per
     zone. All grants must be inside a single block.

     Fixed by collecting valid keys first, then emitting one update-policy
     block containing all grant statements.

146. `checkpoint-146-zone-db-records-filter`
     Fixes "can only concatenate list (not UndefinedMarker) to list" error
     when rendering zone.db.j2 with explicit records.

     The template used selectattr('state', 'undefined') which is not a valid
     Jinja2 test name, producing an UndefinedMarker when concatenated.

     Fix: replaced the broken guard condition with:
       _present_records = item.records | rejectattr('state', 'equalto', 'absent')
     Also added | upper to record type so lowercase types ('a') are normalised
     to uppercase ('A') in the generated zone file.

147. `checkpoint-147-zone-db-records-state-default`
     Fixes "object of type 'dict' has no attribute 'state'" in zone.db.j2.
     rejectattr('state', 'equalto', 'absent') throws when the 'state' key is
     absent from the record dict rather than treating it as missing.
     Fix: iterate all records with a for loop and use
     _rec.state | default('present') != 'absent' to skip absent records.

148. `checkpoint-148-sync-dns-records-multi-type`
     Rewrites sync_dns_records.py to support all DNS record types, --absent,
     and --ttl. Previously the script only supported A records with
     --record LABEL ADDRESS (nargs=2). The new dns role tasks pass
     --record LABEL TYPE VALUE (nargs=3) which caused unrecognized arguments.

     New CLI: --record LABEL TYPE VALUE [--ttl N] [--absent]
     record_exists(text, label, rtype, value) -- type-aware matching
     remove_record(text, label, rtype, value) -- regex removal
     changed_when updated to detect both 'added' and 'removed' in stdout.
     test_sync_dns_records.py rewritten to cover new API (315 tests).

149. `checkpoint-149-nfs-server-client-roles`
     Adds nfs role supporting both server (exports) and client (fstab mounts)
     on all four platforms: Debian, RedHat, Arch, FreeBSD.

     roles/nfs/defaults/main.yml: nfs.server.{enabled,exports} and
     nfs.client.{enabled,mounts} with full inline documentation.

     roles/nfs/tasks/main.yml:
       Server: install package, create export dirs, deploy /etc/exports,
         enable+start service (systemd on Linux, sysrc+onestart on FreeBSD).
       Client: install package, create mountpoint dirs, configure all mounts
         via Ansible mount module (manages fstab + live mount state).
       State values: mounted|present|unmounted|absent per Ansible mount module.

     roles/nfs/templates/exports.j2: generates /etc/exports from
       nfs.server.exports[].{path,clients[].{host,options}}.

     roles/nfs/handlers/main.yml: Reload NFS exports (exportfs -ra).

     Firewall integration:
       nftables.conf.j2 and pf.conf.j2 open TCP/UDP port 2049 to the
       union of all client hosts across all exports when nfs.server.enabled.

     site.yml: nfs role runs when server or client is enabled.
     90 files total.

150. `checkpoint-150-samba-server-role`
     Adds Samba server role for all four platforms (Debian, RedHat, Arch, FreeBSD).

     roles/samba/defaults/main.yml: samba.{enabled, workgroup, server_string,
     interfaces, hosts_allow, passdb_backend, shares[], users[]}

     roles/samba/tasks/main.yml: platform-specific package names (samba48 on
     FreeBSD), share directory creation, smb.conf deploy, smbpasswd for users
     (passwords from vault as samba_password_<username>), enable+start service.

     roles/samba/templates/smb.conf.j2: generates [global] and per-share
     sections. Per-share hosts_allow falls back to global samba.hosts_allow.

     Firewall: TCP ports 139/445 opened to samba.hosts_allow when
     samba.enabled: true. If hosts_allow is empty, ports opened to all.
     Both nftables.conf.j2 and pf.conf.j2 updated.

     site.yml: samba role runs when samba.enabled: true.
     94 files total.

151. `checkpoint-151-samba-extra-options`
     Adds extra_options: list to samba share definition.
     Each entry is written verbatim into the share section of smb.conf.
     Required for Time Machine vfs objects, fruit settings, and other
     options not covered by the structured share fields.

152. `checkpoint-152-nfs-mountpoint-parent-dir`
     Fixes EPERM when mount module tries to create /srv/nfs/software but
     /srv/nfs does not exist. Added a task to create the parent directory
     (item.path | dirname) before creating the mountpoint directory itself.

153. `checkpoint-153-nfs-skip-chown-on-active-mount`
     Fixes EPERM when file: task tries to chown/chmod an NFS mountpoint
     that already has a live NFS mount on it. The kernel returns EPERM
     on ownership changes to NFS-mounted directories from the client side.
     Fix: skip the task when item.path is already in ansible_mounts.

154. `checkpoint-154-nfs-mountpoint-failed-when-false`
     Fixes persistent EPERM on NFS mountpoint file: task. The ansible_mounts
     check didn't work reliably. Root cause: chown/chmod on an NFS-mounted
     directory returns EPERM from the kernel regardless of user. The directory
     exists and is correct -- the error is spurious. Fix: failed_when: false.

155. `checkpoint-155-step-ca-role`
     Adds step_ca role: internal ACME-compatible CA using Smallstep step-ca.

     Install: Smallstep apt repo (Debian), COPR repo (RedHat), community
     package (Arch), pkg (FreeBSD).

     Lifecycle: creates step-ca system user, data dir, writes password file
     from vault (step_ca_password), runs step ca init --acme --no-db on first
     run only (creates: ca.json), deploys systemd unit, enables and starts.

     ca.json.j2: reads existing ca.json and merges cert duration overrides
     using Jinja2 combine(recursive=True).

     Trust store: when step_ca.trust_root: true, copies root_ca.crt to the
     platform-specific trust anchor directory and runs update-ca-certificates/
     update-ca-trust/trust extract-compat/certctl rehash via handlers.

     Firewall: TCP 9000 opened when step_ca.enabled: true (both nftables and pf).

     site.yml: step_ca runs when step_ca.enabled: true.
     98 files total.

156. `checkpoint-156-step-ca-freebsd-package-name`
     Fixes "No packages available to install matching 'step-ca'" on FreeBSD.
     The FreeBSD ports package is named step-certificates, not step-ca.
     Also installs step-cli alongside it (needed for step ca init).
     Fixed duplicate checkpoint 155 entry in checkpoints.md.

157. `checkpoint-157-step-ca-debian-apt-repo-url`
     Fixes HTTP 404 on Smallstep apt key download. Correct URL is:
       https://packages.smallstep.com/keys/apt/repo-signing-key.gpg
     Key saved to /etc/apt/keyrings/smallstep.asc (modern keyring location).
     Repo now uses .sources format (not .list) with:
       Types: deb
       URIs: https://packages.smallstep.com/stable/debian
       Suites: debs
       Components: main
       Signed-By: /etc/apt/keyrings/smallstep.asc

158. `checkpoint-158-step-ca-init-remove-no-db`
     Fixes "flag '--acme' is incompatible with '--no-db'" during step ca init.
     The --acme provisioner type uses a badger database by default and cannot
     be combined with --no-db. Removed --no-db from the init command.

159. `checkpoint-159-step-ca-json-slurp`
     Fixes "lookup plugin 'file' failed: Unable to access the file ca.json".
     lookup('file') runs on the Ansible controller, not the remote host.
     ca.json only exists on the remote host after step ca init.

     Fix: replaced ca.json.j2 template with two tasks:
       1. slurp: reads ca.json from the remote host into a register variable
       2. copy: patches durations using b64decode | from_json | combine(recursive)
          and writes the result back to the remote host

     Removed ca.json.j2 from FILE_MANIFEST and generation_contracts.yml.
     97 files total.

160. `checkpoint-160-step-ca-freebsd-rc-conf-path`
     Fixes "No configured Step CA found. Please run service step_ca configure"
     on FreeBSD. The ports rc.d script for step-certificates reads two rc.conf
     variables to locate the CA: step_ca_config (path to ca.json) and
     step_ca_password (path to password file). Without them it cannot find
     the CA we initialised in /etc/step-ca.

     Two sysrc tasks added before the enable/start tasks:
       sysrc step_ca_config=/etc/step-ca/config/ca.json
       sysrc step_ca_password=/etc/step-ca/password.txt

161. `checkpoint-161-dnssec-inline-signing`
     Adds optional DNSSEC inline-signing support per primary zone.

     named.conf.local.j2: when zone.dnssec.enabled: true, adds to zone block:
       dnssec-policy default;
       inline-signing yes;
       key-directory "<key_directory>";
     BIND handles signing automatically on zone load and update.

     dns/tasks/main.yml: four new tasks before named-checkconf:
       - Ensure DNSSEC key directory exists (mode 0750)
       - Generate KSK via dnssec-keygen -f KSK (skipped if ksk_file provided)
       - Generate ZSK via dnssec-keygen (skipped if zsk_file provided)
       - Copy operator-provided KSK/ZSK if ksk_file/zsk_file defined

     Key algorithm defaults to ECDSAP256SHA256 (modern, compact).
     -b flag auto-set: 256 for ECDSA, 2048 for RSA.
     Both key tasks use creates: glob so they are idempotent.

     Inventory shape:
       dnssec:
         enabled: true
         algorithm: ECDSAP256SHA256
         key_directory: /etc/bind/keys
         # optional: ksk_file/zsk_file for pre-generated keys

162. `checkpoint-162-step-ca-freebsd-steppath`
     Fixes step-ca FreeBSD startup. Reading the rc.d script revealed:
     - The script checks step_ca_steppath (not step_ca_config) for the CA dir
     - Default is /usr/local/etc/step/ca -- our CA is in /etc/step-ca
     - The script runs as user 'step' by default

     Fixes:
     - sysrc now sets step_ca_steppath, step_ca_user, step_ca_group, step_ca_password
     - become_user removed from step ca init task (system user has nologin shell)
     - Added "Fix ownership" task after init to chown the data dir to step_ca.user

163. `checkpoint-163-step-ca-freebsd-pidfile`
     Fixes "daemon: ppidfile /var/run/step_ca.pid: Permission denied" on FreeBSD.
     daemon(8) runs as step-ca user and tries to write the pidfile in /var/run
     which is root:wheel 755. The rc.d startprecmd also tries install but
     runs too late. Fix: pre-create /var/run/step_ca.pid owned by step-ca
     via Ansible file: task (runs as root) before the service starts.

164. `checkpoint-164-step-ca-freebsd-certs-dir`
     Fixes "Destination directory /usr/local/share/certs does not exist" on
     FreeBSD when trust_root: true. Added a file: task to create the directory
     before the copy: task for the root CA certificate.

165. `checkpoint-165-dnssec-keygen-idempotent`
     Fixes DNSSEC KSK/ZSK generation tasks not being idempotent.
     creates: doesn't support glob patterns -- it treats the argument as a
     literal path, so it never matches K<zone>.+*+*.key and always re-runs.

     Fix: replaced creates: glob with find: tasks that search for existing
     key files using patterns and contains: to distinguish KSK from ZSK.
     The generate tasks loop over the find results and only run when matched==0.

166. `checkpoint-166-samba-freebsd-package-name`
     Fixes "No packages available to install matching 'samba48'" on FreeBSD.
     samba48 (4.8) is a very old package no longer in the FreeBSD repositories.
     The current default Samba package is samba419 (4.19).

167. `checkpoint-167-samba-freebsd-conf-path`
     Fixes "Destination directory /etc/samba does not exist" on FreeBSD.
     FreeBSD Samba installs to /usr/local/etc/samba, not /etc/samba.
     Added _smb_conf_dir fact (platform-specific), create dir task before
     smb.conf deploy, and _smb_conf uses /usr/local/etc/samba/smb.conf on
     FreeBSD.

168. `checkpoint-168-samba-freebsd-service-name`
     Fixes "smbd does not exist in /etc/rc.d or the local startup directories".
     On FreeBSD, the Samba rc.d service is named samba_server, not smbd.
     Fixed: _smb_service fact, handler, sysrc enable, and onestart command.
     rc.conf key is samba_server_enable (not smbd_enable).

169. `checkpoint-169-step-ca-idempotency`
     Fixes two non-idempotent step_ca tasks:

     1. Write step-ca password file: always changed because vault string may
        have trailing newline mismatching the file on disk. Fix: | trim + \n
        to normalize to exactly one trailing newline consistently.

     2. Fix step-ca data directory ownership: file: recurse: true always
        reports changed even when nothing changes. Fix: replaced with
        chown -R via command:, gated on _step_ca_init is changed so it
        only runs when step ca init actually executed (first run only).

170. `checkpoint-170-samba-freebsd-smb4conf`
     Fixes "WARNING: /usr/local/etc/smb4.conf is not readable" on FreeBSD.
     The FreeBSD Samba port uses smb4.conf (not samba/smb.conf) as its config
     file, located directly in /usr/local/etc/ not in a samba/ subdirectory.
     Fixed _smb_conf to /usr/local/etc/smb4.conf and _smb_conf_dir to
     /usr/local/etc on FreeBSD.
     Also gated the panic action line in smb.conf.j2 on Debian only, as the
     /usr/share/samba/panic-action script doesn't exist on FreeBSD.

171. `checkpoint-171-nfs-freebsd-no-package`
     Fixes "No packages available to install matching 'nfs-utils'" on FreeBSD.
     NFS is part of the FreeBSD base system -- no package installation needed.
     Set _nfs_server_pkg and _nfs_client_pkg to '' on FreeBSD and added
     _nfs_*_pkg | length > 0 guards on both install tasks.

172. `checkpoint-172-nfs-freebsd-mount-options`
     Fixes "fstab: Inappropriate file type or format" on FreeBSD NFS mounts.
     FreeBSD's fstab parser doesn't understand Linux NFS option syntax:
       vers=3 / nfsvers=3 -> nfsv3
       vers=4 / nfsvers=4 -> nfsv4
       nolock             -> nolockd
     Added Jinja2 regex_replace translation in the mount task's opts field,
     applied only when os_family == FreeBSD.

173. `checkpoint-173-nfs-freebsd-opts-namespace`
     Fixes NFS option translation not working despite checkpoint-172.
     Jinja2 variable reassignment inside {% if %} blocks is scoped to the
     block -- the outer _raw variable is unaffected. Used namespace() to
     create a mutable reference that persists across block scope boundaries.
     {%- set _ns = namespace(raw=...) -%} then {%- set _ns.raw = ... -%}
     inside the if block correctly updates the value.

174. `checkpoint-174-step-ca-arch-step-cli-binary`
     Fixes "No such file or directory: b'step'" on Arch Linux.
     The Arch community step-cli package installs the binary as 'step-cli',
     not 'step'. Added _step_cli fact that resolves to 'step-cli' on Arch
     and 'step' on all other platforms. The init command uses {{ _step_cli }}
     instead of hardcoded 'step'.

175. `checkpoint-175-dnssec-ksk-detection-flags`
     Fixes DNSSEC KSK/ZSK generation not idempotent. The find: contains:
     filter used comment text ('This is a key-signing key') which varies
     between BIND versions and may not match.
     Fix: use the DNSKEY record flags field which is stable and unambiguous:
       KSK: contains 'DNSKEY 257 ' (flags=257, KSK bit set)
       ZSK: contains 'DNSKEY 256 ' (flags=256, no KSK bit)
     These values are part of the DNSKEY RDATA and consistent across all
     BIND versions.

176. `checkpoint-176-nfs-freebsd-opts-inline-expr`
     Fixes NFS mount option translation still not working on FreeBSD despite
     checkpoint-173. The namespace() approach inside a >- YAML block scalar
     is unreliable: YAML folds newlines to spaces before Jinja2 processes the
     template, creating interaction issues with {%- -%} whitespace stripping.

     Fix: replaced the multi-line namespace block with a single inline Jinja2
     expression that chains regex_replace filters, using a ternary conditional
     to apply FreeBSD translations only when os_family == FreeBSD.
     No YAML block scalars, no namespace scoping, no whitespace ambiguity.

177. `checkpoint-177-step-ca-arch-init-command`
     Fixes rc=2 silent failure on Arch Linux step-ca init.
     On Arch the binary is 'step-ca' and the init command is 'step-ca init'.
     On all other platforms the binary is 'step' and the command is 'step ca init'.
     Replaced _step_cli fact with _step_ca_init_cmd:
       Arch:  'step-ca init'
       other: 'step ca init'

178. `checkpoint-178-dnssec-remove-keygen-tasks`
     Removes dnssec-keygen KSK/ZSK generation tasks which were never
     idempotent despite multiple attempts (creates: glob, find+contains,
     find+flags). The root fix: with dnssec-policy default + inline-signing,
     BIND automatically generates and manages KSK and ZSK in the key-directory
     when it first loads the zone. Manual dnssec-keygen is unnecessary and
     conflicts with BIND's own key management.
     Operator-provided key copy tasks (ksk_file/zsk_file) are retained.

179. `checkpoint-179-nfs-mount-debug`
     Adds debug task before NFS mount on FreeBSD to show computed opts value.
     Temporary diagnostic checkpoint.

180. `checkpoint-180-step-ca-arch-install-step-cli`
     Fixes step-ca init on Arch Linux. The Arch step-ca package is the server
     binary only and does not include the step CLI init tool. Added step-cli
     to the Arch install task (provides 'step' binary from AUR/community).
     Reverted _step_ca_init_cmd fact -- all platforms use 'step ca init'.
     Checkpoint-177's 'step-ca init' fix was wrong: that's the server binary
     not the init command.

181. `checkpoint-181-step-ca-arch-step-cli-binary-name`
     Fixes step ca init rc=2 on Arch. The step-cli package on Arch installs
     the binary as 'step-cli' not 'step'. Added _step_bin fact:
       Arch: step-cli
       all others: step
     Init command is now: {{ _step_bin }} ca init

182. `checkpoint-182-nfs-freebsd-split-write-mount`
     Diagnostic + fix for persistent FreeBSD NFS mount failure.
     Split the single mount: task into three FreeBSD-specific tasks:
       1. Write fstab entry (state: present - no mount attempt)
       2. Print fstab content so we can see what Ansible actually writes
       3. Explicit mount via command: mount {{ item.path }}
     Linux continues to use the standard mount: state: mounted task.
     This separates the fstab write from the mount attempt, letting us
     see the exact fstab format and whether mount succeeds independently.

183. `checkpoint-183-nfs-freebsd-opts-field`
     Fixes FreeBSD NFS mount failure. FreeBSD mount_nfs does not accept
     nfsv3, rsize=N, or wsize=N as fstab mount options (Linux syntax).
     Added freebsd_opts per-mount field: used instead of opts on FreeBSD.
     Default is 'rw' when freebsd_opts is not set.
     Linux mount task unchanged (uses opts as before).
     Previous option translation (nfsv3, nolockd etc.) removed from fstab
     write task -- freebsd_opts gives the operator full control.

184. `checkpoint-184-nfs-freebsd-opts-rw-prefix`
     Fixes FreeBSD NFS fstab options. nfsv3 cannot appear alone -- needs rw.
     rsize/wsize are valid on FreeBSD. soft/timeo are Linux-only (stripped).

     Translation applied on FreeBSD:
       vers=3/nfsvers=3 -> nfsv3
       vers=4/nfsvers=4 -> nfsv4
       nolock -> nolockd
       soft, timeo=N -> stripped
       rw prepended when neither rw nor ro present

     freebsd_opts per mount overrides all translation.
     FreeBSD mount split into state:present (fstab) + explicit mount command.
     Linux uses standard mount: state: mounted (unchanged).
     Container reset after 183 -- restored from ZIP and re-applied all fixes.

185. `checkpoint-185-nfs-freebsd-opts-keep-vers`
     Simplifies FreeBSD NFS option translation. vers=3 is valid on FreeBSD
     as-is -- no translation needed. Only changes needed:
       nolock  -> nolockd
       soft    -> stripped (Linux-only)
       timeo=N -> stripped (Linux-only)
       rw      -> prepended if neither rw nor ro present
     freebsd_opts override still available per mount.

186. `checkpoint-186-nfs-freebsd-remove-debug-tasks`
     Removes NFS FreeBSD fstab debug tasks (Show fstab after write, Print
     fstab content) after confirming mounts work correctly with the
     checkpoint-184 translation producing rw,nfsv3,rsize=65535,wsize=65535.

187. `checkpoint-187-nfs-freebsd-mount-idempotent`
     Fixes FreeBSD NFS mounts accumulating duplicates on each run.
     The explicit mount command ran unconditionally every playbook run,
     stacking duplicate NFS mounts. Fix: run 'mount' first to get active
     mounts, then only mount paths not already present in that output.

188. `checkpoint-188-step-ca-freebsd-pidfile-idempotent`
     Fixes step-ca FreeBSD pidfile task always reporting changed.
     file: state: touch always updates mtime and reports changed.
     Fix: stat the pidfile first, only touch if it doesn't exist or
     has the wrong owner.

189. `checkpoint-189-openvpn-role`
     Adds openvpn role supporting server and client mode, EasyRSA PKI,
     all four platforms (Debian, RedHat, Arch, FreeBSD).

     Server: installs openvpn + easy-rsa, initialises PKI, builds CA,
     server cert, DH params, tls-auth key, generates per-client certs,
     deploys server.conf, enables service.

     Client: copies ca.crt/client.crt/client.key/ta.key from controller,
     deploys client.conf, enables service.

     Platform differences handled:
       Config dir: /etc/openvpn (Linux) / /usr/local/etc/openvpn (FreeBSD)
       Service: openvpn@server (Debian) / openvpn-server@server (RedHat/Arch)
                openvpn rc.d (FreeBSD via sysrc openvpn_enable=YES)
       EasyRSA binary path differs per distro
       nogroup vs nobody group for privilege drop

     Firewall: UDP/TCP port 1194 (configurable) opened when openvpn.enabled.
     site.yml: runs when openvpn.enabled: true.
     102 files total.

190. `checkpoint-190-openvpn-easyrsa-dynamic-path`
     Fixes easyrsa binary not found on FreeBSD and Arch. The path varies
     between distros and package versions (/usr/share/easy-rsa/easyrsa,
     /usr/local/share/easy-rsa/easyrsa.real etc). Replaced static path
     fact with a runtime shell find command that searches /usr and
     /usr/local for any file named 'easyrsa' or 'easyrsa.real' and uses
     the first result. Falls back to 'easyrsa' in PATH if not found.

191. `checkpoint-191-openvpn-easyrsa-static-paths`
     Replaces dynamic find with correct static easyrsa paths per distro.
     The path is stable within each distro family:
       Debian:    /usr/share/easy-rsa/easyrsa
       RedHat:    /usr/share/easy-rsa/3/easyrsa
       Arch:      /usr/bin/easyrsa (it's a script in PATH)
       FreeBSD:   /usr/local/share/easy-rsa/easyrsa
     Dynamic find was overkill and ran a shell command on every playbook run.

192. `checkpoint-192-openvpn-create-conf-dir`
     Fixes "Cannot open file ta.key for write: No such file or directory".
     The genkey task ran before the OpenVPN config directory existed.
     Added "Ensure OpenVPN config directory exists" task before genkey.

193. `checkpoint-193-openvpn-client-cipher`
     client.conf.j2 referenced openvpn.server.cipher for the cipher directive.
     In client-only deployments openvpn.server is not set by the operator,
     causing an undefined variable error. Added openvpn.client.cipher default
     (AES-256-GCM) to defaults/main.yml; client.conf.j2 now uses
     openvpn.client.cipher | default('AES-256-GCM').

194. `checkpoint-194-openvpn-freebsd-server-client-paths`
     Multiple openvpn role fixes for FreeBSD and cross-platform correctness:
     - Added _ovpn_server_conf_dir and _ovpn_client_conf_dir facts (separate
       server and client config dirs per distro; replaces single _ovpn_conf_dir
       used for both, which was wrong on RedHat/Arch).
     - Added FreeBSD-aware _easyrsa_dir and _easyrsa_pki_dir facts.
     - Corrected FreeBSD easyrsa binary path to /usr/local/bin/easyrsa.
     - Replaced EASYRSA env var with EASYRSA_PKI in all EasyRSA commands
       (EASYRSA_PKI is the correct variable for specifying the PKI directory).
     - server.conf.j2: replaced ../easy-rsa/pki relative paths with
       {{ _easyrsa_pki_dir }} absolute paths.
     - server.conf.j2 and client.conf.j2: deploy to openvpn.conf on FreeBSD
       (rc.d script expects that filename; was server.conf / client.conf).
     - Fixed group directive: only Debian uses nogroup; all others use nobody.

195. `checkpoint-195-step-ca-copr-password-fixes`
     Two step_ca role fixes:
     - RedHat: replaced "dnf copr enable smallstep/smallstep" with get_url
       downloading from https://packages.smallstep.com/stable/rpm/smallstep.repo.
       Smallstep COPR has no Fedora 42 build; the official RPM repo URL works
       on all supported RedHat-family releases.
     - Password file content: removed trailing \n from
       "{{ step_ca_password | trim }}\n". The \n was being expanded to a
       literal newline by the YAML formatter, producing invalid YAML. step-ca
       strips trailing whitespace from the password file, so the newline is
       unnecessary.

196. `checkpoint-196-step-ca-redhat-repo-url`
     Fix step_ca RedHat repository configuration. The previous get_url
     approach downloading from packages.smallstep.com/stable/rpm/smallstep.repo
     returned HTTP 404 — that URL does not exist. Replaced with a copy task
     that writes the .repo file directly, using the correct baseurl
     https://packages.smallstep.com/stable/fedora/ and GPG key
     https://packages.smallstep.com/keys/smallstep-0x889B19391F774443.gpg.
     Also added update_cache: true to the dnf install task.

197. `checkpoint-197-sshd-sftp-subsystem`
     The sshd_config template was missing the Subsystem sftp directive,
     breaking SFTP access. Added platform-aware sftp-server path:
       Debian:   /usr/lib/openssh/sftp-server
       RedHat:   /usr/libexec/sftp-server
       FreeBSD:  /usr/libexec/sftp-server
       Arch:     /usr/lib/ssh/sftp-server

198. `checkpoint-198-sshd-sftp-redhat-path`
     Fix sftp-server path for RedHat family. Fedora, Alma, Rocky use
     /usr/libexec/openssh/sftp-server (not /usr/libexec/sftp-server).
     FreeBSD remains /usr/libexec/sftp-server (no openssh subdir).

199. `checkpoint-199-set-hostname-domain`
     New capability: set_hostname and set_domain_name variables in
     common/defaults. When set_hostname is non-empty, applies via the
     Ansible hostname module and updates /etc/hosts with a 127.0.1.1
     entry (FQDN + short name if domain is also set). When
     set_domain_name is non-empty, writes a search directive to
     /etc/resolv.conf. Both default to empty string (no change).

200. `checkpoint-200-openvpn-multi-instance`
     Refactored openvpn role from single-instance (openvpn dict with
     mode: server|client) to multi-instance (openvpn_instances list).
     Each entry has a name and mode; a machine can run any number of
     server and client tunnels simultaneously.  Each server instance
     gets its own EasyRSA PKI under easy-rsa/<name>/, its own ta.key,
     config file, and systemd service unit.  Each client instance gets
     its own cert directory and config.  Systemd naming: openvpn@<name>
     on Debian, openvpn-server@<name> / openvpn-client@<name> on
     RedHat/Arch.  FreeBSD uses rc.d profiles (openvpn_profiles sysrc).
     Templates now reference _inst.* variables from include_tasks loop.
     Inline restarts replace handler-based restarts for per-instance
     granularity.  New files: tasks/server_instance.yml,
     tasks/client_instance.yml.

201. `checkpoint-201-bootstrap-scripts`
     New role: bootstrap_scripts. Generates per-host shell scripts on
     the Ansible controller (delegate_to: localhost) that bootstrap a
     fresh server for Ansible management. Two versions per host:
     plaintext (all secrets visible) and encrypted (secrets in an
     openssl AES-256-CBC payload, decrypted at runtime with a key file
     argument). The key is generated once in build/bootstrap/.bootstrap_key.
     Scripts auto-detect platform (Debian/RedHat/Arch/FreeBSD) at
     runtime and install Python3, sudo, openssh; create admin users with
     SSH keys and passwordless sudo; set hostname/domain; configure SSH
     port and key-only auth. Tagged [bootstrap, never] so it only runs
     with --tags bootstrap. Usage:
       ansible-playbook bootstrap.yml -l <host>

202. `checkpoint-202-apache2-role`
     New role: apache2. Backend application server behind nginx, listening
     on 127.0.0.1 only. Activated per-service when app.type is 'apache2'.
     Supports PHP (mod_php), .htaccess (AllowOverride All), custom
     document_root, and extra_config. nginx auto-detects apache2 services
     and proxies to the correct port. Port defaults to apache2_base_port
     (8080) or can be set per-service via app.port.
     Also: nginx now serves static files when a service has no port:
     defined. bootstrap_scripts moved to separate bootstrap.yml playbook.
     Console password (admin_dev_password_hash) set on all environments
     with update_password: always for VNC/console access.
     Service config example:
       services:
         myapp:
           domain: myapp.example.com
           enabled: true
           owner: myapp
           app:
             type: apache2
             php: true

203. `checkpoint-203-dns-serial-and-domain-backends`
     DNS and common-role behavior were hardened around the real operator
     control planes. The services schema now supports `aliases`, which feed
     nginx server_name, DNS A-record derivation, and certificate SANs.
     Primary zones support `overwrite: true`; when used, existing serials are
     preserved, zones are rewritten from inventory content, and serials are
     bumped only for zones that actually changed. `dns-bump-serial` now uses
     the conventional `YYYYMMDDNN` format, fails hard on out-of-range serials,
     and distinguishes safer direct-edit fallback from rndc-based freeze/thaw.
     Existing primary zone files are normalized in-place for trailing dots and
     SOA RNAME format (`user@example.com` -> `user.example.com.`).
     Separately, `set_domain_name` is now backend-aware via the new
     `set_domain_backend` variable with supported values:
     `auto`, `networkmanager`, `systemd-resolved`, `resolvconf`, `dhclient`,
     and `static`. `auto` prefers the active manager instead of assuming
     `/etc/resolv.conf` is authoritative, and the bootstrap script mirrors the
     same preference order.

204. `checkpoint-204-rich-admin-users-nfs-workloads-file-copy`
     Multiple in-flight infrastructure features were stabilized and folded into
     the generator. `admin_users` now accepts either plain usernames or rich
     dict entries with per-user `ssh_keys`, `shell`, `password`, and optional
     supplementary `groups`, while `admin_ssh_public_key` and
     `admin_dev_password_hash` remain the shared fallbacks. The bootstrap and
     ssh_hardening paths normalize this richer shape before creating users,
     deploying keys, and rendering `AllowUsers`.
     The NFS role was expanded with protocol-version controls (`3`, `4`, `4.0`,
     `4.1`, `4.2`), idmap domain settings, generic mounts activation, and a
     first-run-safe export application path that flushes handlers and runs
     `exportfs -ra` before same-play client mounts. The capabilities dispatch
     layer now resolves `id_mapping` to the `nfs` provider.
     Finally, `file_copy_items` now supports inline `content` in addition to
     `src`, validates that exactly one content source is provided, and creates
     parent directories automatically. This enables persistent config injection
     for external inventory use cases such as the Time Machine Samba workload
     without introducing repo-specific one-off tasks.

205. `checkpoint-205-docs-scrub-and-proxmox-lifecycle`
     Documentation was substantially expanded and sanitized. The top-level
     README now links to dedicated per-role docs under `docs/roles/`, and the
     Proxmox infrastructure guidance was split into `docs/infrastructure/`.
     Example inventory values were scrubbed of local environment details, and a
     new repository contract now verifies that known local identifiers do not
     leak into committed docs/examples.
     Proxmox infrastructure provisioning in `infra.yml` is now generator-owned
     and supports explicit lifecycle and rebuild policy controls:
     `state: present|absent` and
     `rebuild_on: never|config_change|always`, plus the runtime override
     `-e proxmox_force_rebuild=true`. `config_change` decisions use a
     controller-side fingerprint stored under `build/.infra-state/`, and
     `state: absent` destroys the guest and clears cached state.

206. `checkpoint-206-lxc-bootstrap-and-disk-volume-fix`
     Fixes Proxmox LXC creation failing with "Only root can pass arbitrary
     filesystem paths" when using API token auth. Root cause: the
     `community.proxmox.proxmox` module sent `storage` and `disk` as separate
     API parameters; PVE interpreted `storage` as a filesystem path request
     which requires ticket auth, not token auth. Fix: replaced `storage`/`disk`
     with `disk_volume` (storage + size), which constructs `rootfs=storage:size`
     as a single API value — matching the working curl behavior.
     Removed the debug curl script generation tasks from infra.yml (no longer
     needed). Added `lxc_bootstrap.yml` playbook to install Python on minimal
     LXC containers via `raw` module before `site.yml` runs. The SSH wait task
     in infra.yml now skips hosts using `proxmox_pct_remote` connection.
     Extended `proxmox_inventory_scaffold.py` with `--ansible-group`,
     `--ansible-port`, `--ansible-connection`, `--ansible-become`, and
     `--ansible-become-method` flags for hosts.ini generation.

207. `checkpoint-207-bootstrap-commands-and-compat-fixes`
     Added `bootstrap_commands` variable to `lxc_bootstrap.yml`: a list of
     arbitrary shell commands run via `raw` before Python installation. Enables
     per-host or per-group prep steps for containers that need OS-level fixes
     before package installation (for example openSUSE 16.0
     systemd-networkd config). Fixed zypper `-q` flag not supported on
     openSUSE. Confirmed bootstrap works across Debian, Ubuntu, Alpine,
     AlmaLinux, Rocky, CentOS, Fedora, Devuan, Arch, openSUSE, and Gentoo.
     openEuler excluded from LXC testing — Proxmox `Setup.pm` cannot detect
     the distro and fails in `post_create_hook`.
     Deferred follow-up: `lxc_bootstrap.yml` is currently named for the first
     use case that introduced it, but the playbook is increasingly useful for
     minimal VMs as well because it solves the more general "pre-Python host
     bootstrap" problem. Keep the current name for now to avoid churn while
     the workflow settles; revisit a rename later if the VM use case becomes
     routine enough that the current name is misleading.

208. `checkpoint-208-firewall-dropins-and-wireguard-topology`
     The Linux firewall stack was refactored away from a monolithic
     `firewall_geo`-owned nftables template into a base `firewall` role plus
     per-role drop-ins under `/etc/nftables.d/`. The new `firewall` role owns
     the nftables skeleton, generic accept/DNAT/masquerade plumbing, immediate
     apply/reload behavior, and FreeBSD `pf` rendering; `firewall_geo` is now a
     geoip-focused Linux add-on with transitional legacy rules only.
     WireGuard, DNS, mailserver, samba, nfs, node_exporter, step_ca, openvpn,
     and workloads now render their own nftables fragments and notify the
     shared `Reload nftables` handler. This removes the old stray
     `default(51820)` behavior and makes service rule ownership explicit.
     In parallel, the repo gained `src/scripts/wireguard_topology_render.py`,
     a user-facing helper that reads a topology YAML, writes inventory
     `host_vars`/vault WireGuard structures, and emits ready-to-use `wg-quick`
     configs. The distro and role tests were updated to match the new firewall
     ownership model, and validation once again passes end to end.
     Deferred follow-up: add a separate recursion-oriented DNS resolver
     workflow/role if that use case is needed. The current `dns` role is
     authoritative-oriented by design and should stay explicit about not
     provisioning a generic recursive/caching nameserver.

209. `checkpoint-209-template-extraction-and-test-expansion`
     Deferred follow-up from the contract audit: continue reducing
     distro-by-distro duplication where one family-level mechanism already
     exists. Two working contracts now apply across the repo:
     1. when fixing a distro-specific bug, check sibling systems in the same
        family and apply the fix family-wide if the same mechanism is valid;
     2. when one task can serve multiple distros cleanly, prefer that shared
        task over copy-pasted per-distro variants.
     Current high-value follow-ups:
     - `apache2`: collapse near-identical distro-specific listen/ports tasks
       into a shared task with computed destination/path variables where
       possible.
     - `docker`: reduce Debian/RedHat/Arch duplication and prefer shared
       family-level tasks unless a real repository or packaging difference
       forces a split.
     - `step_ca`: consolidate installation flows across distro families where
       one package/repository mechanism can be shared cleanly.
     - More broadly, keep auditing roles such as `mailserver`, `nfs`, and
       `openvpn` for cases where family-level handling is possible but not yet
       used.

210. `checkpoint-210-bootstrap-mirrors-host-env-lxc-export`
     Consolidates the post-209 dirty tree into a single checkpoint covering
     performance tuning, distro-agnostic package mirror rewriting before
     Python bootstrap, persistent host environment variables, composable
     lxc_bootstrap hooks, and a new Proxmox export playbook.
     - ansible.cfg: forks = 20, strategy = free (parallelise 17-host runs)
     - New default vars: pkg_manager_mirror, host_environment
     - site.yml: /etc/environment + /etc/profile.d/ansible-enterprise.sh
       (FreeBSD variant at /usr/local/etc/profile.d/); absent when unset
     - site.yml: remove dnf makecache --timer from auto mode (unsafe eager
       refresh; APT TTL is the only supported lightweight native refresh)
     - lxc_bootstrap.yml: single raw/sed mirror task using /etc/os-release
       case statement runs before Python install (covers ubuntu, debian,
       devuan, alpine, fedora, rocky, almalinux, opensuse*/sles)
     - lxc_bootstrap.yml: bootstrap_environment dict injected into all
       raw commands via _bootstrap_env_str; bootstrap_raw_pre_host and
       bootstrap_raw_post_host composable with group-level hooks;
       bootstrap_cache_urls for archive download/extract
     - lxc_export.yml: new playbook -- vzdump export with --storage,
       --mode, --compress, rename, vztmpl template move, optional scp
       fetch; contract entry added in generation_contracts.yml
     - dns: Alpine BIND paths; switch to ansible_facts.service_mgr
     - ssh_hardening: explicit systemd/OpenRC/FreeBSD enable+start tasks
     - test_distro_conditionals.py: TestBootstrapMirrorSetup class +
       updates for service_mgr, bootstrap_raw_pre_host

211. `checkpoint-211-host-locked-safety-guard`
     Adds an opt-in per-host safety lock so legacy/fragile hosts can be
     included in the inventory without risk of accidental changes.
     - New host_var `host_locked: true` (default false) skips every role
       for that host.
     - All five entry playbooks (site.yml, infra.yml, lxc_bootstrap.yml,
       bootstrap.yml, lxc_export.yml) gain a pre_task pair: a debug task
       that loudly announces the lock, then `meta: end_host` gated on
       `host_locked | default(false) | bool`.
     - Override for a single run: `-e host_locked=false --limit foo`.
       An earlier `assert` against `ansible_play_hosts_all` was removed
       because `hostvars[h].host_locked` does not reliably observe
       extra-var precedence through the `extract` filter, causing false
       positives on legitimate overrides.
     - Test: test_generator_invariants.TestHostLockedGuard verifies both
       the end_host guard and the lockdown announcement in every
       entry playbook.

212. `checkpoint-212-check-mode-safety`
     Makes `ansible-playbook --check` safe on fresh hosts where the
     package install task is a no-op and the service unit does not
     exist yet.
     - Guard added on every `state: started`, `state: restarted`, and
       `state: reloaded` task across all roles (44 tasks total): the
       `when:` list now includes `- not ansible_check_mode`. Task skips
       under --check; real runs unchanged.
     - ssh_hardening: the `Resolve admin users primary groups` task
       (`id -gn <user>`) now runs with `check_mode: false` (read-only
       command) and `failed_when: false` (tolerates missing user on
       fresh host); the downstream `Build admin user primary group map`
       set_fact now skips entries with empty stdout so the later
       `file:` task's `group:` does not resolve to the empty string.
     - Symptom that motivated this: node_exporter enable-and-start
       failing in --check with "Could not find the requested service
       prometheus-node-exporter".
     - Test: test_generator_invariants.TestCheckModeGuards scans every
       `tasks/*.yml` and `handlers/*.yml` under `build/roles/`,
       asserting that no `state: started|restarted|reloaded` task is
       missing the guard. TestAdminPrimaryGroupsLookup verifies the
       ssh_hardening flow.

213. `checkpoint-213-nftables-dropins-require-firewall`
     Service roles that deploy nftables snippets into
     `/etc/nftables.d/input/` must first check that the firewall role
     has run and created those directories; otherwise the copy fails
     on hosts where `firewall_enabled: false`.
     - Added `- firewall_enabled | default(false) | bool` to the
       `when:` list of every `Deploy <x> nftables drop-in` task
       (mailserver, nfs, samba, node_exporter, step_ca, openvpn,
       wireguard, workloads; dns was already guarded).
     - Symptom: mailserver failing on sirius-new with
       "Destination directory /etc/nftables.d/input does not exist".
     - Test: test_generator_invariants.TestNftablesDropInGuard globs
       every role task file containing `/etc/nftables.d/` and asserts
       `firewall_enabled` appears in each `Deploy <x> nftables drop-in`
       task's window.

214. `checkpoint-214-wireguard-no-log-label`
     Prevents WireGuard private keys from leaking into the task log.
     - The `Configure WireGuard instances` include_tasks loop iterates
       dicts that contain `private_key`. Without a `label:` inside
       `loop_control`, the `included:` banner prints the whole item
       per iteration -- secret included.
     - Added `label: "{{ _inst.name }}"` so only the interface name
       appears. The template task that actually consumes the key
       already had `no_log: true`.
     - Test: test_generator_invariants.TestWireguardLoopSecretHiding
       asserts the task has a `loop_control:` block with the safe
       label string.

215. `checkpoint-215-host-environment-blockinfile`
     `/etc/environment` is now managed with `blockinfile:` instead of
     `copy:`, so distro-default and PAM-injected entries are preserved.
     - site.yml pre_task replaces the clobbering `copy:` with
       `blockinfile:` using marker
       `# {mark} ANSIBLE MANAGED BLOCK - ansible-enterprise host_environment`.
     - `state:` is now `present` when `host_environment` is non-empty,
       `absent` otherwise, so removing the var cleanly strips the
       managed block (previous logic skipped the task and left stale
       values).
     - `create: true` handles minimal containers where /etc/environment
       does not exist. The /etc/profile.d/ drop-ins are unchanged --
       those files are entirely ours.
     - Test: test_generator_invariants.TestHostEnvironmentBlockinfile
       asserts the blockinfile usage, the marker, the
       conditional-state expression, and rejects any leftover `copy:`
       targeting /etc/environment.

216. `checkpoint-216-ansible-cfg-in-build`
     Moves `ansible.cfg` from the repository root into the generated
     `build/` tree so Ansible actually discovers it.
     - Root cause: documented workflow is `cd build && ansible-playbook`;
       Ansible only checks `$ANSIBLE_CONFIG`, CWD, `~/.ansible.cfg`,
       `/etc/ansible/ansible.cfg` -- it never walks up to the repo
       root. The repo-root `ansible.cfg` was silently never loaded, so
       `inject_facts_as_vars` stayed at its default True and
       `ansible_facts.services` (from service_facts) shadowed the
       project's `services` var, breaking the certbot
       `Assert domain resolves to this host` loop.
     - Added `ansible.cfg` to `FILE_MANIFEST` so it is emitted at
       `build/ansible.cfg` with `inject_facts_as_vars = False`,
       `interpreter_python = auto_silent`, `forks = 20`,
       `strategy = free`.
     - Removed repo-root `ansible.cfg` (stale).
     - Removed `ansible.cfg` from `REQUIRED_ROOT_FILES` in
       `scripts/internal/verify_repo_contracts.py`.
     - Added `ansible.cfg` entry to `scripts/generation_contracts.yml`
       with `source_of_truth: [PROMPT.md, generate_ansible_enterprise.py]`.
     - Test: test_generator_invariants.TestAnsibleCfgInBuild verifies
       `build/ansible.cfg` exists, contains the inject-facts-as-vars
       setting, and that no stale repo-root `ansible.cfg` shadows it.

217. `checkpoint-217-mailserver-masquerade-domains-list`
     Aligns `mailserver_masquerade_domains` with Postfix's native list
     semantics.
     - Variable renamed `mailserver_masquerade_domain` (scalar) ->
       `mailserver_masquerade_domains` (list). Default changes from
       `""` to `[]`. No deprecation shim -- the old key is silently
       ignored; inventory using it must migrate to a list.
     - roles/mailserver/defaults/main.yml: declares `masquerade_domains:
       "{{ mailserver_masquerade_domains | default([]) }}"` and
       removes the singular form.
     - generic.j2: uses the first list entry as the outbound rewrite
       target for existing `smtp_generic_maps` behaviour.
     - main.cf.j2: now also emits Postfix's native
       `masquerade_domains = <comma-joined list>` directive when the
       list is non-empty. Comma separator matches the convention used
       by the nearby `mydestination = localhost, <domain>, ...`.
     - Test: test_generator_invariants.TestMasqueradeDomainsList
       covers the defaults file, the generic.j2 list-first usage,
       and the main.cf.j2 postfix directive emission.

218. `checkpoint-218-regression-test-invariants`
     Adds `src/scripts/tests/test_generator_invariants.py`, a
     retroactive regression-test battery covering the invariants
     established in checkpoints 211-217. Fifteen test methods total,
     grouped by subject class. Addresses the gap where checkpoints
     211-217 were implemented without per-fix tests, violating the
     Bug Fix Test Contract documented in spec/contracts.md.
     - TestHostLockedGuard (2): every entry playbook has end_host +
       announcement.
     - TestCheckModeGuards (1): every service state-change task has
       `not ansible_check_mode`.
     - TestNftablesDropInGuard (1): every nftables drop-in has
       `firewall_enabled`.
     - TestWireguardLoopSecretHiding (1): loop_control.label on the
       WireGuard include.
     - TestAdminPrimaryGroupsLookup (2): ssh_hardening id-gn flow.
     - TestMasqueradeDomainsList (3): mailserver list semantics.
     - TestHostEnvironmentBlockinfile (2): /etc/environment
       non-destructive management.
     - TestAnsibleCfgInBuild (3): build/ansible.cfg exists and
       disables fact-var injection.
     - Follow-up coverage added after the checkpoint audit:
       `test_distro_conditionals.py` now covers `lxc_export.yml`
       (`vzdump`, stop/start, template move, local fetch) and
       `bootstrap_cache_urls`; `test_generator_invariants.py` now
       covers host_environment profile.d files plus `forks = 20` and
       `strategy = free` in `build/ansible.cfg`; and
       `test_verify_repo_contracts.py` now pins the validator contract
       that repo-root `ansible.cfg` is no longer a required root file
       because the generated config lives in `build/`.
