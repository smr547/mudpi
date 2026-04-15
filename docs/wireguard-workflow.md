# WireGuard Workflow for MudPi

## Purpose

This workflow keeps WireGuard configuration under control by making `./wireguard/registry.yaml` the source of truth and generating runtime configuration from it.

The immediate goals are:

- MudPi becomes the hub
- site peers are declared explicitly
- human peers are declared explicitly
- key ownership is always traceable
- enrolling a new human peer is reproducible

---

## Repository Layout

```text
wireguard/
  registry.yaml
  generate_wg.py
  generated/
    wg0.conf
    clients/
      james-laptop.conf
  hub/
    mudpi/
      private.key
      public.key
  peers/
    shedpi/
      public.key
    sten-laptop/
      private.key
      public.key
      preshared.key
    sten-phone/
      private.key
      public.key
      preshared.key
    james-laptop/
      private.key
      public.key
      preshared.key
```

---

## Registry Semantics

### Hub

The `hub` section defines the WireGuard hub running on MudPi.

It includes:

- hub VPN address
- listen port
- endpoint presented to clients
- key location

### Zones

The `zones` section maps logical names such as `reid` and `farm` to real routed subnets.

### Site peers

A site peer is an infrastructure peer that advertises one or more routed LANs behind it.

Example:
- `shedpi` provides route to `192.168.0.0/24`

### Human peers

A human peer is a person/device profile that is granted access to one or more named zones.

Examples:
- `sten-laptop`
- `sten-phone`
- `james-laptop`

A human peer does not advertise routes.

---

## Generator Behaviour

`generate_wg.py` currently does two things:

1. Generates the hub config:
   - `wireguard/generated/wg0.conf`

2. Generates client configs for human peers whose key material exists:
   - `wireguard/generated/clients/<peer>.conf`

The generator reads `./wireguard/registry.yaml` and resolves:

- site peer `routes` into hub `AllowedIPs`
- human peer `access` into client `AllowedIPs`

---

## Minimal Operating Rules

1. Do not hand-edit `wireguard/generated/wg0.conf`
2. Do not hand-edit generated client configs
3. Update `wireguard/registry.yaml`
4. Add or rotate keys in the directory named by `key_ref`
5. Re-run the generator

---

## Existing Peer Workflow

For an existing peer whose keys are already known:

1. Ensure the peer exists in `wireguard/registry.yaml`
2. Ensure key files are in the directory named by `key_ref`
3. Run:
   ```bash
   cd <repo-root>
   python3 wireguard/generate_wg.py
   ```
4. Review generated output:
   ```bash
   ls wireguard/generated
   ls wireguard/generated/clients
   ```

---

## Human Peer Enrolment Workflow

This is the intended workflow for a new human peer such as `james-laptop`.

### 1. Add peer to the registry

Example:

```yaml
  - name: james-laptop
    peer_type: human
    vpn_address: 10.8.1.110
    access:
      - reid
      - farm
    description: James laptop
    key_ref: peers/james-laptop
    key_status: to-be-generated
    enrollment_status: pending
```

### 2. Create peer directory

```bash
mkdir -p wireguard/peers/james-laptop
chmod 700 wireguard/peers/james-laptop
```

### 3. Generate key material

```bash
wg genkey | tee wireguard/peers/james-laptop/private.key | wg pubkey > wireguard/peers/james-laptop/public.key
wg genpsk > wireguard/peers/james-laptop/preshared.key
chmod 600 wireguard/peers/james-laptop/private.key wireguard/peers/james-laptop/public.key wireguard/peers/james-laptop/preshared.key
```

### 4. Generate configs

```bash
cd <repo-root>
python3 wireguard/generate_wg.py
```

This should produce:

```text
wireguard/generated/wg0.conf
wireguard/generated/clients/james-laptop.conf
```

### 5. Install hub config on MudPi

```bash
sudo install -m 600 wireguard/generated/wg0.conf /etc/wireguard/wg0.conf
sudo systemctl restart wg-quick@wg0
```

### 6. Deliver James client config securely

Possible methods:

- copy `wireguard/generated/clients/james-laptop.conf` securely
- convert to QR code for mobile devices
- import manually into WireGuard client

For a phone:

```bash
qrencode -t ansiutf8 < wireguard/generated/clients/james-laptop.conf
```

### 7. Mark enrolment complete

Update the registry entry:

```yaml
    key_status: existing
    enrollment_status: complete
```

---

## Site Peer Workflow

A site peer such as `shedpi` differs from a human peer.

A site peer:

- has a routed subnet behind it
- appears in the hub config with both tunnel IP and routed LAN
- may later need its own generated peer-side config

Example hub output for `shedpi`:

```ini
AllowedIPs = 10.8.1.20/32, 192.168.0.0/24
```

---

## Current Scope of the Minimal Generator

This first version is intentionally small.

It currently assumes:

- one hub
- one registry file at `./wireguard/registry.yaml`
- DNS for clients is `10.1.1.3`
- client `AllowedIPs` are limited to declared zones only
- `PersistentKeepalive = 25` for human peers
- site peer side config generation is not yet implemented

---

## Recommended Next Steps

After this minimal generator is proven with `james-laptop`, likely next steps are:

1. generate site peer configs such as `shedpi.conf`
2. add Makefile targets
3. add validation checks
4. add QR-code helper output
5. separate private material from less sensitive generated output
6. optionally add firewall policy on MudPi as a second layer of enforcement
