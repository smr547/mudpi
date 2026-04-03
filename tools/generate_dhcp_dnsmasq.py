#!/usr/bin/env python3
"""Generate dnsmasq DHCP configuration from network-registry.yaml.

Policy (deliberately conservative)
----------------------------------
This generator is intended for a staged migration from ad-hoc/router DHCP
reservations to registry-driven DHCP on MudPi.

Current policy:
- Generate ONE dnsmasq dhcp.conf file.
- Emit the global DHCP service settings:
    * interface=<chosen interface>
    * bind-interfaces
    * dhcp-authoritative
    * dhcp-range=<configured pool>
    * dhcp-option router=<gateway>
    * dhcp-option dns-server=<MudPi DNS>
    * dhcp-option domain-search=<site domain>
    * domain=<site domain>,<cidr>
- Emit fixed leases ONLY for hosts that have:
    * a MAC address (top-level mac or top-level macs mapping), AND
    * an addresses.lan IPv4 address
- For multi-homed hosts, choose a single preferred MAC for DHCP generation,
  using this priority:
    ethernet, lan, wifi, wlan, primary, fallback, then first available key.
- The generated hostname for dhcp-host is the host identity (name/id/hostname)
  normalised to a dns-safe lowercase label.
- Hosts without a usable MAC or LAN IPv4 are skipped and written to warnings.txt.
- This generator does NOT try to infer dynamic-host identity for privacy-preserving
  devices (e.g. Apple phones using private Wi-Fi addresses). Those devices should
  remain dynamic unless you explicitly choose to model them differently later.
- This generator does NOT rewrite the registry. It only emits dnsmasq config.
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


def extract_lan_ip_and_macs(host: Dict[str, Any]) -> Tuple[Optional[str], Dict[str, str]]:
    addresses = _extract_addresses_mapping(host)
    lan_ip = addresses.get("lan")
    if isinstance(lan_ip, dict):
        lan_ip = lan_ip.get("ipv4") or lan_ip.get("ip")

    fallback_mac = None

    network = host.get("network")
    if (not lan_ip or (not host.get("mac") and not host.get("macs"))) and isinstance(network, dict):
        lan = network.get("lan")
        if isinstance(lan, dict):
            lan_ip = lan_ip or lan.get("ipv4") or lan.get("ip")
            fallback_mac = lan.get("mac")

    interfaces = host.get("interfaces")
    if not lan_ip and isinstance(interfaces, dict):
        lan = interfaces.get("lan")
        if isinstance(lan, dict):
            lan_ip = lan.get("ipv4") or lan.get("ip")
            fallback_mac = fallback_mac or lan.get("mac")
    elif not lan_ip and isinstance(interfaces, list):
        for item in interfaces:
            if not isinstance(item, dict):
                continue
            if str(item.get("name", "")).lower() == "lan":
                lan_ip = item.get("ipv4") or item.get("ip")
                fallback_mac = fallback_mac or item.get("mac")
                break

    if not lan_ip:
        lan_ip = host.get("ip") or host.get("ipv4")

    macs = extract_host_macs(host, fallback_mac=fallback_mac)

    if isinstance(lan_ip, str) and not is_valid_ipv4(lan_ip):
        lan_ip = None

    return lan_ip, macs


@dataclass
class LeaseCandidate:
    host_id: str
    hostname: str
    lan_ip: str
    mac_key: str
    mac: str


def load_registry(path: Path) -> List[Dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("Registry YAML must be a mapping at top level")
    hosts = data.get("hosts", {})
    if isinstance(hosts, list):
        return [h for h in hosts if isinstance(h, dict)]
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
        lan_ip, macs = extract_lan_ip_and_macs(raw)
        chosen = preferred_mac(macs)

        if not lan_ip:
            warnings.append(f"Host {host_id}: skipped because addresses.lan is missing or invalid")
            continue
        if not chosen:
            warnings.append(f"Host {host_id}: skipped because no usable MAC was found")
            continue

        mac_key, mac = chosen

        if lan_ip in seen_ips:
            warnings.append(
                f"Host {host_id}: skipped because LAN IP {lan_ip} duplicates host {seen_ips[lan_ip]}"
            )
            continue
        if mac in seen_macs:
            warnings.append(
                f"Host {host_id}: skipped because MAC {mac} duplicates host {seen_macs[mac]}"
            )
            continue

        seen_ips[lan_ip] = host_id
        seen_macs[mac] = host_id
        candidates.append(LeaseCandidate(host_id=host_id, hostname=hostname, lan_ip=lan_ip, mac_key=mac_key, mac=mac))

    candidates.sort(key=lambda c: tuple(int(x) for x in c.lan_ip.split(".")))
    return candidates, warnings


def build_dhcp_conf(
    interface: str,
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
) -> str:
    lines: List[str] = []
    lines.append("# This file is generated. Edit network-registry.yaml and rerun the generator.")
    lines.append(f"# Registry: {registry_path}")
    lines.append(f"# Site filter: {site or '(none)'}")
    lines.append("#")
    lines.append("# Generation policy:")
    lines.append("# - DHCP served only on the chosen interface")
    lines.append("# - Fixed leases generated only for hosts with a usable MAC and addresses.lan")
    lines.append("# - One preferred MAC is chosen for multi-homed hosts")
    lines.append("# - Privacy-preserving/mobile devices should usually remain dynamic unless deliberately modelled")
    lines.append("")
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
        lines.append(f"# {c.host_id} ({c.mac_key})")
        lines.append(f"dhcp-host={c.mac},{c.hostname},{c.lan_ip}")
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
    p.add_argument("--interface", default="eth0", help="LAN interface for DHCP service")
    p.add_argument("--cidr", required=True, help="LAN CIDR, e.g. 10.1.1.0/24")
    p.add_argument("--range-start", required=True, help="DHCP pool start, e.g. 10.1.1.100")
    p.add_argument("--range-end", required=True, help="DHCP pool end, e.g. 10.1.1.199")
    p.add_argument("--router", required=True, help="Default gateway IP, e.g. 10.1.1.1")
    p.add_argument("--dns-server", required=True, help="DNS server advertised by DHCP, e.g. 10.1.1.3")
    p.add_argument("--domain", required=True, help="Search/default domain, e.g. reid.home.arpa")
    p.add_argument("--lease-time", default="12h", help="Lease time, e.g. 12h")
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

    dhcp_conf = build_dhcp_conf(
        interface=args.interface,
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
        summary_lines.append(f"{c.lan_ip:15}  {c.mac:17}  {c.hostname:20}  ({c.host_id}, {c.mac_key})")
    write_text(outdir / "leases-summary.txt", "\n".join(summary_lines) + "\n")

    if args.stdout:
        print(dhcp_conf)

    print(f"Generated: {outdir / 'dhcp.conf'}")
    print(f"Warnings : {outdir / 'warnings.txt'}")
    print(f"Summary  : {outdir / 'leases-summary.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
