# Network Registry Workflow

Author: Steven Ring
System: MudPi Infrastructure

## Purpose

The authoritative source of network configuration is:

    docs/reference/network-registry.yaml

All DNS, DHCP, reverse DNS, documentation, discovery reports, and future infrastructure tooling derive their information from this registry.

The registry is the source of truth.

Generated files must never be edited manually.

## Standard Workflow

1. Edit `docs/reference/network-registry.yaml`
2. Run:

```bash
make preflight-dnsmasq
```

3. Resolve any warnings.
4. Deploy:

```bash
make deploy-reid-dnsmasq
# or
make deploy-farm-dnsmasq
```

5. Verify DNS and DHCP operation.

## Useful Make Targets

### DNS / DHCP

```bash
make preflight-dnsmasq
make build-dnsmasq
make deploy-reid-dnsmasq
make deploy-farm-dnsmasq
```

### Discovery

```bash
make network-census
make arp-report
make unifi-clients
```

### Lease Reporting

```bash
make leases-report
make leases-report-verbose
make leases-unknown-stubs
make farm-leases-unknown-stubs
```

## Address Allocation Policy

### Reid

- DHCP reservations: 10.1.1.100 – 10.1.1.199
- Dynamic DHCP pool: 10.1.1.200 – 10.1.1.249

### Farm

- DHCP reservations: 192.168.0.100 – 192.168.0.229
- Dynamic DHCP pool: 192.168.0.230 – 192.168.0.249

## Operational Principles

1. The registry is authoritative.
2. Generated files are disposable.
3. DNS and DHCP configuration must never be edited manually.
4. All changes flow through the registry.
5. Preflight validation should be performed before deployment.
6. Successful deployment should be verified using DNS and DHCP tests.
