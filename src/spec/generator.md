<!--
GENERATED FILE - DO NOT EDIT
This file is overwritten by generate_ansible_enterprise.py.
Source of truth: PROMPT.md.
Manual edits will be lost on the next regeneration.
-->

# Generator

The generator owns the managed repository tree through `FILE_MANIFEST`.

## Workflow

1. Read `PROMPT.md` and validate required sections
2. Materialize all files from `FILE_MANIFEST` with appropriate notice headers
3. Apply trust-zone headers: GENERATED FILE or PROTECTED IMPLEMENTATION FILE
4. Write `.generator.lock.yml` (source hash + output hash + file lists)
5. Update `.prompt.sha256` and `.prompt.version`

## Manifest Structure

`FILE_MANIFEST: Dict[str, str]` maps relative paths to file contents.
The generator adds notice headers via `apply_notice()`.

## Trust Zones

- `PROTECTED_FILES` - files that get PROTECTED IMPLEMENTATION FILE header
  (critical infrastructure: firewall, mailserver, nextcloud, verifier, resolver)
- All other manifest files get GENERATED FILE - DO NOT EDIT header

## Verifier

`scripts/verify_repo_contracts.py` imports the generator module and checks:

- Required files exist
- Generated files contain correct headers
- Protected files contain PROTECTED IMPLEMENTATION FILE header
- Protected role file-count minimums are met
- `scripts/generation_contracts.yml` references only manifest paths
- `.generator.lock.yml` matches current source/output hashes
- Regenerated tree matches committed tree exactly (drift detection)

## Running

```bash
python3 generate_ansible_enterprise.py
python3 scripts/verify_repo_contracts.py
```
