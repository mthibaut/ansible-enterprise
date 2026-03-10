#!/usr/bin/env python3
from __future__ import annotations
import hashlib, pathlib, re, shutil
from typing import Dict
with open(__file__, "r", encoding="utf-8") as f:
    f.read().encode("ascii")
ROOT = pathlib.Path(__file__).resolve().parent
PROMPT = ROOT / "PROMPT.md"
HASH_FILE = ROOT / ".prompt.sha256"
VERSION_FILE = ROOT / ".prompt.version"
STAGING_DIR = ROOT / ".regen-staging"
REQUIRED_PROMPT_SECTIONS = ["Deterministic Infrastructure Model","Repository Deterministic Generation Contract","Full Project Regeneration Contract","Generation Acceptance Checklist","Repository Layout Contract","Generator ASCII Contract"]
REQUIRED_OUTPUT_FILES = ['PROMPT.md',
 '.gitignore',
 'README.md',
 'generate_ansible_enterprise.py',
 'requirements.yml',
 'site.yml',
 'inventory/hosts.ini.example',
 'inventory/pull.ini',
 'group_vars/all/main.yml',
 'group_vars/all/vault.yml.example',
 'schemas/services.schema.json',
 'scripts/bootstrap_pull_host.sh',
 'scripts/validate_services_schema.py',
 'scripts/resolve_service_order.py',
 'scripts/verify_repo_contracts.py',
 '.github/workflows/ci.yml',
 '.gitlab-ci.yml',
 'molecule/default/molecule.yml',
 'molecule/default/converge.yml',
 'molecule/default/verify.yml',
 'roles/common/tasks/main.yml',
 'roles/preflight/tasks/main.yml',
 'roles/ssh_hardening/tasks/main.yml',
 'roles/firewall_geo/tasks/main.yml',
 'roles/geoip/tasks/main.yml',
 'roles/dns/tasks/main.yml',
 'roles/nginx/tasks/main.yml',
 'roles/users/tasks/main.yml',
 'roles/nextcloud/tasks/main.yml',
 'roles/mailserver/tasks/main.yml']
