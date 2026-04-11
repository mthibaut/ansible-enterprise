# nfs

Handles NFS server exports, client mounts, and generic non-NFS mounts.

`group_vars` example:
```yaml
nfs:
  server:
    enabled: true
    versions: [3, 4.0]
    threads: 8
    idmap_domain: example.internal
    exports:
      - path: /srv/nfs/data
        clients:
          - host: 192.0.2.0/24
            options: rw,sync,no_subtree_check
  client:
    enabled: true
    mounts:
      - src: server:/srv/nfs/data
        path: /mnt/data
        fstype: nfs4
        opts: vers=4.0,proto=tcp,hard
```

`host_vars` example:
```yaml
mounts:
  - src: //fileserver/share
    path: /mnt/share
    fstype: cifs
    opts: credentials=/root/.smb/login
```

`vault` example:
```yaml
# No role-specific vault keys.
```
