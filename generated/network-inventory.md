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
| farm | farm.home.arpa | 192.168.0.0/24 | shedpi | shedpi | Barking Owl Farm |
| trilogy | trilogy.home.arpa | 192.168.98.0/24 | boatdns | boatdns | Yacht Trilogy |
| testboat | testboat.home.arpa | 192.168.97.0/24 | labdns | labdns | Canberra yacht test system with Starlink test connection |
| vpn | vpn.home.arpa | 10.8.1.0/24 | mudpi | — | WireGuard overlay network |

## Critical Infrastructure Summary

| Host | Site | Function | Notes |
| --- | --- | --- | --- |
| shedpi.farm.home.arpa | farm | dns, dhcp, signalk, farm-server | Local DNS/DHCP authority for Barking Owl |
| mudpi.reid.home.arpa | reid | wireguard-hub, dns, dhcp, ntp-stratum1, dynamic-dns | Infrastructure control-plane node; wlan0 has also acquired DHCP address 10.1.1.129 on the Reid LAN |
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
| router | router.reid.home.arpa | 10.1.1.1 | — | static-on-host | router, gateway | Primary LAN router (to be replaced by RUT241) |
| vdsl-modem | vdsl-modem.reid.home.arpa | 10.1.1.2 | — | static-on-host | modem, bridge | VDSL modem/bridge (Technicolor/Zyxel) VDSL modem/bridge (Technicolor/Zyxel). Advertises IPv6 link-local DNS via RA/RDNSS as fe80::1213:31ff:fe57:fa00, returning bogus synthetic answers such as google.com -> 198.18.1.1. Do not allow clients to use this device for DNS. |
| mudpi | mudpi.reid.home.arpa | 10.1.1.3 | 10.8.1.1 | static-on-host | wireguard-hub, dns, dhcp, ntp-stratum1, dynamic-dns | Infrastructure control-plane node; wlan0 has also acquired DHCP address 10.1.1.129 on the Reid LAN |
| abbhub | abbhub.reid.home.arpa | 10.1.1.6 | — | dhcp-reservation | solar-monitor, appliance | ABB solar monitor hub for RF communication with rooftop panels; queried for plant.xml to monitor solar energy production |
| haswell | haswell.reid.home.arpa | 10.1.1.10 | — | dhcp-reserved | workshop-host | Repurposed Haswell workshop machine running Xubuntu 26.04; rebuilt after inverter/power event; prototype NAS |
| shorepi | shorepi.reid.home.arpa | 10.1.1.20 | — | static-on-host | signalk, grafana, influxdb | Data services node (SignalK, Grafana, InfluxDB) |
| printserver | printserver.reid.home.arpa | 10.1.1.30 | — | static-on-host | print-server, utility | Raspberry Pi 4 used as 3D print server |
| cam-01 | cam-01.reid.home.arpa | 10.1.1.41 | — | dhcp-reservation | camera | Dahua IP camera |
| cam-02 | cam-02.reid.home.arpa | 10.1.1.42 | — | dhcp-reservation | camera | Dahua IP camera |
| cam-03 | cam-03.reid.home.arpa | 10.1.1.43 | — | dhcp-reservation | camera | Dahua IP camera |
| cam-04 | cam-04.reid.home.arpa | 10.1.1.44 | — | dhcp-reservation | camera | Dahua IP camera |
| cam-05 | cam-05.reid.home.arpa | 10.1.1.45 | — | dhcp-reservation | camera | Dahua IP camera |
| cam-06 | cam-06.reid.home.arpa | 10.1.1.46 | — | dhcp-reservation | camera | Dahua IP camera |
| cam-07 | cam-07.reid.home.arpa | 10.1.1.47 | — | dhcp-reservation | camera | Dahua IP camera |
| zappi | zappi.reid.home.arpa | 10.1.1.50 | — | dhcp-reservation | ev-charger, energy-device | MyEnergi Zappi EV charger |
| printer | printer.reid.home.arpa | 10.1.1.60 | — | dhcp-reservation | printer, appliance | Brother HL-L2460DW network printer |
| sonos-spare | sonos-spare.reid.home.arpa | 10.1.1.100 | — | dhcp-reservation | audio, speaker | Sonos device |
| lounge-camera | lounge-camera.reid.home.arpa | 10.1.1.102 | — | dhcp-reservation | — | NEXTECH camera in lounge room for watching dog. |
| energy-monitor | energy-monitor.reid.home.arpa | 10.1.1.104 | — | dhcp-reservation | energy-monitor, esp32, relay-controller | Waveshare ESP32 electricity monitor with 6 relay outputs (mudroom cabinet) |
| soundbar | soundbar.reid.home.arpa | 10.1.1.106 | — | dhcp-reservation | audio, soundbar, airplay | JBL Bar 300 soundbar (Harman / Linkplay platform) |
| irobot-vacuum | irobot-vacuum.reid.home.arpa | 10.1.1.107 | — | dhcp-reservation | vacuum, robot | iRobot vacuum cleaner |
| myplace-tablet | myplace-tablet.reid.home.arpa | 10.1.1.109 | — | dhcp-reservation | home-automation-ui, tablet | Samsung Android tablet mounted in mudroom running MyPlace home automation UI |
| irene-macbook | irene-macbook.reid.home.arpa | 10.1.1.110 | — | — | laptop | macOS device; currently using locally administered (private) MAC address on WiFi |
| weather-station | weather-station.reid.home.arpa | 10.1.1.111 | — | dhcp-reservation | weather-station, esp32, sensors | ESP32-based weather station mounted outside workshop on pole |
| kitchen-display | kitchen-display.reid.home.arpa | 10.1.1.112 | — | dhcp-reservation | display, dashboard, energy-monitor | Samsung tablet in kitchen used for electricity consumption display, weather, and recipes |
| ap-outdoor | ap-outdoor.reid.home.arpa | 10.1.1.113 | — | dhcp-reservation | network-device | Ubiquiti wireless access point under workshop eve (NE corner of garage) |
| sonos-workshop | sonos-workshop.reid.home.arpa | 10.1.1.114 | — | dhcp-reservation | audio, speaker | Sonos device |
| sonos-mudroom | sonos-mudroom.reid.home.arpa | 10.1.1.115 | — | dhcp-reservation | audio, speaker | Sonos device |
| appletv-lounge | appletv-lounge.reid.home.arpa | 10.1.1.116 | — | dhcp-reservation | media-player, tv | Apple TV in lounge room |
| ap-02 | ap-02.reid.home.arpa | 10.1.1.117 | — | dhcp-reservation | wifi-ap | Ubiquiti Wi-Fi access point above hallway leading to big bedroom |
| ap-03 | ap-03.reid.home.arpa | 10.1.1.118 | — | dhcp-reservation | wifi-ap | Ubiquiti Wi-Fi access point -- above study |
| solar-monitor | solar-monitor.reid.home.arpa | 10.1.1.119 | — | dhcp-reservation | solar-monitor, esp32 | ESP32 solar production monitor scrapes data from   http://abbhub/plant.xm |
| chain-counter | chain-counter.reid.home.arpa | 10.1.1.120 | — | dhcp-reservation | esp32 | Experimental chain counter based on ESP32 |
| esp32-spare-1-monitor | esp32-spare-1-monitor.reid.home.arpa | 10.1.1.121 | — | dhcp-reservation | esp32 | ESP32 dev module |
| battery-temp | battery-temp.reid.home.arpa | 10.1.1.122 | — | dhcp-reservation | esp32 | ESP32 experimental battery monitor |
| ap-01 | ap-01.reid.home.arpa | 10.1.1.123 | — | dhcp-reservation | wifi-ap | Ubiquiti Wi-Fi access point above dining room |
| hydrawise-workshop | hydrawise-workshop.reid.home.arpa | 10.1.1.124 | — | dhcp-reservation | irrigation-controller | Hydrawise irrigation controller in workshop (6 valves) |
| signal-generator | signal-generator.reid.home.arpa | 10.1.1.128 | — | dhcp-reservation | signal-generator, esp32 | ESP32-based signal generator in workshop |
| hydrawise-main | hydrawise-main.reid.home.arpa | 10.1.1.130 | — | dhcp-reservation | irrigation-controller | Hydrawise irrigation controller next to terrace (18 valves, 24 port system) |
| tv-french | tv-french.reid.home.arpa | 10.1.1.131 | — | dhcp-reservation | tv, display, smart-tv | Samsung television in French Room |
| dfrobot-edge101 | dfrobot-edge101.reid.home.arpa | 10.1.1.133 | — | dhcp-reservation | signal-generator, esp32 | ESP32-based signal generator in workshop |
| stevenlaptop | stevenlaptop.reid.home.arpa | 10.1.1.134 | — | dhcp-reservation | workstation, admin | Steven's Lenovo Yoga laptop (Kubuntu); dual-homed Ethernet + WiFi |
| wearable-01 | wearable-01.reid.home.arpa | 10.1.1.135 | — | dhcp-reservation | esp32 | ESP32 wearable - currently not in use |
| tv-main-room | tv-main-room.reid.home.arpa | 10.1.1.161 | — | dhcp-reservation | tv, display, smart-tv | Samsung television in main room; responds to ARP in standby but blocks ping/ports until powered on |
| speaker-switch | speaker-switch.reid.home.arpa | 10.1.1.177 | — | dhcp-reservation | audio-switch, custom | Arduino-based 8-relay speaker switch (Ethernet shield) |
| nvr | nvr.reid.home.arpa | 10.1.1.178 | — | dhcp-reservation | nvr, video-recorder, security | VIP Vision NVR (Dahua OEM) for IP camera system |
| irene-iphone | irene-iphone.reid.home.arpa | — | — | — | mobile | — |
| steven-iphone | steven-iphone.reid.home.arpa | — | — | — | mobile | — |