ROLE_DIRS = ["common","preflight","ssh_hardening","firewall_geo","geoip","dns","nginx","users","nextcloud","mailserver"]
FILE_MANIFEST: Dict[str, str] = {'.github/workflows/ci.yml': 'name: CI\n'
                             'on:\n'
                             '  push:\n'
                             '  pull_request:\n'
                             'jobs:\n'
                             '  validate:\n'
                             '    runs-on: ubuntu-latest\n'
                             '    steps:\n'
                             '      - uses: actions/checkout@v4\n'
                             '      - run: python3 scripts/verify_repo_contracts.py\n',
 '.gitignore': 'group_vars/all/vault.yml\n'
               '*.private\n'
               '*.key\n'
               '*.pem\n'
               '__pycache__/\n'
               '*.pyc\n'
               '.regen-staging/\n',
 '.gitlab-ci.yml': 'stages:\n'
                   '  - validate\n'
                   '\n'
                   'validate:\n'
                   '  image: python:3.11\n'
                   '  script:\n'
                   '    - python scripts/verify_repo_contracts.py\n',
 'README.md': '# Enterprise Ansible Platform\n',
 'group_vars/all/main.yml': '---\n'
                            'ssh_port: 22\n'
                            'admin_users: [myadmin]\n'
                            'admin_ssh_public_key: ""\n'
                            'capabilities:\n'
                            '  tls: {provider: nginx}\n'
                            '  reverse_proxy: {provider: nginx}\n'
                            '  dns: {provider: bind}\n'
                            '  database: {provider: mariadb}\n'
                            '  firewall: {provider: nftables}\n'
                            '  geoip: {provider: maxmind_nftables}\n'
                            'geoip:\n'
                            '  enabled: false\n'
                            '  license_key: ""\n'
                            '  download_dir: /var/lib/geoip\n'
                            '  sets_dir: /etc/nftables.d/geoip\n'
                            '  allowed_countries: []\n'
                            'dns_hidden_primary_zones: []\n'
                            'dns_secondaries: []\n'
                            'dns_admin_ip: ""\n'
                            'mailserver:\n'
                            '  enabled: false\n'
                            '  domain: mail.example.com\n'
                            '  admin_mail_user: mailadmin\n'
                            '  admin_mail_password: ""\n'
                            '  masquerading_enabled: false\n'
                            '  masquerade_domain: ""\n'
                            '  masquerade_users: []\n'
                            '  masquerade_hosts: []\n'
                            "nextcloud_version: '29.0.6'\n"
                            'services: {}\n',
 'group_vars/all/vault.yml.example': '---\n'
                                     'ssh_port: 49222\n'
                                     'admin_users: [myadmin]\n'
                                     'admin_ssh_public_key: "ssh-ed25519 AAAAEXAMPLE"\n',
 'inventory/group_vars/.gitkeep': '',
 'inventory/host_vars/.gitkeep': '',
 'inventory/hosts.ini.example': '[all]\nserver1 ansible_host=192.0.2.1 ansible_user=root\n',
 'inventory/pull.ini': '[all]\nlocalhost ansible_connection=local\n',
 'molecule/default/converge.yml': '---\n'
                                  '- name: Converge\n'
                                  '  hosts: all\n'
                                  '  become: true\n'
                                  '  vars:\n'
                                  '    admin_users: [myadmin]\n'
                                  '    admin_ssh_public_key: "ssh-ed25519 AAAATESTKEY"\n'
                                  '  roles:\n'
                                  '    - common\n'
                                  '    - ssh_hardening\n',
 'molecule/default/molecule.yml': '---\n'
                                  'dependency:\n'
                                  '  name: galaxy\n'
                                  'driver:\n'
                                  '  name: docker\n'
                                  'platforms:\n'
                                  '  - name: debian12\n'
                                  '    image: geerlingguy/docker-debian12-ansible\n'
                                  'provisioner:\n'
                                  '  name: ansible\n'
                                  'verifier:\n'
                                  '  name: ansible\n',
 'molecule/default/verify.yml': '---\n'
                                '- name: Verify\n'
                                '  hosts: all\n'
                                '  become: true\n'
                                '  tasks:\n'
                                '    - name: Check sshd_config exists\n'
                                '      stat:\n'
                                '        path: /etc/ssh/sshd_config\n'
                                '      register: sshd\n'
                                '    - assert:\n'
                                '        that:\n'
                                '          - sshd.stat.exists\n'
                                '        fail_msg: "/etc/ssh/sshd_config is missing"\n',
 'requirements.yml': '---\n'
                     'collections:\n'
                     '  - name: community.general\n'
                     '  - name: ansible.posix\n'
                     '  - name: community.crypto\n'
                     '  - name: community.mysql\n',
 'roles/common/tasks/main.yml': '---\n'
                                '- name: Assert core variables are shaped correctly\n'
                                '  assert:\n'
                                '    that:\n'
                                '      - admin_users is iterable\n'
                                '      - services is mapping\n',
 'roles/dns/files/update_dns_serial.py': '#!/usr/bin/env python3\nprint("dns serial helper")\n',
 'roles/dns/handlers/main.yml': '---\n'
                                '- name: Restart DNS\n'
                                '  service:\n'
                                '    name: bind9\n'
                                '    state: restarted\n',
 'roles/dns/tasks/main.yml': "---\n- name: Placeholder for dns\n  debug:\n    msg: 'dns'\n",
 'roles/dns/templates/named.conf.local.j2': 'acl secondaries { };\n',
 'roles/dns/templates/zone.db.j2': '$TTL 86400\n',
 'roles/firewall_geo/handlers/main.yml': '---\n'
                                         '- name: Reload nftables\n'
                                         '  command: nft -f /etc/nftables.conf\n',
 'roles/firewall_geo/tasks/main.yml': '---\n'
                                      '- name: Placeholder for firewall_geo\n'
                                      '  debug:\n'
                                      "    msg: 'firewall_geo'\n",
 'roles/firewall_geo/templates/nftables.conf.j2': 'flush ruleset\n',
 'roles/geoip/files/geoip_ingest.py': '',
 'roles/geoip/tasks/main.yml': "---\n- name: Placeholder for geoip\n  debug:\n    msg: 'geoip'\n",
 'roles/mailserver/handlers/main.yml': '',
 'roles/mailserver/tasks/main.yml': '---\n'
                                    '- name: Placeholder for mailserver\n'
                                    '  debug:\n'
                                    "    msg: 'mailserver'\n",
 'roles/mailserver/templates/10-mail.conf.j2': '',
 'roles/mailserver/templates/10-master.conf.j2': '',
 'roles/mailserver/templates/KeyTable.j2': '',
 'roles/mailserver/templates/SigningTable.j2': '',
 'roles/mailserver/templates/TrustedHosts.j2': '',
 'roles/mailserver/templates/generic.j2': '',
 'roles/mailserver/templates/main.cf.j2': '',
 'roles/mailserver/templates/opendkim.conf.j2': '',
 'roles/nextcloud/tasks/main.yml': '---\n'
                                   '- name: Placeholder for nextcloud\n'
                                   '  debug:\n'
                                   "    msg: 'nextcloud'\n",
 'roles/nginx/handlers/main.yml': '---\n'
                                  '- name: Reload nginx\n'
                                  '  service:\n'
                                  '    name: nginx\n'
                                  '    state: reloaded\n',
 'roles/nginx/tasks/main.yml': "---\n- name: Placeholder for nginx\n  debug:\n    msg: 'nginx'\n",
 'roles/nginx/tasks/render_service.yml': '---\n- debug:\n    msg: render service\n',
 'roles/nginx/templates/client_cert_site.conf.j2': 'server { listen 80; }\n',
 'roles/nginx/templates/nginx.conf.j2': 'events {}\nhttp { include /etc/nginx/conf.d/*.conf; }\n',
 'roles/nginx/templates/site.conf.j2': 'server { listen 80; }\n',
 'roles/preflight/tasks/main.yml': '---\n'
                                   '- name: Validate services schema\n'
                                   '  command: python3 scripts/validate_services_schema.py\n'
                                   '  args:\n'
                                   '    chdir: "{{ playbook_dir }}"\n'
                                   '- name: Ensure admin SSH key is populated\n'
                                   '  assert:\n'
                                   '    that:\n'
                                   '      - admin_ssh_public_key is defined\n'
                                   '      - admin_ssh_public_key | length > 20\n'
                                   '    fail_msg: "admin_ssh_public_key must be set to a real '
                                   'public key"\n',
 'roles/ssh_hardening/handlers/main.yml': '---\n'
                                          '- name: Restart SSH\n'
                                          '  service:\n'
                                          '    name: ssh\n'
                                          '    state: restarted\n',
 'roles/ssh_hardening/tasks/main.yml': '---\n'
                                       '- name: Install OpenSSH server\n'
                                       '  package:\n'
                                       '    name: openssh-server\n'
                                       '    state: present\n'
                                       '- name: Ensure admin users exist\n'
                                       '  user:\n'
                                       '    name: "{{ item }}"\n'
                                       '    shell: /bin/bash\n'
                                       '    state: present\n'
                                       '  loop: "{{ admin_users }}"\n'
                                       '- name: Deploy sshd_config\n'
                                       '  template:\n'
                                       '    src: sshd_config.j2\n'
                                       '    dest: /etc/ssh/sshd_config\n'
                                       '    mode: "0600"\n'
                                       '    validate: "sshd -t -f %s"\n'
                                       '  notify: Restart SSH\n'
                                       '- meta: flush_handlers\n'
                                       '- name: Deploy admin SSH keys\n'
                                       '  ansible.posix.authorized_key:\n'
                                       '    user: "{{ item }}"\n'
                                       '    key: "{{ admin_ssh_public_key }}"\n'
                                       '  loop: "{{ admin_users }}"\n'
                                       '  when: admin_ssh_public_key | length > 0\n',
 'roles/ssh_hardening/templates/sshd_config.j2': 'Port {{ ssh_port }}\n'
                                                 'PasswordAuthentication no\n'
                                                 'PubkeyAuthentication yes\n'
                                                 'UsePAM yes\n'
                                                 'AllowUsers {{ admin_users | join(" ") }}\n',
 'roles/users/tasks/main.yml': "---\n- name: Placeholder for users\n  debug:\n    msg: 'users'\n",
 'schemas/services.schema.json': '{\n'
                                 '  "$schema": "http://json-schema.org/draft-07/schema#",\n'
                                 '  "type": "object"\n'
                                 '}\n',
 'scripts/bootstrap_pull_host.sh': '#!/usr/bin/env bash\n'
                                   'set -euo pipefail\n'
                                   '[ -f requirements.yml ] || { echo "requirements.yml missing"; '
                                   'exit 1; }\n'
                                   'ansible-galaxy collection install -r requirements.yml\n'
                                   'ansible-pull -i inventory/pull.ini site.yml\n',
 'scripts/resolve_service_order.py': '#!/usr/bin/env python3\n'
                                     'import yaml\n'
                                     'from collections import defaultdict, deque\n'
                                     "data = yaml.safe_load(open('group_vars/all/main.yml')) or "
                                     '{}\n'
                                     "services = data.get('services', {})\n"
                                     'graph = defaultdict(list)\n'
                                     'in_degree = {name: 0 for name in services}\n'
                                     'for name, svc in services.items():\n'
                                     "    for dep in svc.get('depends_on', []):\n"
                                     '        if dep in services:\n'
                                     '            graph[dep].append(name)\n'
                                     '            in_degree[name] += 1\n'
                                     'queue = deque(sorted([name for name, degree in '
                                     'in_degree.items() if degree == 0]))\n'
                                     'order = []\n'
                                     'while queue:\n'
                                     '    node = queue.popleft(); order.append(node)\n'
                                     '    for nxt in sorted(graph[node]):\n'
                                     '        in_degree[nxt] -= 1\n'
                                     '        if in_degree[nxt] == 0: queue.append(nxt)\n'
                                     "if len(order) != len(services): raise SystemExit('dependency "
                                     "cycle detected')\n"
                                     'for name in order: print(name)\n',
 'scripts/validate_services_schema.py': '#!/usr/bin/env python3\n'
                                        'import json, yaml\n'
                                        'from jsonschema import validate\n'
                                        "schema = json.load(open('schemas/services.schema.json'))\n"
                                        "data = yaml.safe_load(open('group_vars/all/main.yml')) or "
                                        '{}\n'
                                        "validate(instance=data.get('services', {}), "
                                        'schema=schema)\n'
                                        "print('services schema validation passed')\n",
 'scripts/verify_repo_contracts.py': '#!/usr/bin/env python3\n'
                                     'from pathlib import Path\n'
                                     'root = Path(__file__).resolve().parents[1]\n'
                                     'required = [\n'
                                     '    '
                                     "'PROMPT.md','.gitignore','README.md','generate_ansible_enterprise.py','requirements.yml','site.yml',\n"
                                     '    '
                                     "'inventory/hosts.ini.example','inventory/pull.ini','group_vars/all/main.yml','group_vars/all/vault.yml.example',\n"
                                     '    '
                                     "'schemas/services.schema.json','scripts/bootstrap_pull_host.sh','scripts/validate_services_schema.py',\n"
                                     '    '
                                     "'scripts/resolve_service_order.py','.github/workflows/ci.yml','.gitlab-ci.yml',\n"
                                     '    '
                                     "'molecule/default/molecule.yml','molecule/default/converge.yml','molecule/default/verify.yml'\n"
                                     ']\n'
                                     'missing = [p for p in required if not (root / p).exists()]\n'
                                     "if missing: raise SystemExit('Missing required files\\n' + "
                                     "'\\n'.join(missing))\n"
                                     'for role in '
                                     "['common','preflight','ssh_hardening','firewall_geo','geoip','dns','nginx','users','nextcloud','mailserver']:\n"
                                     "    if not (root / 'roles' / role / 'tasks' / "
                                     "'main.yml').exists(): raise SystemExit('Missing role task "
                                     "file for ' + role)\n"
                                     "print('repository contracts verified successfully')\n",
 'site.yml': '---\n'
             '- name: Enterprise configuration\n'
             '  hosts: all\n'
             '  become: true\n'
             '\n'
             '  pre_tasks:\n'
             '    - name: Run preflight validation\n'
             '      include_role:\n'
             '        name: preflight\n'
             '\n'
             '  roles:\n'
             '    - role: common\n'
             '    - role: ssh_hardening\n'
             '    - role: geoip\n'
             '      when: geoip.enabled | default(false) | bool\n'
             '    - role: firewall_geo\n'
             '    - role: dns\n'
             '    - role: nginx\n'
             '    - role: users\n'
             '    - role: nextcloud\n'
             '      when:\n'
             '        - services.nextcloud is defined\n'
             '        - services.nextcloud.enabled | default(false) | bool\n'
             "        - services.nextcloud.app.type == 'nextcloud'\n"
             '    - role: mailserver\n'
             '      when: mailserver.enabled | default(false) | bool\n',
 'spec/architecture.md': '',
 'spec/contracts.md': '',
 'spec/generator.md': '',
 'spec/roles.md': '',
 'spec/services.md': '',
 'templates/bind/.gitkeep': '',
 'templates/dovecot/.gitkeep': '',
 'templates/nftables/.gitkeep': '',
 'templates/nginx/.gitkeep': '',
 'templates/postfix/.gitkeep': ''}
