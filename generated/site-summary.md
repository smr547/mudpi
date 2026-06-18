# Site Summary

Generated from `docs/reference/network-registry.yaml`.

## reid

**Zone:** `reid.home.arpa`  
**Description:** Canberra home site  
**LAN CIDR:** `10.1.1.0/24`  
**Gateway:** `10.1.1.1`  
**DNS mode:** `local-authoritative`  
**DNS server host:** `mudpi`  
**DNS server IP:** `10.1.1.3`  
**Search domain:** `reid.home.arpa`  
**DHCP mode:** `authoritative`  
**DHCP authority:** `mudpi`  

| Host | LAN IP | VPN IP | Addressing | Roles |
| --- | --- | --- | --- | --- |
| router | 10.1.1.1 | — | static-on-host | router, gateway |
| vdsl-modem | 10.1.1.2 | — | static-on-host | modem, bridge |
| mudpi | 10.1.1.3 | 10.8.1.1 | static-on-host | wireguard-hub, dns, dhcp, ntp-stratum1, dynamic-dns |
| abbhub | 10.1.1.6 | — | dhcp-reservation | solar-monitor, appliance |
| haswell | 10.1.1.10 | — | dhcp-reserved | workshop-host |
| shorepi | 10.1.1.20 | — | static-on-host | signalk, grafana, influxdb |
| printserver | 10.1.1.30 | — | static-on-host | print-server, utility |
| cam-01 | 10.1.1.41 | — | dhcp-reservation | camera |
| cam-02 | 10.1.1.42 | — | dhcp-reservation | camera |
| cam-03 | 10.1.1.43 | — | dhcp-reservation | camera |
| cam-04 | 10.1.1.44 | — | dhcp-reservation | camera |
| cam-05 | 10.1.1.45 | — | dhcp-reservation | camera |
| cam-06 | 10.1.1.46 | — | dhcp-reservation | camera |
| cam-07 | 10.1.1.47 | — | dhcp-reservation | camera |
| zappi | 10.1.1.50 | — | dhcp-reservation | ev-charger, energy-device |
| printer | 10.1.1.60 | — | dhcp-reservation | printer, appliance |
| sonos-spare | 10.1.1.100 | — | dhcp-reservation | audio, speaker |
| lounge-camera | 10.1.1.102 | — | dhcp-reservation | — |
| energy-monitor | 10.1.1.104 | — | dhcp-reservation | energy-monitor, esp32, relay-controller |
| soundbar | 10.1.1.106 | — | dhcp-reservation | audio, soundbar, airplay |
| irobot-vacuum | 10.1.1.107 | — | dhcp-reservation | vacuum, robot |
| myplace-tablet | 10.1.1.109 | — | dhcp-reservation | home-automation-ui, tablet |
| irene-macbook | 10.1.1.110 | — | — | laptop |
| weather-station | 10.1.1.111 | — | dhcp-reservation | weather-station, esp32, sensors |
| kitchen-display | 10.1.1.112 | — | dhcp-reservation | display, dashboard, energy-monitor |
| ap-outdoor | 10.1.1.113 | — | dhcp-reservation | network-device |
| sonos-workshop | 10.1.1.114 | — | dhcp-reservation | audio, speaker |
| sonos-mudroom | 10.1.1.115 | — | dhcp-reservation | audio, speaker |
| appletv-lounge | 10.1.1.116 | — | dhcp-reservation | media-player, tv |
| ap-02 | 10.1.1.117 | — | dhcp-reservation | wifi-ap |
| ap-03 | 10.1.1.118 | — | dhcp-reservation | wifi-ap |
| solar-monitor | 10.1.1.119 | — | dhcp-reservation | solar-monitor, esp32 |
| chain-counter | 10.1.1.120 | — | dhcp-reservation | esp32 |
| esp32-spare-1-monitor | 10.1.1.121 | — | dhcp-reservation | esp32 |
| battery-temp | 10.1.1.122 | — | dhcp-reservation | esp32 |
| ap-01 | 10.1.1.123 | — | dhcp-reservation | wifi-ap |
| hydrawise-workshop | 10.1.1.124 | — | dhcp-reservation | irrigation-controller |
| signal-generator | 10.1.1.128 | — | dhcp-reservation | signal-generator, esp32 |
| hydrawise-main | 10.1.1.130 | — | dhcp-reservation | irrigation-controller |
| tv-french | 10.1.1.131 | — | dhcp-reservation | tv, display, smart-tv |
| dfrobot-edge101 | 10.1.1.133 | — | dhcp-reservation | signal-generator, esp32 |
| stevenlaptop | 10.1.1.134 | — | dhcp-reservation | workstation, admin |
| wearable-01 | 10.1.1.135 | — | dhcp-reservation | esp32 |
| tv-main-room | 10.1.1.161 | — | dhcp-reservation | tv, display, smart-tv |
| speaker-switch | 10.1.1.177 | — | dhcp-reservation | audio-switch, custom |
| nvr | 10.1.1.178 | — | dhcp-reservation | nvr, video-recorder, security |
| irene-iphone | — | — | — | mobile |
| steven-iphone | — | — | — | mobile |

## farm

**Zone:** `farm.home.arpa`  
**Description:** Barking Owl Farm  
**LAN CIDR:** `192.168.0.0/24`  
**Gateway:** `192.168.0.1`  
**DNS mode:** `local-authoritative`  
**DNS server host:** `shedpi`  
**DNS server IP:** `192.168.0.210`  
**Search domain:** `farm.home.arpa`  
**DHCP mode:** `authoritative`  
**DHCP authority:** `shedpi`  

| Host | LAN IP | VPN IP | Addressing | Roles |
| --- | --- | --- | --- | --- |
| farm-router | 192.168.0.1 | — | dhcp-reservation | router, gateway |
| ap1 | 192.168.0.100 | — | dhcp-reservation | wifi-ap |
| sunnyboy1 | 192.168.0.147 | — | dhcp-reservation | pv-inverter |
| weatherstation | 192.168.0.179 | — | dhcp-reservation | weather |
| ap2 | 192.168.0.194 | — | dhcp-reservation | wifi-ap |
| sunnyboy2 | 192.168.0.206 | — | dhcp-reservation | pv-inverter |
| shedpi | 192.168.0.210 | 10.8.1.4 | dhcp-reservation | dns, dhcp, signalk, farm-server |
| sunnyboy3 | 192.168.0.223 | — | dhcp-reservation | pv-inverter |
| sunnyisland | 192.168.0.250 | — | dhcp-reservation | battery-inverter, solar-control |

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
