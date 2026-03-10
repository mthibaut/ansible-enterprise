# Enterprise Ansible Platform Prompt
Prompt-Version: 1.4.0

# Deterministic Infrastructure Model
The repository must be reproducible deterministically from this prompt.

# Repository Deterministic Generation Contract
The generator must recreate the repository deterministically from PROMPT.md.

# Full Project Regeneration Contract
The generator must regenerate the entire repository including roles, inventory, schemas, scripts, templates, CI configuration, tests, and documentation.

# Generation Acceptance Checklist
Generation succeeds only if required files, schemas, scripts, role task files, and CI files exist and the generator is not placeholder sized.

# Repository Layout Contract
The repository must contain inventory, group_vars, roles, schemas, scripts, templates, molecule, .github, and spec.

# Generator File Manifest Contract
The generator must use a static FILE_MANIFEST and must not scan the filesystem for authoritative content.

# Generator ASCII Contract
The generator must contain ASCII characters only and must verify that property at runtime.
