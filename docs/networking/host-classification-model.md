
## Host Classification Model

Each host in `network-registry.yaml` is described using three complementary fields:

- `category`
- `roles`
- `addressing`

Together these fields describe **what a device is**, **what it does**, and **how it is connected to the network**.

### Category

The `category` field provides a **broad, stable classification** for the device.

Examples:

| Category | Meaning |
|--------|--------|
| `infrastructure` | core network control-plane systems |
| `server` | hosts running application services |
| `energy` | solar or EV energy management devices |
| `appliance` | self-contained network appliances |
| `sensor` | data collection devices |
| `client` | user-operated or roaming devices |

Categories are intentionally **few in number and rarely change**.

They are primarily used for:

- documentation
- inventory summaries
- diagram grouping
- future monitoring or policy grouping

---

### Roles

The `roles` field describes **what the device actually does**.

A host may have **multiple roles**.

Examples:

```yaml
roles: [wireguard-hub, dns, dhcp, ntp-stratum1]
```

Roles provide the operational detail that categories intentionally avoid.

Typical roles include:

- `dns`
- `dhcp`
- `wireguard-hub`
- `signalk`
- `grafana`
- `solar-monitor`
- `ev-charger`
- `print-server`

Roles may evolve over time as systems gain or lose functionality.

---

### Addressing

The `addressing` field defines **how the host receives its IP address**.

| Addressing Mode | Meaning |
|----------------|--------|
| `static-on-host` | IP configured directly on the device |
| `dhcp-reservation` | DHCP lease tied to MAC address |
| `dhcp-dynamic` | address assigned from dynamic pool |
| `wireguard-static` | fixed VPN overlay address |

Addressing describes **network behaviour**, not device purpose.

---

### Example

```yaml
- name: mudpi
  site: reid
  category: infrastructure
  addressing: static-on-host
  addresses:
    lan: 10.1.1.10
    vpn: 10.8.1.1
  roles:
    - wireguard-hub
    - dns
    - dhcp
    - ntp-stratum1
```

Interpretation:

- **category**: infrastructure node
- **roles**: provides DNS, DHCP, VPN, and time services
- **addressing**: statically configured IP addresses

---

### Design Philosophy

The MudPi registry separates these concerns deliberately:

| Field | Purpose |
|-----|-----|
| `category` | high-level classification |
| `roles` | functional capabilities |
| `addressing` | network configuration behaviour |

This separation keeps the schema **simple, expressive, and stable as the network grows**.