LAYOUT_DIRS = ["inventory/group_vars","inventory/host_vars","templates/nginx","templates/bind","templates/postfix","templates/dovecot","templates/nftables","spec"]
GENERATED_TOP_LEVEL_DIRS = ["inventory","group_vars","roles","schemas","scripts","templates","molecule",".github","spec"]
GENERATED_TOP_LEVEL_FILES = [".gitignore","README.md","requirements.yml","site.yml",".gitlab-ci.yml"]
def read_text(path: pathlib.Path) -> str: return path.read_text(encoding="utf-8")
def write_text(path: pathlib.Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.replace("\r\n","\n").replace("\r","\n"), encoding="utf-8")
    if path.suffix in {".py", ".sh"}: path.chmod(0o755)
def sha256_text(text: str) -> str: return hashlib.sha256(text.encode("utf-8")).hexdigest()
def parse_prompt_version(prompt_text: str) -> str:
    m = re.search(r"^Prompt-Version:\s*([0-9]+\.[0-9]+\.[0-9]+)\s*$", prompt_text, re.MULTILINE)
    if not m: raise SystemExit("PROMPT.md missing valid Prompt-Version")
    return m.group(1)
def version_tuple(version: str): return tuple(int(x) for x in version.split("."))
def verify_prompt(prompt_text: str) -> None:
    missing=[s for s in REQUIRED_PROMPT_SECTIONS if s not in prompt_text]
    if missing: raise SystemExit("PROMPT.md missing required sections\n"+"\n".join(missing))
