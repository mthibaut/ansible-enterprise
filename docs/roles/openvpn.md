# openvpn

Creates one or more OpenVPN server or client instances from `openvpn_instances`.

`group_vars` example:
```yaml
openvpn_instances:
  - name: main
    mode: server
    port: 1194
    proto: udp
    network: 10.8.0.0
    netmask: 255.255.255.0
    clients: [laptop]
```

`host_vars` example:
```yaml
openvpn_instances:
  - name: office
    mode: client
    remote: vpn.example.com
    port: 1194
    proto: udp
```

`vault` example:
```yaml
# Keep client/server keys in vault or referenced secure files.
```
