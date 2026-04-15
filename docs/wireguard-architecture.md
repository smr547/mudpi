# WireGuard Architecture and Enrolment Guide (MudPi)

## Overview

This document defines the WireGuard architecture used across the MudPi-managed network.  
It establishes a clear, reproducible model for:

- Identity (who/what is a peer)
- Routing (what networks are reachable)
- Access control (who can reach what)

The system is **declarative**, driven by a YAML registry.

---

## Core Design Principles

1. **Single Source of Truth**
   - All configuration is generated from `wireguard/registry.yaml`

2. **No Manual Edits**
   - Never edit `/etc/wireguard/wg0.conf` directly

3. **Separation of Concerns**
   - Routing ≠ Access control

4. **Deterministic Identity**
   - Each peer has a stable name and VPN address

---

## Peer Types

### 1. Site Peers

Infrastructure nodes that provide access to a LAN.

Examples:
- `mudpi` (Reid)
- `shedpi` (Farm)
- `boatpi` (Trilogy)

**Characteristics:**
- Advertise routes
- Represent entire subnets
- Act as gateways

**Registry fields:**
```yaml
peer_type: site
routes:
  - 192.168.0.0/24
```

---

### 2. Human Peers

Devices belonging to users.

Examples:
- `sten-laptop`
- `sten-phone`
- `irene`

**Characteristics:**
- Do NOT advertise routes
- Consume access to zones
- Represent a single device/profile

**Registry fields:**
```yaml
peer_type: human
access:
  - reid
```

---

## Zones

Zones represent logical network areas.

```yaml
zones:
  reid:
    subnet: 10.1.1.0/24
    via: mudpi

  farm:
    subnet: 192.168.0.0/24
    via: shedpi

  trilogy:
    subnet: 192.168.98.0/24
    via: boatpi
```

### Semantics

- `subnet` → actual network
- `via` → which site peer provides access

---

## Addressing Convention

| Range              | Purpose       |
|-------------------|--------------|
| 10.8.1.1–49       | Site peers    |
| 10.8.1.100–199    | Human peers   |

Example:
- `shedpi` → 10.8.1.20
- `irene` → 10.8.1.120

---

## Configuration Generation Rules

### Site Peer (Hub Side)

```ini
[Peer]
PublicKey = ...
AllowedIPs = <vpn_ip>/32, <routed_subnet>
```

Example:
```ini
AllowedIPs = 10.8.1.20/32, 192.168.0.0/24
```

---

### Human Peer (Hub Side)

```ini
[Peer]
PublicKey = ...
AllowedIPs = <vpn_ip>/32
```

---

### Human Peer (Client Side)

AllowedIPs derived from zones:

Example (Irene):
```ini
AllowedIPs = 10.1.1.0/24
```

---

## Enrolment Workflows

### Add a New Human Peer (e.g. Irene)

1. Add entry to `registry.yaml`
2. Create directory:
   ```bash
   mkdir wireguard/peers/irene
   ```
3. Generate keys:
   ```bash
   wg genkey | tee private.key | wg pubkey > public.key
   wg genpsk > preshared.key
   ```
4. Run generator:
   ```bash
   make wg
   ```
5. Deploy to MudPi:
   ```bash
   sudo cp wg0.conf /etc/wireguard/
   sudo systemctl restart wg-quick@wg0
   ```
6. Deliver client config:
   ```bash
   qrencode -t ansiutf8 < irene.conf
   ```

---

### Add a New Site Peer (e.g. BoatPi)

1. Add entry to `registry.yaml`
2. Define routed subnets:
   ```yaml
   routes:
     - 192.168.98.0/24
   ```
3. Generate keys
4. Generate configs
5. Deploy to both:
   - MudPi (hub)
   - BoatPi (peer)

---

## Naming Conventions

- Use lowercase names
- Use prefixes to imply ownership:
  - `sten-laptop`
  - `sten-phone`
- One device = one peer

---

## Security Model

- Private keys stored securely in repo (consider encryption later)
- Preshared keys used for additional security
- Clients use `PersistentKeepalive = 25`
- No inbound access required on client devices

---

## Summary

This architecture provides:

- Clear separation between routing and access
- Human-readable configuration
- Deterministic, reproducible deployments
- Scalable multi-site VPN design

---

## Future Enhancements

- Integrate with DNS registry
- Add firewall enforcement (iptables/nftables)
- Automate QR code generation
- Encrypt key material in repo