## Site Inventory: farm

**Zone:** `farm.home.arpa`  
**Description:** Barking Owl Farm  
**Subnet:** `192.168.0.0/24`  
**Gateway:** `192.168.0.1`  
**DNS authority:** `shedpi`  
**DHCP authority:** `shedpi`  

| Host | FQDN | LAN IP | VPN IP | Addressing | Roles | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| farm-router | farm-router.farm.home.arpa | 192.168.0.1 | — | dhcp-reservation | router, gateway | Farm LAN gateway/router |
| ap1 | ap1.farm.home.arpa | 192.168.0.100 | — | dhcp-reservation | wifi-ap | — |
| sunnyboy1 | sunnyboy1.farm.home.arpa | 192.168.0.147 | — | dhcp-reservation | pv-inverter | Observed stable address; DHCP/static configuration not yet confirmed |
| weatherstation | weatherstation.farm.home.arpa | 192.168.0.179 | — | dhcp-reservation | weather | Farm weather station |
| ap2 | ap2.farm.home.arpa | 192.168.0.194 | — | dhcp-reservation | wifi-ap | — |
| sunnyboy2 | sunnyboy2.farm.home.arpa | 192.168.0.206 | — | dhcp-reservation | pv-inverter | Observed stable address; DHCP/static configuration not yet confirmed |
| shedpi | shedpi.farm.home.arpa | 192.168.0.210 | 10.8.1.4 | dhcp-reservation | dns, dhcp, signalk, farm-server | Local DNS/DHCP authority for Barking Owl |
| sunnyboy3 | sunnyboy3.farm.home.arpa | 192.168.0.223 | — | dhcp-reservation | pv-inverter | Observed stable address; DHCP/static configuration not yet confirmed |
| sunnyisland | sunnyisland.farm.home.arpa | 192.168.0.250 | — | dhcp-reservation | battery-inverter, solar-control | Observed stable address; may be DHCP-assigned or statically configured on device |

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
