# CLAUDE.md - ansible-enterprise

This repository is written and maintained by Claude. These rules are binding
for every session. Read the contract files below BEFORE changing anything.

## Read first

| File | Governs |
|---|---|
| `src/spec/contracts.md` | repository contracts: generated-file protection, lockstep generation, trust zones, manifest, generation contracts, Bug Fix Test Contract, Local Configuration Scrub Contract |
| `src/spec/ai-development-mode.md` | trust zones and rules for AI contributors, required validation |
| `src/PROMPT.md` | architectural source of truth; spec first, then generator |
| `src/spec/architecture.md`, `src/spec/generator.md`, `src/spec/roles.md`, `src/spec/services.md` | design the generator implements |
| `src/spec/checkpoints.md` | numbered change log; every change gets the next checkpoint |
| `src/scripts/generation_contracts.yml` | per-file generation contracts checked by the verifier |

## Where things live

- `src/generate_ansible_enterprise.py` writes ONLY `build/` (from `FILE_MANIFEST`).
  `build/` is gitignored and must never be edited by hand.
- Files in `src/spec/` and `src/scripts/` are edited directly. Some still carry
  a stale "GENERATED FILE - DO NOT EDIT" header; the generator does not write them.
- Repo-root files (`README.md`, `Makefile`, `CLAUDE.md`, `docs/`) are free zone.

## Rules

1. Every change needs a test in `src/scripts/tests/` (`test_<role>.py` for role
   structure/ordering, `test_<script>.py` for scripts) - not only bug fixes.
   Write the test first.
2. Change order: spec (`PROMPT.md` / `src/spec/*`) -> test -> generator ->
   `src/scripts/generation_contracts.yml` for new generated files ->
   checkpoint entry in `src/spec/checkpoints.md` (contiguous numbering).
3. Never put real local identifiers (hostnames, LAN IPs, domains, token names)
   in committed files. Use `example.com`, `example.internal`, `192.0.2.0/24`.
   The verifier enforces this with the denylist at
   `../.ansible-enterprise-local-config-patterns.yml`.
4. The generator must stay ASCII-only. Keep this file ASCII-only too.
5. Before scripted edits of the generator: copy it aside first. For pure
   refactors, `make generate` must leave `src/.generator.lock.yml` unchanged
   (it hashes generator source and output). `src/.prompt.version` is a counter
   bumped on every generate run.
6. Do not commit to `main` unless asked; never push unless asked.

## Validate after every change

```bash
make all          # generate + verify_repo_contracts
make test         # unit tests
make checkpoints  # checkpoint numbering
make services     # services schema
```
