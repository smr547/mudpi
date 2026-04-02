#!/usr/bin/env python3
"""Generate dnsmasq configuration snippets from MudPi network-registry.yaml.

Generator policy
================
This script intentionally follows a conservative DNS publication policy so the
registry can become authoritative in stages without accidentally publishing
incidental or unstable addresses.

The current policy is:

1. Canonical LAN A records
   - Generate canonical forward records from ``dns.canonical`` to
     ``addresses.lan``.
   - Also generate a short-name record from the first label of the canonical
     hostname to ``addresses.lan``. Example:
       mudpi.reid.home.arpa -> 10.1.1.3
       mudpi                -> 10.1.1.3

2. Alias A records
   - Generate alias records from ``dns.aliases``.
   - If an alias ends with ``.vpn.home.arpa``, publish it to ``addresses.vpn``.
   - Otherwise, publish aliases to ``addresses.lan``.
   - This lets a host expose an explicit VPN alias such as
       mudpi.vpn.home.arpa -> 10.8.1.1
     while keeping ordinary aliases on the LAN address.

3. Reverse DNS / PTR records
   - Generate PTR records only for ``addresses.lan``.
   - Reverse DNS for VPN is deliberately omitted at this stage.

4. Wi-Fi and other incidental addresses
   - Ignore ``addresses.wifi`` and any non-LAN/non-VPN addresses for DNS
     publication by default.
   - The registry may still record those addresses for inventory and discovery,
     but they are not published into authoritative DNS unless policy changes
     later.

5. Multi-homed devices
   - ``mac`` and ``macs`` are inventory/discovery concerns only.
   - They are intentionally ignored by this generator.

6. Scope filtering
   - A ``--site`` filter can be used so you can generate only the records for a
     specific site, for example ``reid``.

Output files
============
The script writes three dnsmasq snippet files:

- hosts.conf   : canonical forward records and short names
- aliases.conf : explicit aliases
- reverse.conf : PTR records for LAN addresses

The files are suitable for installation into ``/etc/dnsmasq.d/``.
"""
from __future__ import annotations

import argparse
import ipaddress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required: pip install pyyaml") from exc


@dataclass
class RegistryHost:
    host_id: str
    site: Optional[str]
    addresses: Dict[str, str] = field(default_factory=dict)
    dns_canonical: Optional[str] = None
    dns_aliases: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def lan_ip(self) -> Optional[str]:
        return self.addresses.get("lan")

    @property
    def vpn_ip(self) -> Optional[str]:
        return self.addresses.get("vpn")


def is_valid_ipv4(value: Any) -> bool:
    try:
        ipaddress.IPv4Address(str(value))
        return True
    except Exception:
        return False


def normalize_fqdn(name: str) -> str:
    return str(name).strip().lower().rstrip(".")


def canonical_short_name(fqdn: str) -> str:
    return normalize_fqdn(fqdn).split(".", 1)[0]


def ptr_name_for_ipv4(ip: str) -> str:
    return ipaddress.IPv4Address(ip).reverse_pointer


def _extract_addresses_mapping(host: Dict[str, Any]) -> Dict[str, Any]:
    addresses = host.get("addresses")
    if isinstance(addresses, dict):
        return addresses
    return {}


def _coerce_ip(value: Any) -> Optional[str]:
    if isinstance(value, dict):
        value = value.get("ipv4") or value.get("ip")
    if value is None:
        return None
    value = str(value).strip()
    return value if is_valid_ipv4(value) else None


