# MudPi Distributed DNS Architecture

Author: Sten Ring\
System: MudPi Infrastructure Node\
Purpose: Document the private DNS architecture used across the
Home--Farm--Boat--VPN network.

------------------------------------------------------------------------

# 1. Overview

The MudPi system acts as the **infrastructure control node** for a
distributed private network spanning:

-   Reid (Canberra home)
-   Barking Owl Farm
-   Yacht Trilogy
-   Testboat lab system in Canberra
-   VPN overlay network
-   Roaming devices (laptop, co‑owners, etc.)

The network is interconnected using **WireGuard VPN**, and DNS
resolution is implemented using a **hybrid distributed architecture**.

This design provides:

-   Local resilience at each site
-   Global name resolution across the VPN
-   Simple human‑readable hostnames
-   Compliance with IETF private naming standards

------------------------------------------------------------------------

# 2. Private Namespace

The system uses the IETF‑reserved private domain:

    home.arpa

Site namespaces are defined directly beneath this domain:

    reid.home.arpa
    barkingowl.home.arpa
    trilogy.home.arpa
    testboat.home.arpa
    vpn.home.arpa

Each site manages its own subdomain.

------------------------------------------------------------------------

# 3. Naming Convention

Hostnames follow the pattern:

    host.site.home.arpa

Examples:

  Host                                  Domain                       Description
  ------------------------------------- ---------------------------- -------------
  mudpi.reid.home.arpa                  Reid infrastructure server   
  shorepi.reid.home.arpa                Application server           
  shedpi.barkingowl.home.arpa           Farm server                  
  weatherstation.barkingowl.home.arpa   Farm weather station         
  nav.trilogy.home.arpa                 Yacht navigation computer    
  mudpi.vpn.home.arpa                   VPN overlay interface        

Short names may also be used locally when DHCP provides the appropriate
search domain.

Example:

    weatherstation → weatherstation.barkingowl.home.arpa

------------------------------------------------------------------------

# 4. Hybrid DNS Model

The system uses a **two‑layer DNS architecture**.

## 4.1 Local DNS Authority

Each site hosts its own DNS server responsible for its own zone.

  Site          DNS Server    Zone
  ------------- ------------- ----------------------
  Reid          MudPi         reid.home.arpa
  Barking Owl   ShedPi        barkingowl.home.arpa
  Trilogy       Boat system   trilogy.home.arpa
  Testboat      Lab system    testboat.home.arpa
  VPN           MudPi         vpn.home.arpa

Local clients query the local DNS server first.

This ensures that site services continue to function even if the VPN or
internet connection fails.

Example (Barking Owl):

    Laptop → ShedPi DNS

Queries resolved locally:

    weatherstation
    weatherstation.barkingowl.home.arpa
    shedpi.barkingowl.home.arpa

MudPi is not required for these local queries.

------------------------------------------------------------------------

# 5. MudPi as Coordinating Resolver

MudPi acts as the **cross‑site resolver** for the entire estate.

MudPi forwards queries to other DNS servers via the VPN when required.

Example forwarding rules:

    barkingowl.home.arpa → ShedPi
    trilogy.home.arpa → Boat DNS
    testboat.home.arpa → Testboat DNS

Example resolution path from Reid:

    Laptop
       ↓
    MudPi DNS
       ↓
    ShedPi DNS
       ↓
    weatherstation.barkingowl.home.arpa

------------------------------------------------------------------------

# 6. DHCP and Search Domains

Each site distributes a search domain via DHCP.

  Site          Search Domain
  ------------- ----------------------
  Reid          reid.home.arpa
  Barking Owl   barkingowl.home.arpa
  Trilogy       trilogy.home.arpa
  Testboat      testboat.home.arpa

This allows short hostnames to function locally.

Example:

    http://weatherstation

is automatically expanded to:

    weatherstation.barkingowl.home.arpa

------------------------------------------------------------------------

# 7. Canonical Names

The **fully qualified domain name (FQDN)** is always considered the
authoritative name.