def reconcile_prompt_change(prompt_text: str):
    prompt_version=parse_prompt_version(prompt_text)
    prompt_hash=sha256_text(prompt_text)
    old_hash=read_text(HASH_FILE).strip() if HASH_FILE.exists() else ""
    old_version=read_text(VERSION_FILE).strip() if VERSION_FILE.exists() else ""
    if old_version and version_tuple(prompt_version) < version_tuple(old_version):
        raise SystemExit("Prompt-Version "+prompt_version+" is older than repository version "+old_version)
    return prompt_version, prompt_hash, old_hash != prompt_hash
def clear_staging() -> None:
    if STAGING_DIR.exists(): shutil.rmtree(STAGING_DIR)
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
def materialize_manifest(base_dir: pathlib.Path) -> None:
    for rel in sorted(FILE_MANIFEST): write_text(base_dir/rel, FILE_MANIFEST[rel])
def verify_output(base_dir: pathlib.Path) -> None:
    missing=[rel for rel in REQUIRED_OUTPUT_FILES if not (base_dir/rel).exists()]
    if missing: raise SystemExit("Missing required files\n"+"\n".join(missing))
    for role in ROLE_DIRS:
        if not (base_dir/'roles'/role/'tasks'/'main.yml').exists(): raise SystemExit("Missing role tasks/main.yml for "+role)