def extract_addresses(host: Dict[str, Any]) -> Dict[str, str]:
    """Extract addresses in a backward-compatible way.

    Preferred schema is top-level ``addresses`` such as:

        addresses:
          lan: 10.1.1.3
          wifi: 10.1.1.129
          vpn: 10.8.1.1

    Older fallback layouts are tolerated where practical, but DNS generation is
    still intentionally limited to the published-policy keys of ``lan`` and
    ``vpn``.
    """
    out: Dict[str, str] = {}

    addresses = _extract_addresses_mapping(host)
    for key, value in addresses.items():
        ip = _coerce_ip(value)
        if ip:
            out[str(key).strip().lower()] = ip

    # Backward-compatible fallbacks for older schemas.
    network = host.get("network")
    if isinstance(network, dict):
        lan = network.get("lan")
        if "lan" not in out:
            ip = _coerce_ip(lan)
            if ip:
                out["lan"] = ip

    interfaces = host.get("interfaces")
    if isinstance(interfaces, dict):
        if "lan" not in out:
            ip = _coerce_ip(interfaces.get("lan"))
            if ip:
                out["lan"] = ip
    elif isinstance(interfaces, list):
        for item in interfaces:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip().lower()
            if name and name not in out:
                ip = _coerce_ip(item)
                if ip:
                    out[name] = ip

    if "lan" not in out:
        ip = _coerce_ip(host.get("ip") or host.get("ipv4"))
        if ip:
            out["lan"] = ip

    return out


