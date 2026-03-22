# Network Inventory

Generated from `docs/reference/network-registry.yaml`.

This document provides an operational inventory of the MudPi multi-site network,
including sites, subnets, DNS/DHCP authority, key hosts, and service roles.
It is intended as a human-readable engineering reference for maintenance,
troubleshooting, and continuity of operations.

## Estate Overview

| Site | Zone | Subnet | DNS | DHCP | Notes |
| --- | --- | --- | --- | --- | --- |
| reid | reid.home.arpa | 10.1.1.0/24 | mudpi | mudpi | Canberra home site |
| barkingowl | barkingowl.home.arpa | 192.168.0.0/24 | shedpi | shedpi | Barking Owl Farm |
| trilogy | trilogy.home.arpa | 192.168.98.0/24 | boatdns | boatdns | Yacht Trilogy |
| testboat | testboat.home.arpa | 192.168.97.0/24 | labdns | labdns | Canberra yacht test system with Starlink test connection |
| vpn | vpn.home.arpa | 10.8.1.0/24 | mudpi | — | WireGuard overlay network |

## Critical Infrastructure Summary

| Host | Site | Function | Notes |
| --- | --- | --- | --- |
| shedpi.barkingowl.home.arpa | barkingowl | dns, dhcp, farm-server | Local DNS/DHCP authority for Barking Owl |
| mudpi.reid.home.arpa | reid | wireguard-hub, dns, dhcp, ntp-stratum1, dynamic-dns | Infrastructure control-plane node |
| labdns.testboat.home.arpa | testboat | dns, dhcp | Placeholder lab DNS/DHCP host |
| boatdns.trilogy.home.arpa | trilogy | dns, dhcp | Placeholder onboard DNS/DHCP host |

## Addressing Policy Summary

| Role | Host ID |
| --- | --- |
| Gateway | .1 |
| Primary infra node | .10 |
| Secondary / application host | .20 |
| Utility host | .30 |
| Reserved appliances | .50–.69 |
| Dynamic pool | .100–.199 |

## Site Inventory: reid

**Zone:** `reid.home.arpa`  
**Description:** Canberra home site  
**Subnet:** `10.1.1.0/24`  
**Gateway:** `10.1.1.1`  
**DNS authority:** `mudpi`  
**DHCP authority:** `mudpi`  

| Host | FQDN | LAN IP | VPN IP | Addressing | Roles | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| router | router.reid.home.arpa | 10.1.1.1 | — | static-on-host | gateway | Site gateway |
| mudpi | mudpi.reid.home.arpa | 10.1.1.10 | 10.8.1.1 | static-on-host | wireguard-hub, dns, dhcp, ntp-stratum1, dynamic-dns | Infrastructure control-plane node |
| shorepi | shorepi.reid.home.arpa | 10.1.1.20 | — | static-on-host | signalk, influxdb, grafana, app-host | Legacy services host |

## Site Inventory: barkingowl

**Zone:** `barkingowl.home.arpa`  
**Description:** Barking Owl Farm  
**Subnet:** `192.168.0.0/24`  
**Gateway:** `192.168.0.1`  
**DNS authority:** `shedpi`  
**DHCP authority:** `shedpi`  

| Host | FQDN | LAN IP | VPN IP | Addressing | Roles | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| shedpi | shedpi.barkingowl.home.arpa | 192.168.0.10 | 10.8.1.30 | static-on-host | dns, dhcp, farm-server | Local DNS/DHCP authority for Barking Owl |
| weatherstation | weatherstation.barkingowl.home.arpa | 192.168.0.50 | — | dhcp-reservation | weather | Example farm service for Bubs and local users |

## Site Inventory: trilogy

**Zone:** `trilogy.home.arpa`  
**Description:** Yacht Trilogy  
**Subnet:** `192.168.98.0/24`  
**Gateway:** `192.168.98.1`  
**DNS authority:** `boatdns`  
**DHCP authority:** `boatdns`  

| Host | FQDN | LAN IP | VPN IP | Addressing | Roles | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| boatdns | boatdns.trilogy.home.arpa | 192.168.98.10 | 10.8.1.40 | static-on-host | dns, dhcp | Placeholder onboard DNS/DHCP host |
| signalk | signalk.trilogy.home.arpa | 192.168.98.20 | — | static-on-host | signalk | Placeholder onboard Signal K service |

## Site Inventory: testboat

**Zone:** `testboat.home.arpa`  
**Description:** Canberra yacht test system with Starlink test connection  
**Subnet:** `192.168.97.0/24`  
**Gateway:** `192.168.97.1`  
**DNS authority:** `labdns`  
**DHCP authority:** `labdns`  

| Host | FQDN | LAN IP | VPN IP | Addressing | Roles | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| labdns | labdns.testboat.home.arpa | 192.168.97.10 | 10.8.1.50 | static-on-host | dns, dhcp | Placeholder lab DNS/DHCP host |

## Site Inventory: vpn

**Zone:** `vpn.home.arpa`  
**Description:** WireGuard overlay network  
**Overlay:** `10.8.1.0/24`  
**Hub:** `10.8.1.1`  
**DNS authority:** `mudpi`  

| Host | FQDN | LAN IP | VPN IP | Addressing | Roles | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| laptop | laptop.vpn.home.arpa | — | 10.8.1.20 | wireguard-static | roaming-client | Sten's roaming laptop |

## Operational Notes

- Infrastructure hosts use static addresses configured on-host where practical.
- Appliances and sensors use DHCP reservations on the site DHCP server.
- Mobile and visitor devices use dynamic DHCP pools.
- Site-local short names depend on local DHCP search domains.
- Canonical names follow the pattern `host.site.home.arpa`.
- MudPi acts as the cross-site coordinating resolver for the estate.
