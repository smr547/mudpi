# MudPi Architecture

MudPi is the **core infrastructure node** for the Ring family distributed network.

It connects the home network with remote systems including Barking Owl Farm and the yacht Trilogy.

---

# System Overview

MudPi provides:

- Secure VPN connectivity
- Time synchronization
- Core network infrastructure services

The design philosophy is:

- simple
- reliable
- reproducible

---

# Connected Sites

| Site | Role |
|----|----|
| Canberra Home | primary LAN |
| Barking Owl Farm | remote farm network |
| Trilogy Yacht | mobile network |
| Remote devices | laptops and maintenance systems |

---

# Network Relationships

MudPi acts as the **hub** for all VPN connections.

Remote sites connect via WireGuard and can securely communicate with each other.
