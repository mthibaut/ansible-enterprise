# wireguard

Creates one or more WireGuard interfaces from `wireguard_instances`.

`group_vars` example:
```yaml
wireguard_instances:
  - name: wg0
    listen_port: 51820
    address: ["10.10.0.1/24"]
    private_key: "{{ vault_wireguard_private_key }}"
    peers:
      - public_key: "BASE64PUBKEY"
        allowed_ips: ["10.10.0.2/32"]
```

`host_vars` example:
```yaml
wireguard_instances:
  - name: wg0
    mtu: 1420
```

`vault` example:
```yaml
vault_wireguard_private_key: "BASE64PRIVATEKEY"
```
