# Role Configuration Guides

Each role has a short configuration guide here with:

- what the role does
- the main inventory keys it reads
- an example for `group_vars`
- an example for `host_vars`
- any related `vault` keys

Available guides:

- [preflight](preflight.md)
- [common](common.md)
- [ssh_hardening](ssh_hardening.md)
- [users](users.md)
- [geoip](geoip.md)
- [firewall_geo](firewall_geo.md)
- [dns](dns.md)
- [certbot](certbot.md)
- [apache2](apache2.md)
- [nginx](nginx.md)
- [nextcloud](nextcloud.md)
- [mailserver](mailserver.md)
- [node_exporter](node_exporter.md)
- [docker](docker.md)
- [prometheus](prometheus.md)
- [grafana](grafana.md)
- [openvpn](openvpn.md)
- [wireguard](wireguard.md)
- [step_ca](step_ca.md)
- [samba](samba.md)
- [nfs](nfs.md)
- [container_engine](container_engine.md)
- [workloads](workloads.md)
- [bootstrap_scripts](bootstrap_scripts.md)
- [proxmox](proxmox.md)
- [pfsense](pfsense.md)
- [file_copy](file_copy.md)

For generated defaults, the most precise source remains `build/roles/<role>/defaults/main.yml` after `make generate`.
