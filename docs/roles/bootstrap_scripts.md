# bootstrap_scripts

Generates bootstrap shell scripts on the controller for new hosts.

`group_vars` example:
```yaml
bootstrap_output_dir: "{{ playbook_dir }}/bootstrap"
bootstrap_repo_uri: "git@github.com:your-org/ansible-enterprise.git"
```

`host_vars` example:
```yaml
bootstrap_repo_uri: "/opt/ansible-enterprise"
```

`vault` example:
```yaml
admin_ssh_public_key: "ssh-ed25519 AAAA..."
admin_dev_password_hash: "$6$..."
```
