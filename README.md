# MudPi

MudPi is a **Raspberry Pi 5 infrastructure server** located in the mudroom communications cabinet
at the Canberra home of the Ring family.

MudPi provides the **core network infrastructure services** for the home network and acts as the
secure hub connecting:

- Canberra home network
- Barking Owl Farm network
- Yacht *Trilogy*
- Remote laptops and devices

The system is designed to be:

- Reliable
- Low power
- Fully documented
- Rebuildable if hardware fails

---

# Primary Roles

MudPi serves several critical functions.

## Network Boundary Server

MudPi sits at the **edge of the home LAN** and manages secure connectivity between local and remote systems.

## VPN Hub

MudPi hosts the **WireGuard hub** used to interconnect all remote sites.

## Infrastructure Services

MudPi runs core infrastructure services including:

- Dynamic DNS updater
- WireGuard VPN
- GPS disciplined time server

## Documentation Anchor

All system configuration and architecture documentation is stored in this repository.

---

# Physical Location

MudPi is installed in the **mudroom communications cabinet**.

The cabinet contains:

- Raspberry Pi 5
- Structured house cabling
- Ethernet switch
- PoE distribution
- DC UPS power system

MudPi is powered from the **house DC UPS system** to allow continued operation during power outages.

---

# Current Services

| Service | Purpose |
|------|------|
| Dynamic DNS | Maintain DNS record for dynamic home IP |
| WireGuard | Secure VPN hub |
| GPS Time Server | High precision time source |
| SSH | System administration |

---

# Repository Structure

See `docs/repository-structure.md` for the recommended repository layout.
