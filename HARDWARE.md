# MudPi Hardware

MudPi is a **Raspberry Pi 5 based infrastructure server** located in the mudroom
communications cabinet at the Canberra home.

The purpose of this document is to describe the **physical hardware configuration**
so the system can be rebuilt or repaired if necessary.

---

# System Overview

MudPi provides core infrastructure services for the home network including:

- Dynamic DNS updates
- WireGuard VPN hub
- GPS disciplined time server
- Secure remote administration

The hardware platform is designed to be:

- Reliable
- Low power
- Easily replaceable
- Fully documented

---

# Core Platform

## Computer

Model:

Raspberry Pi 5

Purpose:

Runs all MudPi infrastructure services.

Notes:

The Raspberry Pi platform was selected because it is:

- reliable
- widely available
- easy to replace
- well supported in Linux environments

---

# Storage

MudPi uses **SSD storage rather than SD cards** for reliability.

Typical configuration:

- NVMe or USB SSD connected to the Raspberry Pi
- Linux root filesystem stored on the SSD

Benefits:

- higher reliability
- better performance
- reduced risk of filesystem corruption

---

# Networking

MudPi is connected to the home network via **Gigabit Ethernet**.

Connection:

Ethernet cable to the communications cabinet switch.

MudPi acts as the **infrastructure node** supporting:

- VPN connectivity
- network services
- time synchronisation

---

# GPS Time Server Hardware

MudPi includes a **GPS receiver with PPS (Pulse Per Second)** output
to provide a high precision time reference.

Typical components:

- USB GPS receiver
- PPS signal connected to Raspberry Pi GPIO

This allows MudPi to operate as a **GPS disciplined NTP server** for the local network.

Benefits:

- highly accurate system time
- stable reference for logging systems
- reliable time distribution across the LAN

---

# Power System

MudPi is powered from the **house DC UPS system** installed in the
mudroom communications cabinet.

Power architecture:

- central DC battery backup
- regulated supply to infrastructure devices

Benefits:

- continued operation during power outages
- stable power supply
- improved system reliability

---

# Communications Cabinet

MudPi is installed in the **mudroom communications cabinet** which also contains:

- structured house Ethernet cabling
- network switch
- PoE distribution
- monitoring infrastructure

This cabinet acts as the **central communications hub for the house**.

---

# Physical Design Philosophy

MudPi hardware design follows several principles.

## Simple replacement

All components should be replaceable using widely available hardware.

## Minimal moving parts

No fans or spinning disks if possible.

## Clear documentation

All connections and components should be documented in this repository.

---

# Future Hardware Expansion

Possible future hardware additions include:

- additional SSD storage
- improved GPS antenna placement
- hardware monitoring sensors

---

# Rebuild Notes

If MudPi hardware fails:

1. Replace Raspberry Pi
2. Connect SSD
3. Restore software configuration from the MudPi repository

See:

recovery/rebuild-mudpi.md