def load_registry(path: Path) -> Tuple[Dict[str, Any], List[RegistryHost]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("Registry YAML must be a mapping at top level")

    hosts = data.get("hosts", {})
    host_items: List[Tuple[str, Dict[str, Any]]] = []

    if isinstance(hosts, dict):
        for host_id, raw in hosts.items():
            if isinstance(raw, dict):
                host_items.append((str(host_id), raw))
    elif isinstance(hosts, list):
        for idx, raw in enumerate(hosts):
            if not isinstance(raw, dict):
                continue
            host_id = raw.get("id") or raw.get("name") or raw.get("hostname")
            dns = raw.get("dns") if isinstance(raw.get("dns"), dict) else {}
            if not host_id and isinstance(dns.get("canonical"), str):
                host_id = normalize_fqdn(dns["canonical"]).split(".", 1)[0]
            if not host_id:
                host_id = f"host-{idx+1}"
            host_items.append((str(host_id), raw))
    else:
        raise ValueError("Registry YAML 'hosts' must be a mapping or a list of host objects")

    loaded: List[RegistryHost] = []
    for host_id, raw in host_items:
        addresses = extract_addresses(raw)
        dns = raw.get("dns") if isinstance(raw.get("dns"), dict) else {}
        canonical = dns.get("canonical") if isinstance(dns.get("canonical"), str) else None
        aliases = dns.get("aliases") if isinstance(dns.get("aliases"), list) else []
        loaded.append(
            RegistryHost(
                host_id=host_id,
                site=raw.get("site"),
                addresses=addresses,
                dns_canonical=normalize_fqdn(canonical) if canonical else None,
                dns_aliases=[normalize_fqdn(x) for x in aliases if isinstance(x, str) and x.strip()],
                raw=raw,
            )
        )
    return data, loaded


def iter_site_hosts(hosts: Iterable[RegistryHost], site: Optional[str]) -> Iterable[RegistryHost]:
    for host in hosts:
        if site is None or host.site in (None, site):
            yield host


def generate_records(hosts: Iterable[RegistryHost]) -> Tuple[List[str], List[str], List[str], List[str]]:
    hosts_conf: List[str] = []
    aliases_conf: List[str] = []
    reverse_conf: List[str] = []
    warnings: List[str] = []

    seen_forward: Dict[str, str] = {}
    seen_ptr: Dict[str, str] = {}

    def add_unique_forward(name: str, ip: str, bucket: List[str], context: str) -> None:
        key = f"{name}|{ip}"
        if key in seen_forward:
            return
        # Also catch same name pointing somewhere else; that is a policy conflict.
        for seen_key, seen_context in seen_forward.items():
            seen_name, seen_ip = seen_key.split("|", 1)
            if seen_name == name and seen_ip != ip:
                warnings.append(
                    f"Forward-name conflict for {name}: {seen_ip} ({seen_context}) vs {ip} ({context})"
                )
                return
        seen_forward[key] = context
        bucket.append(f"address=/{name}/{ip}")

    def add_unique_ptr(ip: str, fqdn: str, context: str) -> None:
        ptr_name = ptr_name_for_ipv4(ip)
        existing = seen_ptr.get(ptr_name)
        if existing and existing != fqdn:
            warnings.append(
                f"PTR conflict for {ip} ({ptr_name}): {existing} vs {fqdn} ({context})"
            )
            return
        seen_ptr[ptr_name] = fqdn
        reverse_conf.append(f"ptr-record={ptr_name},{fqdn}")

    for host in hosts:
        lan_ip = host.lan_ip
        vpn_ip = host.vpn_ip
        canonical = host.dns_canonical

        if not canonical:
            warnings.append(f"Host {host.host_id}: skipped because dns.canonical is missing")
            continue
        if not lan_ip:
            warnings.append(f"Host {host.host_id}: skipped because addresses.lan is missing")
            continue

        # Policy: canonical name publishes to LAN address only.
        add_unique_forward(canonical, lan_ip, hosts_conf, f"{host.host_id} canonical")

        # Policy: publish short-name convenience record from canonical first label.
        short_name = canonical_short_name(canonical)
        add_unique_forward(short_name, lan_ip, hosts_conf, f"{host.host_id} short-name")

        # Policy: only LAN gets PTR at this stage.
        add_unique_ptr(lan_ip, canonical, f"{host.host_id} lan")

        # Policy: aliases normally point to LAN; explicit *.vpn.home.arpa aliases point to VPN.
        for alias in host.dns_aliases:
            target_ip = lan_ip
            if alias.endswith(".vpn.home.arpa"):
                if vpn_ip:
                    target_ip = vpn_ip
                else:
                    warnings.append(
                        f"Host {host.host_id}: alias {alias} ends with .vpn.home.arpa but addresses.vpn is missing"
                    )
                    continue
            add_unique_forward(alias, target_ip, aliases_conf, f"{host.host_id} alias")

    return hosts_conf, aliases_conf, reverse_conf, warnings


def render_header(title: str, registry_path: Path, site: Optional[str]) -> List[str]:
    lines = [
        f"# {title}",
        f"# Generated from: {registry_path}",
        f"# Site filter: {site if site else 'all'}",
        "# This file is generated. Edit network-registry.yaml instead.",
        "",
    ]
    return lines


def write_lines(path: Path, header_lines: List[str], body_lines: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(header_lines + sorted(body_lines) + [""])
    path.write_text(text, encoding="utf-8")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate dnsmasq snippets from network-registry.yaml")
    p.add_argument("--registry", required=True, help="Path to network-registry.yaml")
    p.add_argument("--site", help="Optional site filter, e.g. reid")
    p.add_argument("--outdir", default="generate/dnsmasq", help="Output directory for dnsmasq snippets")
    p.add_argument("--stdout", action="store_true", help="Also print generated content to stdout")
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    registry_path = Path(args.registry)
    if not registry_path.exists():
        raise SystemExit(f"Registry not found: {registry_path}")

    _, hosts = load_registry(registry_path)
    filtered_hosts = list(iter_site_hosts(hosts, args.site))
    hosts_conf, aliases_conf, reverse_conf, warnings = generate_records(filtered_hosts)

    outdir = Path(args.outdir)
    hosts_path = outdir / "hosts.conf"
    aliases_path = outdir / "aliases.conf"
    reverse_path = outdir / "reverse.conf"
    warnings_path = outdir / "warnings.txt"

    write_lines(hosts_path, render_header("dnsmasq canonical/short-name records", registry_path, args.site), hosts_conf)
    write_lines(aliases_path, render_header("dnsmasq alias records", registry_path, args.site), aliases_conf)
    write_lines(reverse_path, render_header("dnsmasq reverse PTR records", registry_path, args.site), reverse_conf)
    write_lines(warnings_path, render_header("generator warnings", registry_path, args.site), warnings)

    print(f"Wrote {hosts_path}")
    print(f"Wrote {aliases_path}")
    print(f"Wrote {reverse_path}")
    print(f"Wrote {warnings_path}")
    print(f"Hosts processed: {len(filtered_hosts)}")
    print(f"Warnings: {len(warnings)}")

    if args.stdout:
        for label, lines in (
            ("hosts.conf", hosts_conf),
            ("aliases.conf", aliases_conf),
            ("reverse.conf", reverse_conf),
        ):
            print(f"\n### {label} ###")
            for line in sorted(lines):
                print(line)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
