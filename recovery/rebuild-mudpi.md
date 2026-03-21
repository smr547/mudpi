# MudPi Rebuild Procedure

This document describes how to rebuild MudPi if the hardware fails.

---

# Required Hardware

- Raspberry Pi 5
- SSD storage
- Ethernet connection
- GPS receiver (for time server)

---

# Operating System

Install a fresh Linux system on the Raspberry Pi.

Recommended:

Raspberry Pi OS or Ubuntu Server.

---

# Install Core Packages

Install basic tools and networking packages.

Example:

apt install wireguard chrony gpsd

---

# Restore Configuration

Restore configuration files from the repository:

- WireGuard configuration
- NTP configuration
- Dynamic DNS scripts

---

# Verify Services

After installation verify:

- VPN connectivity
- DNS updates
- GPS lock
- NTP synchronization
