#!/usr/bin/env python3
"""Generate dnsmasq DNS snippets from network-registry.yaml.

This version keeps the original publication policy while adding a small amount
of structure for multi-site authoritative DNS.

Key additions over the baseline:
- Optional site domain selection via --domain (otherwise inferred from --site)
- Optional zone config generation (zone.conf) for authoritative local zones
- Optional generated hosts file (authoritative.hosts) for addn-hosts/expand-hosts
- Optional interface binding lines in zone.conf for site-local resolvers
- Retains address=/name/ip and ptr-record output for deployments that prefer the
  original generated-snippet style

Typical usage
-------------
Farm resolver (ShedPi), authoritative locally for farm.home.arpa:
    generate_dnsmasq.py \
      --registry docs/reference/network-registry.yaml \
      --site barkingowl \
      --domain farm.home.arpa \
      --interfaces eth0,wg0 \
      --mode hosts-file

Global resolver (MudPi), authoritative for replicated farm.home.arpa data:
    generate_dnsmasq.py \
      --registry docs/reference/network-registry.yaml \
      --site barkingowl \
      --domain farm.home.arpa \
      --mode address

Publication policy
------------------
- Canonical DNS publication prefers addresses.lan
- Falls back to addresses.wifi
- Falls back to legacy ip/ipv4 forms if needed
- VPN aliases (*.vpn.home.arpa) use addresses.vpn
- PTR generation uses the same canonical publication address
- mac / macs are inventory details only and are ignored by DNS publication
"""

from __future__ import annotations

import argparse
import ipaddress
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required: pip install pyyaml") from exc

HOST_SUFFIX_SANITIZE_RE = re.compile(r"[^a-z0-9-]+")


def is_valid_ipv4(value: Optional[str]) -> bool:
    if not value:
        return False
    try:
        ipaddress.IPv4Address(str(value))
        return True
    except Exception:
        return False


def normalize_label(name: str) -> str:
    cleaned = HOST_SUFFIX_SANITIZE_RE.sub("-", name.strip().lower()).strip("-")
    return cleaned or "unnamed-host"


def _extract_addresses_mapping(host: Dict[str, Any]) -> Dict[str, Any]:
    addresses = host.get("addresses")
    return addresses if isinstance(addresses, dict) else {}


def extract_dns_service_ip(host: Dict[str, Any]) -> Tuple[Optional[str], str]:
    addresses = _extract_addresses_mapping(host)

    lan_ip = addresses.get("lan")
    wifi_ip = addresses.get("wifi")

    if isinstance(lan_ip, dict):
        lan_ip = lan_ip.get("ipv4") or lan_ip.get("ip")
    if isinstance(wifi_ip, dict):
        wifi_ip = wifi_ip.get("ipv4") or wifi_ip.get("ip")

    if isinstance(lan_ip, str) and is_valid_ipv4(lan_ip):
        return lan_ip, "lan"
    if isinstance(wifi_ip, str) and is_valid_ipv4(wifi_ip):
        return wifi_ip, "wifi"

    candidate = host.get("ip") or host.get("ipv4")
    if isinstance(candidate, str) and is_valid_ipv4(candidate):
        return candidate, "legacy"

    return None, "none"


def extract_vpn_ip(host: Dict[str, Any]) -> Optional[str]:
    addresses = _extract_addresses_mapping(host)
    vpn_ip = addresses.get("vpn")
    if isinstance(vpn_ip, dict):
        vpn_ip = vpn_ip.get("ipv4") or vpn_ip.get("ip")
    if isinstance(vpn_ip, str) and is_valid_ipv4(vpn_ip):
        return vpn_ip
    return None


