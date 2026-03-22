# Site Summary

Generated from `docs/reference/network-registry.yaml`.

## reid

**Zone:** `reid.home.arpa`  
**Description:** Canberra home site  
**LAN CIDR:** `10.1.1.0/24`  
**Gateway:** `10.1.1.1`  
**DNS mode:** `local-authoritative`  
**DNS server host:** `mudpi`  
**DNS server IP:** `10.1.1.10`  
**Search domain:** `reid.home.arpa`  
**DHCP mode:** `authoritative`  
**DHCP authority:** `mudpi`  

| Host | LAN IP | VPN IP | Addressing | Roles |
| --- | --- | --- | --- | --- |
| router | 10.1.1.1 | — | static-on-host | gateway |
| abbhub | 10.1.1.6 | — | dhcp-reservation | solar-monitor, appliance |
| mudpi | 10.1.1.10 | 10.8.1.1 | static-on-host | wireguard-hub, dns, dhcp, ntp-stratum1, dynamic-dns |
| shorepi | 10.1.1.20 | — | static-on-host | signalk, influxdb, grafana, app-host |
| printserver | 10.1.1.30 | — | static-on-host | print-server, utility |
| printer | — | — | dhcp-dynamic | printer, appliance |

## barkingowl

**Zone:** `barkingowl.home.arpa`  
**Description:** Barking Owl Farm  
**LAN CIDR:** `192.168.0.0/24`  
**Gateway:** `192.168.0.1`  
**DNS mode:** `local-authoritative`  
**DNS server host:** `shedpi`  
**DNS server IP:** `192.168.0.10`  
**Search domain:** `barkingowl.home.arpa`  
**DHCP mode:** `authoritative`  
**DHCP authority:** `shedpi`  

| Host | LAN IP | VPN IP | Addressing | Roles |
| --- | --- | --- | --- | --- |
| shedpi | 192.168.0.10 | 10.8.1.30 | static-on-host | dns, dhcp, farm-server |
| weatherstation | 192.168.0.50 | — | dhcp-reservation | weather |

## trilogy

**Zone:** `trilogy.home.arpa`  
**Description:** Yacht Trilogy  
**LAN CIDR:** `192.168.98.0/24`  
**Gateway:** `192.168.98.1`  
**DNS mode:** `local-authoritative`  
**DNS server host:** `boatdns`  
**DNS server IP:** `192.168.98.10`  
**Search domain:** `trilogy.home.arpa`  
**DHCP mode:** `authoritative`  
**DHCP authority:** `boatdns`  

| Host | LAN IP | VPN IP | Addressing | Roles |
| --- | --- | --- | --- | --- |
| boatdns | 192.168.98.10 | 10.8.1.40 | static-on-host | dns, dhcp |
| signalk | 192.168.98.20 | — | static-on-host | signalk |

## testboat

**Zone:** `testboat.home.arpa`  
**Description:** Canberra yacht test system with Starlink test connection  
**LAN CIDR:** `192.168.97.0/24`  
**Gateway:** `192.168.97.1`  
**DNS mode:** `local-authoritative`  
**DNS server host:** `labdns`  
**DNS server IP:** `192.168.97.10`  
**Search domain:** `testboat.home.arpa`  
**DHCP mode:** `authoritative`  
**DHCP authority:** `labdns`  

| Host | LAN IP | VPN IP | Addressing | Roles |
| --- | --- | --- | --- | --- |
| labdns | 192.168.97.10 | 10.8.1.50 | static-on-host | dns, dhcp |

## vpn

**Zone:** `vpn.home.arpa`  
**Description:** WireGuard overlay network  
**Overlay CIDR:** `10.8.1.0/24`  
**Hub:** `10.8.1.1`  
**DNS mode:** `authoritative-on-mudpi`  
**DNS server host:** `mudpi`  
**DNS server IP:** `10.8.1.1`  
**DHCP mode:** `none`  

| Host | LAN IP | VPN IP | Addressing | Roles |
| --- | --- | --- | --- | --- |
| laptop | — | 10.8.1.20 | wireguard-static | roaming-client |