def verify_generation_acceptance(base_dir: pathlib.Path) -> None:
    verify_output(base_dir)
    generator_text=read_text(base_dir/'generate_ansible_enterprise.py')
    generator_text.encode('ascii')
    if len(generator_text.splitlines()) < 100: raise SystemExit('Generator appears incomplete or placeholder')
    verify_prompt(read_text(base_dir/'PROMPT.md'))
def remove_generated_repo_content() -> None:
    for rel in GENERATED_TOP_LEVEL_DIRS:
        path=ROOT/rel
        if path.exists(): shutil.rmtree(path)
    for rel in GENERATED_TOP_LEVEL_FILES:
        path=ROOT/rel
        if path.exists(): path.unlink()
def commit_staged_tree(staging_root: pathlib.Path) -> None:
    remove_generated_repo_content()
    for rel in sorted(FILE_MANIFEST):
        dst=ROOT/rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(staging_root/rel, dst)
    for rel in LAYOUT_DIRS: (ROOT/rel).mkdir(parents=True, exist_ok=True)
def main() -> None:
    if not PROMPT.exists(): raise SystemExit('PROMPT.md missing')
    prompt_text=read_text(PROMPT)
    verify_prompt(prompt_text)
    prompt_version,prompt_hash,changed=reconcile_prompt_change(prompt_text)
    clear_staging(); materialize_manifest(STAGING_DIR)
    write_text(STAGING_DIR/'PROMPT.md', prompt_text)
    write_text(STAGING_DIR/'generate_ansible_enterprise.py', read_text(ROOT/'generate_ansible_enterprise.py'))
    verify_generation_acceptance(STAGING_DIR)
    commit_staged_tree(STAGING_DIR)
    shutil.rmtree(STAGING_DIR)
    write_text(HASH_FILE, prompt_hash+'\n')
    write_text(VERSION_FILE, prompt_version+'\n')
    print('Generation Acceptance Checklist passed.')
    if changed: print('Prompt change reconciled.')
    print('Repository regenerated successfully.')
if __name__ == '__main__': main()
