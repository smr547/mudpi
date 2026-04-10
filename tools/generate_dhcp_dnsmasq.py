#!/usr/bin/env python3
"""Generate dnsmasq DHCP configuration from network-registry.yaml.

This version preserves the baseline behaviour and adds two small but useful
capabilities for a staged multi-site rollout:
- optional interface binding list via --extra-interface
- optional dhcp-host tagging by site role/category for easier future policy use

Policy remains conservative:
- Generate ONE dnsmasq dhcp.conf file.
- Emit the global DHCP service settings.
- Emit fixed leases ONLY for hosts that have a MAC and a usable service IPv4.
- Address preference remains lan, then wifi, then legacy forms.
- One preferred MAC is chosen for multi-homed hosts.
"""

from __future__ import annotations

import argparse
import ipaddress
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required: pip install pyyaml") from exc

HOST_SUFFIX_SANITIZE_RE = re.compile(r"[^a-z0-9-]+")
MAC_RE = re.compile(r"^[0-9a-f]{2}(?::[0-9a-f]{2}){5}$")


def normalize_mac(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    mac = str(value).strip().lower().replace("-", ":")
    return mac if MAC_RE.fullmatch(mac) else None


def is_valid_ipv4(value: Optional[str]) -> bool:
    if not value:
        return False
    try:
        ipaddress.IPv4Address(str(value))
        return True
    except Exception:
        return False


def normalize_hostname(name: str) -> str:
    cleaned = HOST_SUFFIX_SANITIZE_RE.sub("-", name.strip().lower()).strip("-")
    return cleaned or "unnamed-host"


def normalize_tag(value: str) -> str:
    return normalize_hostname(value).replace("-", "_")


def _extract_addresses_mapping(host: Dict[str, Any]) -> Dict[str, Any]:
    addresses = host.get("addresses")
    return addresses if isinstance(addresses, dict) else {}


def extract_host_macs(host: Dict[str, Any], fallback_mac: Optional[str] = None) -> Dict[str, str]:
    extracted: Dict[str, str] = {}

    macs = host.get("macs")
    if isinstance(macs, dict):
        for key, value in macs.items():
            mac = normalize_mac(value)
            if mac:
                extracted[str(key)] = mac

    top_mac = normalize_mac(host.get("mac"))
    if top_mac and top_mac not in extracted.values():
        extracted.setdefault("primary", top_mac)

    fb = normalize_mac(fallback_mac)
    if fb and fb not in extracted.values():
        extracted.setdefault("fallback", fb)

    return extracted


def preferred_mac(macs: Dict[str, str]) -> Optional[Tuple[str, str]]:
    for key in ("ethernet", "lan", "wifi", "wlan", "primary", "fallback"):
        if key in macs:
            return key, macs[key]
    if macs:
        key = next(iter(macs.keys()))
        return key, macs[key]
    return None


def extract_service_ip_and_macs(host: Dict[str, Any]) -> Tuple[Optional[str], str, Dict[str, str]]:
    addresses = _extract_addresses_mapping(host)

    lan_ip = addresses.get("lan")
    wifi_ip = addresses.get("wifi")

    if isinstance(lan_ip, dict):
        lan_ip = lan_ip.get("ipv4") or lan_ip.get("ip")
    if isinstance(wifi_ip, dict):
        wifi_ip = wifi_ip.get("ipv4") or wifi_ip.get("ip")

    chosen_ip: Optional[str] = None
    address_kind = "legacy"
    fallback_mac = None

    if isinstance(lan_ip, str) and is_valid_ipv4(lan_ip):
        chosen_ip = lan_ip
        address_kind = "lan"
    elif isinstance(wifi_ip, str) and is_valid_ipv4(wifi_ip):
        chosen_ip = wifi_ip
        address_kind = "wifi"

    network = host.get("network")
    if not chosen_ip and isinstance(network, dict):
        lan = network.get("lan")
        if isinstance(lan, dict):
            candidate = lan.get("ipv4") or lan.get("ip")
            if isinstance(candidate, str) and is_valid_ipv4(candidate):
                chosen_ip = candidate
                address_kind = "legacy"
                fallback_mac = lan.get("mac")

    interfaces = host.get("interfaces")
    if not chosen_ip and isinstance(interfaces, dict):
        lan = interfaces.get("lan")
        if isinstance(lan, dict):
            candidate = lan.get("ipv4") or lan.get("ip")
            if isinstance(candidate, str) and is_valid_ipv4(candidate):
                chosen_ip = candidate
                address_kind = "legacy"
                fallback_mac = fallback_mac or lan.get("mac")
    elif not chosen_ip and isinstance(interfaces, list):
        for item in interfaces:
            if not isinstance(item, dict):
                continue
            if str(item.get("name", "")).lower() == "lan":
                candidate = item.get("ipv4") or item.get("ip")
                if isinstance(candidate, str) and is_valid_ipv4(candidate):
                    chosen_ip = candidate
                    address_kind = "legacy"
                    fallback_mac = fallback_mac or item.get("mac")
                    break

    if not chosen_ip:
        candidate = host.get("ip") or host.get("ipv4")
        if isinstance(candidate, str) and is_valid_ipv4(candidate):
            chosen_ip = candidate
            address_kind = "legacy"

    macs = extract_host_macs(host, fallback_mac=fallback_mac)
    return chosen_ip, address_kind, macs


@dataclass
class LeaseCandidate:
    host_id: str
    hostname: str
    ip: str
    address_kind: str
    mac_key: str
    mac: str
    category: str
    roles: List[str]


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
        out: List[Dict[str, Any]] = []
        for key, value in hosts.items():
            if isinstance(value, dict):
                clone = dict(value)
                clone.setdefault("name", str(key))
                out.append(clone)
        return out
    raise ValueError("Registry YAML 'hosts' must be a list or mapping")


def collect_candidates(hosts: Iterable[Dict[str, Any]], site: Optional[str]) -> Tuple[List[LeaseCandidate], List[str]]:
    candidates: List[LeaseCandidate] = []
    warnings: List[str] = []
    seen_ips: Dict[str, str] = {}
    seen_macs: Dict[str, str] = {}

    for raw in hosts:
        if site is not None and raw.get("site") not in (None, site):
            continue

        host_id = str(raw.get("id") or raw.get("name") or raw.get("hostname") or "unnamed-host")
        hostname = normalize_hostname(host_id)
        service_ip, address_kind, macs = extract_service_ip_and_macs(raw)
        chosen = preferred_mac(macs)

        if not service_ip:
            warnings.append(f"Host {host_id}: skipped because neither addresses.lan nor addresses.wifi is usable")
            continue
        if not chosen:
            warnings.append(f"Host {host_id}: skipped because no usable MAC was found")
            continue

        mac_key, mac = chosen

        if service_ip in seen_ips:
            warnings.append(
                f"Host {host_id}: skipped because service IP {service_ip} duplicates host {seen_ips[service_ip]}"
            )
            continue
        if mac in seen_macs:
            warnings.append(
                f"Host {host_id}: skipped because MAC {mac} duplicates host {seen_macs[mac]}"
            )
            continue

        seen_ips[service_ip] = host_id
        seen_macs[mac] = host_id
        roles = raw.get("roles") if isinstance(raw.get("roles"), list) else []
        category = str(raw.get("category") or "uncategorized")
        candidates.append(
            LeaseCandidate(
                host_id=host_id,
                hostname=hostname,
                ip=service_ip,
                address_kind=address_kind,
                mac_key=mac_key,
                mac=mac,
                category=category,
                roles=[str(r) for r in roles if isinstance(r, (str, int, float))],
            )
        )

    candidates.sort(key=lambda c: tuple(int(x) for x in c.ip.split(".")))
    return candidates, warnings


def build_dhcp_conf(
    interfaces: List[str],
    cidr: str,
    range_start: str,
    range_end: str,
    lease_time: str,
    router: str,
    dns_server: str,
    domain: str,
    candidates: List[LeaseCandidate],
    registry_path: Path,
    site: Optional[str],
    emit_tags: bool,
) -> str:
    lines: List[str] = []
    lines.append("# This file is generated. Edit network-registry.yaml and rerun the generator.")
    lines.append(f"# Registry: {registry_path}")
    lines.append(f"# Site filter: {site or '(none)'}")
    lines.append("#")
    lines.append("# Generation policy:")
    lines.append("# - DHCP served only on the chosen interfaces")
    lines.append("# - Fixed leases generated only for hosts with a usable MAC and a usable service IP")
    lines.append("# - Address preference is lan, then wifi, then legacy forms")
    lines.append("# - One preferred MAC is chosen for multi-homed hosts")
    lines.append("")
    for interface in interfaces:
        lines.append(f"interface={interface}")
    lines.append("bind-interfaces")
    lines.append("dhcp-authoritative")
    lines.append("")
    lines.append(f"dhcp-range={range_start},{range_end},{ipaddress.ip_network(cidr, strict=False).netmask},{lease_time}")
    lines.append(f"dhcp-option=option:router,{router}")
    lines.append(f"dhcp-option=option:dns-server,{dns_server}")
    lines.append(f"dhcp-option=option:domain-search,{domain}")
    lines.append(f"domain={domain},{cidr}")
    lines.append("")
    lines.append("# Fixed leases generated from registry")
    for c in candidates:
        lines.append(f"# {c.host_id} ({c.mac_key}, {c.address_kind}, category={c.category})")
        tag_prefix = ""
        if emit_tags:
            tags = [f"set:{normalize_tag(c.category)}"] + [f"set:{normalize_tag(role)}" for role in c.roles]
            tag_prefix = ",".join(tags) + "," if tags else ""
        lines.append(f"dhcp-host={tag_prefix}{c.mac},{c.hostname},{c.ip}")
    lines.append("")
    return "\n".join(lines)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate dnsmasq DHCP config from network-registry.yaml")
    p.add_argument("--registry", required=True, help="Path to network-registry.yaml")
    p.add_argument("--site", help="Optional site filter, e.g. reid")
    p.add_argument("--outdir", default="generate/dhcp", help="Output directory")
    p.add_argument("--interface", default="eth0", help="Primary LAN interface for DHCP service")
    p.add_argument("--extra-interface", action="append", default=[], help="Additional interface(s) to bind")
    p.add_argument("--cidr", required=True, help="LAN CIDR, e.g. 10.1.1.0/24")
    p.add_argument("--range-start", required=True, help="DHCP pool start, e.g. 10.1.1.100")
    p.add_argument("--range-end", required=True, help="DHCP pool end, e.g. 10.1.1.199")
    p.add_argument("--router", required=True, help="Default gateway IP, e.g. 10.1.1.1")
    p.add_argument("--dns-server", required=True, help="DNS server advertised by DHCP, e.g. 10.1.1.3")
    p.add_argument("--domain", required=True, help="Search/default domain, e.g. reid.home.arpa")
    p.add_argument("--lease-time", default="12h", help="Lease time, e.g. 12h")
    p.add_argument("--emit-tags", action="store_true", help="Add set:<tag> markers from category/roles")
    p.add_argument("--stdout", action="store_true", help="Also print dhcp.conf to stdout")
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    try:
        ipaddress.ip_network(args.cidr, strict=False)
        ipaddress.IPv4Address(args.range_start)
        ipaddress.IPv4Address(args.range_end)
        ipaddress.IPv4Address(args.router)
        ipaddress.IPv4Address(args.dns_server)
    except ValueError as exc:
        print(f"Invalid IP/CIDR input: {exc}", file=sys.stderr)
        return 2

    registry_path = Path(args.registry)
    if not registry_path.exists():
        print(f"Registry not found: {registry_path}", file=sys.stderr)
        return 2

    try:
        hosts = load_registry(registry_path)
        candidates, warnings = collect_candidates(hosts, args.site)
    except Exception as exc:
        print(f"Failed to load or process registry: {exc}", file=sys.stderr)
        return 2

    interfaces = [args.interface] + [i for i in args.extra_interface if i and i != args.interface]
    dhcp_conf = build_dhcp_conf(
        interfaces=interfaces,
        cidr=args.cidr,
        range_start=args.range_start,
        range_end=args.range_end,
        lease_time=args.lease_time,
        router=args.router,
        dns_server=args.dns_server,
        domain=args.domain,
        candidates=candidates,
        registry_path=registry_path,
        site=args.site,
        emit_tags=args.emit_tags,
    )

    outdir = Path(args.outdir)
    write_text(outdir / "dhcp.conf", dhcp_conf)

    warnings_text = [
        "# generator warnings",
        f"# Generated from: {registry_path}",
        f"# Site filter: {args.site or '(none)'}",
        "# This file is generated. Edit network-registry.yaml instead.",
        "",
    ]
    warnings_text.extend(warnings if warnings else ["No warnings."])
    write_text(outdir / "warnings.txt", "\n".join(warnings_text) + "\n")

    summary_lines = [
        "# generated lease summary",
        f"# Registry: {registry_path}",
        f"# Site filter: {args.site or '(none)'}",
        "",
    ]
    for c in candidates:
        summary_lines.append(
            f"{c.ip:15}  {c.mac:17}  {c.hostname:20}  ({c.host_id}, {c.mac_key}, {c.address_kind}, {c.category})"
        )
    write_text(outdir / "leases-summary.txt", "\n".join(summary_lines) + "\n")

    if args.stdout:
        print(dhcp_conf)

    print(f"Generated: {outdir / 'dhcp.conf'}")
    print(f"Warnings : {outdir / 'warnings.txt'}")
    print(f"Summary  : {outdir / 'leases-summary.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
