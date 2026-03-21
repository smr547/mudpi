
# MudPi Repository Structure

This document describes a recommended repository structure for the **MudPi infrastructure server**.
MudPi acts as the **home network boundary server** and infrastructure node for the Ring family
home–farm–boat network ecosystem.

The goal of this repository is:

- Clear documentation
- Reproducible configuration
- Easy maintenance by family members
- Separation between infrastructure and individual services

---

# Repository Philosophy

MudPi should follow several design principles.

## 1. Documentation First

Every service running on MudPi should have documentation explaining:

- Why it exists
- How it works
- How to rebuild it

Future maintainers (Sten, Irene, PJ, James) should be able to rebuild MudPi from this repository.

## 2. Configuration is Version Controlled

Where possible:

- service configs
- scripts
- systemd unit files

should be stored in the repo.

## 3. Services May Have Their Own Repositories

If a service becomes complex or reusable it may be separated into its own repository.

Examples:

- ddns updater
- signalk integrations
- telemetry collectors

MudPi then references these services.

---

# Top Level Repository Layout

Recommended structure:

```
mudpi/
│
├── README.md
├── ARCHITECTURE.md
├── HARDWARE.md
├── NETWORK.md
├── SERVICES.md
│
├── docs/
│   ├── diagrams/
│   ├── architecture/
│   ├── network/
│   ├── recovery/
│   └── operations/
│
├── services/
│   ├── ddns/
│   ├── wireguard/
│   ├── dns/
│   └── timeserver/
│
├── configs/
│   ├── systemd/
│   ├── dnsmasq/
│   ├── wireguard/
│   └── ntp/
│
├── scripts/
│   ├── install/
│   ├── maintenance/
│   └── diagnostics/
│
└── recovery/
    ├── rebuild-mudpi.md
    ├── disaster-recovery.md
    └── backup-procedures.md
```

---

# Core Documentation Files

## README.md

Overview of MudPi:

- purpose
- system role
- major services
- network diagram

This is the entry point for anyone opening the repository.

---

## ARCHITECTURE.md

Describes the overall system architecture including:

- MudPi role
- relationship with ShorePi
- Barking Owl Farm systems
- Trilogy yacht network
- WireGuard topology

---

## HARDWARE.md

Describes the physical installation:

- Raspberry Pi 5
- SSD storage
- UPS power
- Ethernet connections
- cabinet location

---

## NETWORK.md

Documents network topology:

- LAN addressing
- VPN addressing
- routing between sites

Example networks:

- Canberra Home: 10.1.1.0/24
- Barking Owl Farm: 192.168.0.0/24
- Trilogy Yacht: 192.168.98.0/24
- WireGuard: 10.8.1.0/24

---

## SERVICES.md

Summary of services running on MudPi.

Example sections:

- Dynamic DNS updater
- WireGuard VPN hub
- DNS server (future)
- GPS disciplined time server

---

# docs/ Directory

Contains longer narrative documentation.

Recommended structure:

```
docs/
   architecture/
   network/
   operations/
   recovery/
   diagrams/
```

Examples:

- network topology diagrams
- system lifecycle docs
- maintenance procedures

---

# services/ Directory

Contains documentation and minimal configuration for each service.

Example:

```
services/
   ddns/
      README.md
      design.md
      install.md

   wireguard/
      README.md
      topology.md

   timeserver/
      README.md
      gps-pps.md
```

If a service becomes substantial it can move to its own repository.

---

# configs/

Contains configuration files copied from the running system.

Example:

```
configs/
   systemd/
   dnsmasq/
   wireguard/
   ntp/
```

These should represent **known-good configurations**.

---

# scripts/

Automation scripts.

Examples:

- installation helpers
- diagnostics
- maintenance scripts

---

# recovery/

Critical documentation explaining how to rebuild the system.

Example files:

- rebuild-mudpi.md
- disaster-recovery.md
- backup-procedures.md

These documents should allow the entire system to be rebuilt from scratch.

---

# Time Server Documentation

MudPi currently runs a **GPS disciplined time server**.

Documentation should include:

- GPS receiver hardware
- PPS configuration
- chrony/ntp configuration
- accuracy expectations

Recommended location:

```
services/timeserver/
```

---

# Diagram Sources

All diagrams should store **editable source files**.

Recommended format:

- draw.io
- Mermaid

Example location:

```
docs/diagrams/
```

---

# Long-Term Goal

The repository should make MudPi a **fully reproducible infrastructure node**.

If MudPi fails, the system should be rebuildable using only:

- this repository
- a new Raspberry Pi
- a fresh Linux installation

---