def load_registry(path: Path) -> List[Dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("Registry YAML must be a mapping at top level")
    hosts = data.get("hosts", {})
    if isinstance(hosts, list):
        out: List[Dict[str, Any]] = []
        for item in hosts:
            if not isinstance(item, dict):
                continue
            if any(k in item for k in ("name", "id", "hostname")):
                out.append(item)
                continue
            if len(item) == 1:
                only_key = next(iter(item.keys()))
                only_val = item[only_key]
                if isinstance(only_val, dict):
                    clone = dict(only_val)
                    clone.setdefault("name", str(only_key))
                    out.append(clone)
                    continue
            out.append(item)
        return out
    if isinstance(hosts, dict):
        out = []
        for key, value in hosts.items():
            if isinstance(value, dict):
                clone = dict(value)
                clone.setdefault("name", str(key))
                out.append(clone)
        return out
    raise ValueError("Registry YAML 'hosts' must be a list or mapping")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def ptr_name(ip: str) -> str:
    octets = ip.split(".")
    return ".".join(reversed(octets)) + ".in-addr.arpa"


def infer_domain(site: Optional[str]) -> Optional[str]:
    if not site:
        return None
    mapping = {
        "reid": "reid.home.arpa",
        "barkingowl": "farm.home.arpa",
        "trilogy": "trilogy.home.arpa",
        "testboat": "testboat.home.arpa",
        "vpn": "vpn.home.arpa",
    }
    return mapping.get(site)


def parse_interfaces(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate dnsmasq DNS config from network-registry.yaml")
    p.add_argument("--registry", required=True, help="Path to network-registry.yaml")
    p.add_argument("--site", help="Optional site filter, e.g. reid")
    p.add_argument("--domain", help="Authoritative zone domain, e.g. farm.home.arpa")
    p.add_argument("--outdir", default="generated/dnsmasq", help="Output directory")
    p.add_argument("--install-root", help="Base directory for dnsmasq deployment (used to emit absolute paths)",)
    p.add_argument(
        "--mode",
        choices=("address", "hosts-file", "both"),
        default="both",
        help="Output style: address records, generated hosts file, or both",
    )
    p.add_argument(
        "--interfaces",
        help="Optional comma-separated interfaces for zone.conf, e.g. eth0,wg0",
    )
    p.add_argument(
        "--no-bind-interfaces",
        action="store_true",
        help="Do not emit bind-interfaces into zone.conf",
    )
    p.add_argument("--stdout", action="store_true", help="Also print generated files to stdout")
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    registry_path = Path(args.registry)
    if not registry_path.exists():
        print(f"Registry not found: {registry_path}", file=sys.stderr)
        return 2

    try:
        hosts = load_registry(registry_path)
    except Exception as exc:
        print(f"Failed to load registry: {exc}", file=sys.stderr)
        return 2

    domain = (args.domain or infer_domain(args.site) or "home.arpa").strip().lower()
    interfaces = parse_interfaces(args.interfaces)

    hosts_lines: List[str] = [
        "# This file is generated. Edit network-registry.yaml and rerun the generator.",
        f"# Registry: {registry_path}",
        f"# Site filter: {args.site or '(none)'}",
        f"# Domain: {domain}",
        "",
    ]
    authoritative_hosts_lines: List[str] = [
        "# This file is generated. Edit network-registry.yaml and rerun the generator.",
        f"# Registry: {registry_path}",
        f"# Site filter: {args.site or '(none)'}",
        f"# Domain: {domain}",
        "",
    ]
    aliases_lines: List[str] = [
        "# This file is generated. Edit network-registry.yaml and rerun the generator.",
        f"# Registry: {registry_path}",
        f"# Site filter: {args.site or '(none)'}",
        f"# Domain: {domain}",
        "",
    ]
    reverse_lines: List[str] = [
        "# This file is generated. Edit network-registry.yaml and rerun the generator.",
        f"# Registry: {registry_path}",
        f"# Site filter: {args.site or '(none)'}",
        f"# Domain: {domain}",
        "",
    ]
    zone_lines: List[str] = [
        "# This file is generated. Edit network-registry.yaml and rerun the generator.",
        f"# Registry: {registry_path}",
        f"# Site filter: {args.site or '(none)'}",
        f"# Domain: {domain}",
        "",
        f"domain={domain}",
        f"local=/{domain}/",
        "expand-hosts",
    ]
    for iface in interfaces:
        zone_lines.append(f"interface={iface}")
    if interfaces and not args.no_bind_interfaces:
        zone_lines.append("bind-interfaces")

    if args.install_root and args.site:
        base = f"{args.install_root}/{args.site}"
        zone_lines.append(f"addn-hosts={base}/authoritative.hosts")
        zone_lines.append(f"conf-file={base}/aliases.conf")
        zone_lines.append(f"conf-file={base}/reverse.conf")
    else:
        zone_lines.append("addn-hosts=authoritative.hosts")
        zone_lines.append("conf-file=aliases.conf")
        zone_lines.append("conf-file=reverse.conf")
    zone_lines.append("")
    
    warnings: List[str] = []
    forward_records: Dict[str, Tuple[str, str]] = {}
    reverse_records: Dict[str, str] = {}
    authoritative_rows: Dict[str, List[str]] = {}

    for raw in hosts:
        if args.site is not None and raw.get("site") not in (None, args.site):
            continue

        host_id = str(raw.get("id") or raw.get("name") or raw.get("hostname") or "unnamed-host")
        dns = raw.get("dns") if isinstance(raw.get("dns"), dict) else {}
        canonical = dns.get("canonical")
        aliases = dns.get("aliases") if isinstance(dns.get("aliases"), list) else []
        service_ip, address_kind = extract_dns_service_ip(raw)
        vpn_ip = extract_vpn_ip(raw)

        if not canonical:
            warnings.append(f"Host {host_id}: skipped because dns.canonical is missing")
            continue
        if not isinstance(canonical, str):
            warnings.append(f"Host {host_id}: skipped because dns.canonical is not a string")
            continue
        if not service_ip:
            warnings.append(
                f"Host {host_id}: skipped because neither addresses.lan nor addresses.wifi is usable for DNS publication"
            )
            continue

        canonical_name = canonical.strip().lower()
        canonical_domain = canonical_name.split(".", 1)[1] if "." in canonical_name else ""
        if canonical_domain != domain:
            warnings.append(
                f"Host {host_id}: skipped because canonical domain {canonical_domain or '(none)'} does not match requested domain {domain}"
            )
            continue

        short_name = normalize_label(canonical_name.split(".", 1)[0])
        authoritative_rows.setdefault(service_ip, [])
        for name in (canonical_name, short_name):
            if name not in authoritative_rows[service_ip]:
                authoritative_rows[service_ip].append(name)

        def add_forward(name: str, ip: str, source: str) -> None:
            existing = forward_records.get(name)
            if existing and existing[0] != ip:
                warnings.append(
                    f"Forward-name conflict for {name}: {existing[0]} ({existing[1]}) vs {ip} ({source})"
                )
                return
            forward_records[name] = (ip, source)

        add_forward(canonical_name, service_ip, f"{host_id} canonical ({address_kind})")
        add_forward(short_name, service_ip, f"{host_id} short-name ({address_kind})")

        for alias in aliases:
            if not isinstance(alias, str):
                continue
            alias_name = alias.strip().lower()
            alias_ip = vpn_ip if alias_name.endswith(".vpn.home.arpa") and vpn_ip else service_ip
            add_forward(alias_name, alias_ip, f"{host_id} alias")
            if alias_ip == service_ip and alias_name.endswith(f".{domain}"):
                authoritative_rows.setdefault(service_ip, [])
                if alias_name not in authoritative_rows[service_ip]:
                    authoritative_rows[service_ip].append(alias_name)

        ptr = ptr_name(service_ip)
        existing_ptr = reverse_records.get(ptr)
        if existing_ptr and existing_ptr != canonical_name:
            warnings.append(f"Reverse-name conflict for {ptr}: {existing_ptr} vs {canonical_name}")
        else:
            reverse_records[ptr] = canonical_name

    for name in sorted(forward_records.keys()):
        ip, source = forward_records[name]
        if "canonical" in source or "short-name" in source:
            hosts_lines.append(f"# {source}")
            hosts_lines.append(f"address=/{name}/{ip}")
        else:
            aliases_lines.append(f"# {source}")
            aliases_lines.append(f"address=/{name}/{ip}")

    for ip in sorted(authoritative_rows.keys(), key=lambda x: tuple(int(o) for o in x.split("."))):
        names = authoritative_rows[ip]
        authoritative_hosts_lines.append(f"{ip} {' '.join(names)}")

    for ptr in sorted(reverse_records.keys()):
        reverse_lines.append(f"ptr-record={ptr},{reverse_records[ptr]}")

    outdir = Path(args.outdir)
    write_text(outdir / "hosts.conf", "\n".join(hosts_lines) + "\n")
    write_text(outdir / "authoritative.hosts", "\n".join(authoritative_hosts_lines) + "\n")
    write_text(outdir / "aliases.conf", "\n".join(aliases_lines) + "\n")
    write_text(outdir / "reverse.conf", "\n".join(reverse_lines) + "\n")
    write_text(outdir / "zone.conf", "\n".join(zone_lines) + "\n")

    warnings_text = [
        "# generator warnings",
        f"# Generated from: {registry_path}",
        f"# Site filter: {args.site or '(none)'}",
        f"# Domain: {domain}",
        "# This file is generated. Edit network-registry.yaml instead.",
        "",
    ]
    warnings_text.extend(warnings if warnings else ["No warnings."])
    write_text(outdir / "warnings_dns.txt", "\n".join(warnings_text) + "\n")

    summary_lines = [
        "# dns publication summary",
        f"# Registry: {registry_path}",
        f"# Site filter: {args.site or '(none)'}",
        f"# Domain: {domain}",
        "",
    ]
    for ip in sorted(authoritative_rows.keys(), key=lambda x: tuple(int(o) for o in x.split("."))):
        summary_lines.append(f"{ip:15}  {' '.join(authoritative_rows[ip])}")
    write_text(outdir / "summary.txt", "\n".join(summary_lines) + "\n")

    if args.stdout:
        for name in ("zone.conf", "authoritative.hosts", "aliases.conf", "reverse.conf", "hosts.conf"):
            print(f"=== {name} ===")
            print((outdir / name).read_text(encoding="utf-8"))

    print(f"Generated: {outdir / 'zone.conf'}")
    print(f"Generated: {outdir / 'authoritative.hosts'}")
    print(f"Generated: {outdir / 'aliases.conf'}")
    print(f"Generated: {outdir / 'reverse.conf'}")
    print(f"Generated: {outdir / 'hosts.conf'}")
    print(f"Generated: {outdir / 'summary.txt'}")
    print(f"Warnings : {outdir / 'warnings_dns.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
