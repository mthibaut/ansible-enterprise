# file_copy

Copies files from the repo or writes inline content to target hosts, creating parent directories automatically.

`group_vars` example:
```yaml
file_copy_items:
  - src: contrib/myapp-logrotate.conf
    dest: /etc/logrotate.d/myapp
    mode: "0644"
  - content: |
      [global]
        log level = 1
    dest: /etc/myapp/generated.conf
    mode: "0644"
```

`host_vars` example:
```yaml
file_copy_items:
  - content: |
      hello from host override
    dest: /etc/motd.d/custom
```

`vault` example:
```yaml
# Reference vault vars inside file_copy_items[].content if needed.
```