Examples:

    weatherstation.barkingowl.home.arpa
    mudpi.reid.home.arpa
    nav.trilogy.home.arpa

Short names are provided only for convenience within the local network.

------------------------------------------------------------------------

# 8. VPN Overlay Integration

The VPN overlay network uses:

    vpn.home.arpa

Example hosts:

    mudpi.vpn.home.arpa
    laptop.vpn.home.arpa
    trilogygw.vpn.home.arpa

VPN clients typically use MudPi as their DNS server.

Example WireGuard configuration:

    DNS = 10.8.1.1

------------------------------------------------------------------------

# 9. Resilience Characteristics

This architecture ensures:

-   Each site continues operating independently
-   DNS remains functional during WAN outages
-   Cross‑site name resolution works through VPN
-   Local users are unaware of infrastructure complexity

Example resilience scenarios:

  Scenario        Outcome
  --------------- ----------------------------------
  VPN down        Local DNS still works
  Internet down   Local DNS still works
  MudPi offline   Local sites continue functioning

------------------------------------------------------------------------

# 10. Operational Benefits

This architecture provides:

-   Clean naming hierarchy
-   Site autonomy
-   Easy troubleshooting
-   Clear separation of infrastructure vs services
-   Scalability for additional sites

This model is commonly used in:

-   research vessel networks
-   remote observatories
-   expedition infrastructure
-   distributed industrial control systems

------------------------------------------------------------------------

# 11. Future Extensions

Potential future enhancements include:

-   DNSSEC for internal zones
-   automated zone generation from a registry file
-   failover DNS between MudPi and ShorePi
-   service discovery via mDNS where appropriate

------------------------------------------------------------------------

# 12. Summary

MudPi serves as the **network control plane**, coordinating DNS and VPN
infrastructure across the distributed environment while allowing each
site to maintain local operational independence.

The result is a resilient, scalable, and standards‑compliant private
network spanning home, farm, yacht, and mobile systems.

## TODO – Policy Update Required

This document describes the overall DNS architecture for the MudPi multi-site network.  
Since the initial draft, several **network policy decisions** have been adopted and are now
implemented in `docs/reference/network-registry.yaml`.

These policies must be formally captured in this document to ensure the architecture
documentation reflects the operational design.

The following policy areas require documentation updates:

### Addressing Plan
Standardised addressing is now used across all sites:

| Role | Host ID |
|-----|------|
| Gateway | `.1` |
| Primary infrastructure node (DNS/DHCP) | `.10` |
| Secondary / application server | `.20` |
| Utility host | `.30` |
| Reserved appliances / sensors | `.50–.69` |
| Dynamic DHCP pool | `.100–.199` |
| Temporary / experimental | `.200–.239` |
| Administrative reserve | `.240–.254` |

### DHCP Policy
DHCP authority resides on the **site infrastructure host**, not the router.

| Site | DHCP Authority |
|----|----|
| Reid | MudPi |
| Barking Owl | ShedPi |
| Trilogy | boat infrastructure host |
| Testboat | lab infrastructure host |

Routers should gradually be reduced to **gateway-only devices**.

### Address Assignment Policy

| Device Type | Address Method |
|----|----|
| Infrastructure hosts | Static address configured on host |
| Routers | Static |
| Appliances / sensors | DHCP reservation |
| Mobile clients | Dynamic DHCP |

### DNS Policy

- Each site DNS server is **authoritative for its own zone**.
- MudPi acts as the **cross-site coordinating resolver**.
- Short hostnames are **site-local convenience only**.
- Canonical names follow: ``host.site.home.arpa``


Example:

```
mudpi.reid.home.arpa
shedpi.barkingowl.home.arpa
nav.trilogy.home.arpa
```

### Configuration Source of Truth

The authoritative infrastructure registry is: ``docs/reference/network-registry.yaml``


This registry drives generation of:

- DNS host records
- DHCP reservations
- reverse DNS entries
- host documentation

Future tooling may automatically generate configuration from this registry.
