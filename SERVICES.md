# MudPi Services

This document summarises the services currently running on MudPi.

---

# Dynamic DNS Updater

Purpose:

Maintain a DNS record that tracks the dynamic IP address of the home internet connection.

Function:

- Detect current external IP
- Update DNS provider record

Service name:

ddns.service

---

# WireGuard VPN

Provides secure connectivity between:

- Canberra home
- Barking Owl Farm
- Trilogy yacht
- Remote devices

VPN network:

10.8.1.0/24

---

# GPS Disciplined Time Server

MudPi runs a **GPS disciplined NTP time server**.

Features:

- GPS receiver
- PPS timing signal
- High precision system clock

This allows accurate time distribution across the home network.
