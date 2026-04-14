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

Topology-driven generation is also available via
[wireguard_topology_render.py](/Users/mthibaut/install/chat-gpt-out/ansible-enterprise/src/scripts/wireguard_topology_render.py).
It compiles a topology YAML into:

- `host_vars/<host>/wireguard.yml`
- `host_vars/<host>/wireguard_vault_<network>.yml`
- ready-to-use `wg-quick` configs under `wg-conf/`

Example:

```bash
./src/scripts/wireguard_topology_render.py \
  --inventory ../gilde \
  --topology ../wireguard/topology.yml
```

Use `--rotate <network>` to force-regenerate keys and PSKs for one network.
