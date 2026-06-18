# Host Registry

Generated from `docs/reference/network-registry.yaml`.

| Host | Site | Category | LAN IP | VPN IP | Addressing | Roles | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ap1 | farm | network | 192.168.0.100 | — | dhcp-reservation | wifi-ap | — |
| ap2 | farm | network | 192.168.0.194 | — | dhcp-reservation | wifi-ap | — |
| farm-router | farm | network | 192.168.0.1 | — | dhcp-reservation | router, gateway | Farm LAN gateway/router |
| shedpi | farm | infrastructure | 192.168.0.210 | 10.8.1.4 | dhcp-reservation | dns, dhcp, signalk, farm-server | Local DNS/DHCP authority for Barking Owl |
| sunnyboy1 | farm | energy | 192.168.0.147 | — | dhcp-reservation | pv-inverter | Observed stable address; DHCP/static configuration not yet confirmed |
| sunnyboy2 | farm | energy | 192.168.0.206 | — | dhcp-reservation | pv-inverter | Observed stable address; DHCP/static configuration not yet confirmed |
| sunnyboy3 | farm | energy | 192.168.0.223 | — | dhcp-reservation | pv-inverter | Observed stable address; DHCP/static configuration not yet confirmed |
| sunnyisland | farm | energy | 192.168.0.250 | — | dhcp-reservation | battery-inverter, solar-control | Observed stable address; may be DHCP-assigned or statically configured on device |
| weatherstation | farm | sensor | 192.168.0.179 | — | dhcp-reservation | weather | Farm weather station |
| abbhub | reid | energy | 10.1.1.6 | — | dhcp-reservation | solar-monitor, appliance | ABB solar monitor hub for RF communication with rooftop panels; queried for plant.xml to monitor solar energy production |
| ap-01 | reid | network | 10.1.1.123 | — | dhcp-reservation | wifi-ap | Ubiquiti Wi-Fi access point above dining room |
| ap-02 | reid | network | 10.1.1.117 | — | dhcp-reservation | wifi-ap | Ubiquiti Wi-Fi access point above hallway leading to big bedroom |
| ap-03 | reid | network | 10.1.1.118 | — | dhcp-reservation | wifi-ap | Ubiquiti Wi-Fi access point -- above study |
| ap-outdoor | reid | network | 10.1.1.113 | — | dhcp-reservation | network-device | Ubiquiti wireless access point under workshop eve (NE corner of garage) |
| appletv-lounge | reid | media | 10.1.1.116 | — | dhcp-reservation | media-player, tv | Apple TV in lounge room |
| battery-temp | reid | iot | 10.1.1.122 | — | dhcp-reservation | esp32 | ESP32 experimental battery monitor |
| cam-01 | reid | camera | 10.1.1.41 | — | dhcp-reservation | camera | Dahua IP camera |
| cam-02 | reid | camera | 10.1.1.42 | — | dhcp-reservation | camera | Dahua IP camera |
| cam-03 | reid | camera | 10.1.1.43 | — | dhcp-reservation | camera | Dahua IP camera |
| cam-04 | reid | camera | 10.1.1.44 | — | dhcp-reservation | camera | Dahua IP camera |
| cam-05 | reid | camera | 10.1.1.45 | — | dhcp-reservation | camera | Dahua IP camera |
| cam-06 | reid | camera | 10.1.1.46 | — | dhcp-reservation | camera | Dahua IP camera |
| cam-07 | reid | camera | 10.1.1.47 | — | dhcp-reservation | camera | Dahua IP camera |
| chain-counter | reid | iot | 10.1.1.120 | — | dhcp-reservation | esp32 | Experimental chain counter based on ESP32 |
| dfrobot-edge101 | reid | iot | 10.1.1.133 | — | dhcp-reservation | signal-generator, esp32 | ESP32-based signal generator in workshop |
| energy-monitor | reid | iot | 10.1.1.104 | — | dhcp-reservation | energy-monitor, esp32, relay-controller | Waveshare ESP32 electricity monitor with 6 relay outputs (mudroom cabinet) |
| esp32-spare-1-monitor | reid | iot | 10.1.1.121 | — | dhcp-reservation | esp32 | ESP32 dev module |
| haswell | reid | infrastructure | 10.1.1.10 | — | dhcp-reserved | workshop-host | Repurposed Haswell workshop machine running Xubuntu 26.04; rebuilt after inverter/power event; prototype NAS |
| hydrawise-main | reid | iot | 10.1.1.130 | — | dhcp-reservation | irrigation-controller | Hydrawise irrigation controller next to terrace (18 valves, 24 port system) |
| hydrawise-workshop | reid | iot | 10.1.1.124 | — | dhcp-reservation | irrigation-controller | Hydrawise irrigation controller in workshop (6 valves) |
| irene-iphone | reid | personal | — | — | — | mobile | — |
| irene-macbook | reid | personal | 10.1.1.110 | — | — | laptop | macOS device; currently using locally administered (private) MAC address on WiFi |
| irobot-vacuum | reid | iot | 10.1.1.107 | — | dhcp-reservation | vacuum, robot | iRobot vacuum cleaner |
| kitchen-display | reid | iot | 10.1.1.112 | — | dhcp-reservation | display, dashboard, energy-monitor | Samsung tablet in kitchen used for electricity consumption display, weather, and recipes |
| lounge-camera | reid | unknown | 10.1.1.102 | — | dhcp-reservation | — | NEXTECH camera in lounge room for watching dog. |
| mudpi | reid | infrastructure | 10.1.1.3 | 10.8.1.1 | static-on-host | wireguard-hub, dns, dhcp, ntp-stratum1, dynamic-dns | Infrastructure control-plane node; wlan0 has also acquired DHCP address 10.1.1.129 on the Reid LAN |
| myplace-tablet | reid | iot | 10.1.1.109 | — | dhcp-reservation | home-automation-ui, tablet | Samsung Android tablet mounted in mudroom running MyPlace home automation UI |
| nvr | reid | security | 10.1.1.178 | — | dhcp-reservation | nvr, video-recorder, security | VIP Vision NVR (Dahua OEM) for IP camera system |
| printer | reid | appliance | 10.1.1.60 | — | dhcp-reservation | printer, appliance | Brother HL-L2460DW network printer |
| printserver | reid | server | 10.1.1.30 | — | static-on-host | print-server, utility | Raspberry Pi 4 used as 3D print server |
| router | reid | network | 10.1.1.1 | — | static-on-host | router, gateway | Primary LAN router (to be replaced by RUT241) |
| shorepi | reid | infrastructure | 10.1.1.20 | — | static-on-host | signalk, grafana, influxdb | Data services node (SignalK, Grafana, InfluxDB) |
| signal-generator | reid | iot | 10.1.1.128 | — | dhcp-reservation | signal-generator, esp32 | ESP32-based signal generator in workshop |
| solar-monitor | reid | iot | 10.1.1.119 | — | dhcp-reservation | solar-monitor, esp32 | ESP32 solar production monitor scrapes data from   http://abbhub/plant.xm |
| sonos-mudroom | reid | media | 10.1.1.115 | — | dhcp-reservation | audio, speaker | Sonos device |
| sonos-spare | reid | media | 10.1.1.100 | — | dhcp-reservation | audio, speaker | Sonos device |
| sonos-workshop | reid | media | 10.1.1.114 | — | dhcp-reservation | audio, speaker | Sonos device |
| soundbar | reid | media | 10.1.1.106 | — | dhcp-reservation | audio, soundbar, airplay | JBL Bar 300 soundbar (Harman / Linkplay platform) |
| speaker-switch | reid | iot | 10.1.1.177 | — | dhcp-reservation | audio-switch, custom | Arduino-based 8-relay speaker switch (Ethernet shield) |
| steven-iphone | reid | personal | — | — | — | mobile | — |
| stevenlaptop | reid | workstation | 10.1.1.134 | — | dhcp-reservation | workstation, admin | Steven's Lenovo Yoga laptop (Kubuntu); dual-homed Ethernet + WiFi |
| tv-french | reid | media | 10.1.1.131 | — | dhcp-reservation | tv, display, smart-tv | Samsung television in French Room |
| tv-main-room | reid | media | 10.1.1.161 | — | dhcp-reservation | tv, display, smart-tv | Samsung television in main room; responds to ARP in standby but blocks ping/ports until powered on |
| vdsl-modem | reid | network | 10.1.1.2 | — | static-on-host | modem, bridge | VDSL modem/bridge (Technicolor/Zyxel) VDSL modem/bridge (Technicolor/Zyxel). Advertises IPv6 link-local DNS via RA/RDNSS as fe80::1213:31ff:fe57:fa00, returning bogus synthetic answers such as google.com -> 198.18.1.1. Do not allow clients to use this device for DNS. |
| wearable-01 | reid | iot | 10.1.1.135 | — | dhcp-reservation | esp32 | ESP32 wearable - currently not in use |
| weather-station | reid | iot | 10.1.1.111 | — | dhcp-reservation | weather-station, esp32, sensors | ESP32-based weather station mounted outside workshop on pole |
| zappi | reid | energy | 10.1.1.50 | — | dhcp-reservation | ev-charger, energy-device | MyEnergi Zappi EV charger |
| labdns | testboat | infrastructure | 192.168.97.10 | 10.8.1.50 | static-on-host | dns, dhcp | Placeholder lab DNS/DHCP host |
| boatdns | trilogy | infrastructure | 192.168.98.10 | 10.8.1.40 | static-on-host | dns, dhcp | Placeholder onboard DNS/DHCP host |
| signalk | trilogy | server | 192.168.98.20 | — | static-on-host | signalk | Placeholder onboard Signal K service |
| laptop | vpn | client | — | 10.8.1.20 | wireguard-static | roaming-client | Sten's roaming laptop |
