<!--
GENERATED FILE - DO NOT EDIT
This file is overwritten by generate_ansible_enterprise.py.
Source of truth: PROMPT.md.
Manual edits will be lost on the next regeneration.
-->

# Architecture

This project uses a deterministic generation model.

`PROMPT.md` defines the high-level contract. `generate_ansible_enterprise.py`
materialises the managed repository tree from `FILE_MANIFEST`.

## Orchestration model

The runtime is role-driven. `site.yml` runs a fixed ordered list of roles.
Roles are conditionally included based on flags (`geoip.enabled`,
`mailserver.enabled`, `services.nextcloud.enabled`) and on the
`_required_providers` list produced by the `resolve_capabilities` pre-task.

The `capabilities` dict in `group_vars/all/main.yml` maps capability names
to the provider roles that satisfy them. At runtime, `resolve_capabilities`
iterates enabled services, resolves each `requires` entry through the
`capabilities` dict, and registers `_required_providers` as a sorted list
of provider role names. Roles that need service-driven activation check
`'rolename' in _required_providers`.

Currently wired:
- `requires: [mail]` activates the `mailserver` role and opens mail ports
- `requires: [bind]` contributes to the DNS role activation condition
- `requires: [maxmind_nftables]` contributes to the geoip role condition

CI enforces via `verify_capability_contracts()` that every `requires` entry
in the services dict names a known key in `capabilities`.

The existing `when:` guards in `site.yml` remain as the primary mechanism.
They combine flag-based conditions with `_required_providers` checks.

## Service-driven behaviour

The `services` dict in `group_vars/all/main.yml` is the source of truth for
application-level configuration. It currently drives:

- **nginx**: `render_service.yml` loops over `services`, selects a vhost
  template per service type, and renders one vhost config per enabled service.
  This is genuinely service-driven.
- **DNS**: `roles/dns/tasks/main.yml` derives `_effective_dns_zones` from
  `dns_hidden_primary_zones` plus any enabled service domain not already
  covered by a declared zone (apex match or subdomain). Zones are created
  and registered in `named.conf.local` automatically. (checkpoint-047)

The following are not yet fully service-driven:

- **firewall**: HTTP/HTTPS and DNS port rules derive from `services`, while
  mail ports are opened by the mailserver role when that role is active.
  The mailserver role can be activated directly with `mailserver.enabled` or
  indirectly through `requires: [mail]` capability resolution.
- **application deployment**: nextcloud and mailserver are conditionally
  included roles, not service-dispatched deployments.

Future work: make role activation rely solely on capability resolution once
legacy flag compatibility is no longer needed.

## Capabilities provider-dispatch

The `capabilities` dict maps capability names to provider role names.
Services declare what they need via a `requires:` list; `resolve_capabilities`
translates those declarations into `_required_providers` at play time.

**Implemented (checkpoint-050):**
- `resolve_capabilities` pre-task in `site.yml` produces `_required_providers`
- `verify_capability_contracts()` in CI: every `requires` value must be a
  known key in `capabilities`
- `requires: [mail]` correctly activates mailserver and mail firewall ports
- `requires: [bind]` and `requires: [maxmind_nftables]` contribute to their
  respective role activation conditions

**Not yet fully service-driven:**
- `mailserver.enabled` remains a backwards-compatible activation path in
  addition to `_required_providers`
- Application roles (nextcloud, mailserver) remain conditionally-included
  roles, not capability-dispatched deployments
- There is no schema enforcement that a service `requires` only capabilities
  its declared `app.type` legitimately needs

**Future work:**
- Derive all role activation solely from `_required_providers`, retiring the
  parallel flag-based conditions
- Enforce `requires` schema per `app.type` in the services JSON schema

## Generation model

The generator enforces lockstep generation. The `.generator.lock.yml` file
records source and output hashes. CI verifies that the committed tree exactly
matches a fresh regeneration.

## Trust zones

Three zones govern file ownership:

1. Immutable Generated Zone - files written by the generator, never hand-edited
2. Protected Logic Zone - critical infrastructure roles + verifier scripts
3. Free Development Zone - documentation, spec files, helper scripts
