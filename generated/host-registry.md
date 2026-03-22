# Host Registry

Generated from `docs/reference/network-registry.yaml`.

| Host | Site | LAN IP | VPN IP | Addressing | Roles | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| shedpi | barkingowl | 192.168.0.10 | 10.8.1.30 | static-on-host | dns, dhcp, farm-server | Local DNS/DHCP authority for Barking Owl |
| weatherstation | barkingowl | 192.168.0.50 | — | dhcp-reservation | weather | Example farm service for Bubs and local users |
| mudpi | reid | 10.1.1.10 | 10.8.1.1 | static-on-host | wireguard-hub, dns, dhcp, ntp-stratum1, dynamic-dns | Infrastructure control-plane node |
| router | reid | 10.1.1.1 | — | static-on-host | gateway | Site gateway |
| shorepi | reid | 10.1.1.20 | — | static-on-host | signalk, influxdb, grafana, app-host | Legacy services host |
| labdns | testboat | 192.168.97.10 | 10.8.1.50 | static-on-host | dns, dhcp | Placeholder lab DNS/DHCP host |
| boatdns | trilogy | 192.168.98.10 | 10.8.1.40 | static-on-host | dns, dhcp | Placeholder onboard DNS/DHCP host |
| signalk | trilogy | 192.168.98.20 | — | static-on-host | signalk | Placeholder onboard Signal K service |
| laptop | vpn | — | 10.8.1.20 | wireguard-static | roaming-client | Sten's roaming laptop |
