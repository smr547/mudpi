# Host Registry

Generated from `docs/reference/network-registry.yaml`.

| Host | Site | Category | LAN IP | VPN IP | Addressing | Roles | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| shedpi | barkingowl | infrastructure | 192.168.0.10 | 10.8.1.30 | static-on-host | dns, dhcp, farm-server | Local DNS/DHCP authority for Barking Owl |
| weatherstation | barkingowl | sensor | 192.168.0.50 | — | dhcp-reservation | weather | Example farm service for Bubs and local users |
| abbhub | reid | energy | 10.1.1.6 | — | dhcp-reservation | solar-monitor, appliance | ABB solar monitor hub for RF communication with rooftop panels; queried for plant.xml to monitor solar energy production |
| mudpi | reid | infrastructure | 10.1.1.10 | 10.8.1.1 | static-on-host | wireguard-hub, dns, dhcp, ntp-stratum1, dynamic-dns | Infrastructure control-plane node |
| printer | reid | appliance | — | — | dhcp-dynamic | printer, appliance | Brother HL-L2460DW network printer |
| printserver | reid | server | 10.1.1.30 | — | static-on-host | print-server, utility | Raspberry Pi 5 used as 3D print server |
| router | reid | infrastructure | 10.1.1.1 | — | static-on-host | gateway | Site gateway |
| shorepi | reid | server | 10.1.1.20 | — | static-on-host | signalk, influxdb, grafana, app-host | Legacy services host |
| zappi | reid | energy | 10.1.1.50 | — | dhcp-reservation | ev-charger, energy-device | MyEnergi Zappi EV charger |
| labdns | testboat | infrastructure | 192.168.97.10 | 10.8.1.50 | static-on-host | dns, dhcp | Placeholder lab DNS/DHCP host |
| boatdns | trilogy | infrastructure | 192.168.98.10 | 10.8.1.40 | static-on-host | dns, dhcp | Placeholder onboard DNS/DHCP host |
| signalk | trilogy | server | 192.168.98.20 | — | static-on-host | signalk | Placeholder onboard Signal K service |
| laptop | vpn | client | — | 10.8.1.20 | wireguard-static | roaming-client | Sten's roaming laptop |
