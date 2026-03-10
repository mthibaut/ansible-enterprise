#!/usr/bin/env python3
from pathlib import Path
root = Path(__file__).resolve().parents[1]
required = [
    'PROMPT.md','.gitignore','README.md','generate_ansible_enterprise.py','requirements.yml','site.yml',
    'inventory/hosts.ini.example','inventory/pull.ini','group_vars/all/main.yml','group_vars/all/vault.yml.example',
    'schemas/services.schema.json','scripts/bootstrap_pull_host.sh','scripts/validate_services_schema.py',
    'scripts/resolve_service_order.py','.github/workflows/ci.yml','.gitlab-ci.yml',
    'molecule/default/molecule.yml','molecule/default/converge.yml','molecule/default/verify.yml'
]
missing = [p for p in required if not (root / p).exists()]
if missing: raise SystemExit('Missing required files\n' + '\n'.join(missing))
for role in ['common','preflight','ssh_hardening','firewall_geo','geoip','dns','nginx','users','nextcloud','mailserver']:
    if not (root / 'roles' / role / 'tasks' / 'main.yml').exists(): raise SystemExit('Missing role task file for ' + role)
print('repository contracts verified successfully')
