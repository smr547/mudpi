#!/usr/bin/env python3
"""Discover live network devices and compare them with network-registry.yaml.

v3 goals:
- Correctly load the current MudPi registry schema:
    * hosts as a list of host objects
    * host identity from name/id/hostname
    * LAN IP from addresses.lan
    * VPN IP from addresses.vpn
    * MAC from top-level mac
- Parse arp-scan, ip -br neigh, nmap -sn output, optional dnsmasq leases, optional avahi browse output
- Merge observations by MAC address where possible
- Prefer stronger evidence sources when consolidating IP/vendor/hostname data
- Compare observations with registry hosts for a site
- Emit:
    * console summary
    * Markdown report
    * candidate YAML for unknown/changed devices
    * CSV summary

The registry remains authoritative. This tool proposes updates; it does not rewrite
network-registry.yaml.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import ipaddress
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required: pip install pyyaml") from exc


MAC_RE = re.compile(r"\b([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})\b")
IPV4_RE = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b")
HOST_SUFFIX_SANITIZE_RE = re.compile(r"[^a-z0-9]+")

SOURCE_PRIORITY = {
    "arp-scan": 100,
    "dhcp": 90,
    "avahi": 70,
    "ip-neigh": 50,
    "nmap": 40,
}

def source_rank(name: str) -> int:
    return SOURCE_PRIORITY.get(name, 0)


@dataclass
class ObservedDevice:
    mac: Optional[str] = None
    ips: Set[str] = field(default_factory=set)
    vendors: Set[str] = field(default_factory=set)
    hostnames: Set[str] = field(default_factory=set)
    mdns_names: Set[str] = field(default_factory=set)
    interfaces: Set[str] = field(default_factory=set)
    sources: Set[str] = field(default_factory=set)
    notes: Set[str] = field(default_factory=set)

    # evidence maps preserve source-specific values so we can prefer stronger sources
    ip_sources: Dict[str, Set[str]] = field(default_factory=dict)
    vendor_sources: Dict[str, Set[str]] = field(default_factory=dict)
    hostname_sources: Dict[str, Set[str]] = field(default_factory=dict)
    mdns_sources: Dict[str, Set[str]] = field(default_factory=dict)

    def add_ip(self, ip: str, source: str) -> None:
        if not ip:
            return
        self.ips.add(ip)
        self.ip_sources.setdefault(ip, set()).add(source)
        self.sources.add(source)

    def add_vendor(self, vendor: str, source: str) -> None:
        if not vendor:
            return
        self.vendors.add(vendor)
        self.vendor_sources.setdefault(vendor, set()).add(source)
        self.sources.add(source)

    def add_hostname(self, hostname: str, source: str) -> None:
        if not hostname:
            return
        self.hostnames.add(hostname)
        self.hostname_sources.setdefault(hostname, set()).add(source)
        self.sources.add(source)

    def add_mdns_name(self, name: str, source: str) -> None:
        if not name:
            return
        self.mdns_names.add(name)
        self.mdns_sources.setdefault(name, set()).add(source)
        self.sources.add(source)

    def merge(self, other: "ObservedDevice") -> None:
        if not self.mac and other.mac:
            self.mac = other.mac
        self.ips |= other.ips
        self.vendors |= other.vendors
        self.hostnames |= other.hostnames
        self.mdns_names |= other.mdns_names
        self.interfaces |= other.interfaces
        self.sources |= other.sources
        self.notes |= other.notes
        for key, values in other.ip_sources.items():
            self.ip_sources.setdefault(key, set()).update(values)
        for key, values in other.vendor_sources.items():
            self.vendor_sources.setdefault(key, set()).update(values)
        for key, values in other.hostname_sources.items():
            self.hostname_sources.setdefault(key, set()).update(values)
        for key, values in other.mdns_sources.items():
            self.mdns_sources.setdefault(key, set()).update(values)

    @property
    def mac_type(self) -> str:
        if not self.mac:
            return "unknown"
        first_octet = int(self.mac.split(":")[0], 16)
        if first_octet & 0b10:
            return "locally_administered"
        return "globally_administered"

    def best_ip(self) -> Optional[str]:
        if not self.ips:
            return None
        def key(ip: str) -> Tuple[int, int, str]:
            sources = self.ip_sources.get(ip, set())
            best = max((source_rank(s) for s in sources), default=0)
            return (best, len(sources), ip)
        return sorted(self.ips, key=key, reverse=True)[0]

    def best_vendor(self) -> Optional[str]:
        if not self.vendors:
            return None
        def key(vendor: str) -> Tuple[int, int, str]:
            sources = self.vendor_sources.get(vendor, set())
            best = max((source_rank(s) for s in sources), default=0)
            return (best, len(sources), vendor)
        return sorted(self.vendors, key=key, reverse=True)[0]


@dataclass
class RegistryHost:
    host_id: str
    site: Optional[str]
    description: str
    category: str
    roles: List[str]
    ipv4: Optional[str]
    vpn_ipv4: Optional[str]
    mac: Optional[str]
    dns_canonical: Optional[str]
    dns_aliases: List[str]
    raw: Dict[str, Any]


@dataclass
class ComparisonRow:
    status: str
    host_id: Optional[str]
    registry_ip: Optional[str]
    observed_ip: Optional[str]
    registry_mac: Optional[str]
    observed_mac: Optional[str]
    vendor: Optional[str]
    hostnames: List[str]
    mdns_names: List[str]
    notes: List[str]
    raw_registry: Optional[RegistryHost] = None
    raw_observed: Optional[ObservedDevice] = None


@dataclass
class ComparisonResult:
    matched: List[ComparisonRow] = field(default_factory=list)
    changed: List[ComparisonRow] = field(default_factory=list)
    unknown: List[ComparisonRow] = field(default_factory=list)
    missing: List[ComparisonRow] = field(default_factory=list)
    conflicts: List[ComparisonRow] = field(default_factory=list)


class DeviceIndex:
    def __init__(self) -> None:
        self.by_mac: Dict[str, ObservedDevice] = {}
        self.by_ip_without_mac: Dict[str, ObservedDevice] = {}

    def _upsert(self, device: ObservedDevice) -> None:
        if device.mac:
            entry = self.by_mac.setdefault(device.mac, ObservedDevice(mac=device.mac))
            entry.merge(device)
        else:
            # ignore records with neither MAC nor IP
            if not device.ips:
                return
            for ip in device.ips:
                entry = self.by_ip_without_mac.setdefault(ip, ObservedDevice())
                entry.merge(device)

    def merge(self, devices: Iterable[ObservedDevice]) -> None:
        for dev in devices:
            self._upsert(dev)

    def all_devices(self) -> List[ObservedDevice]:
        return list(self.by_mac.values()) + list(self.by_ip_without_mac.values())

    def find_by_ip(self, ip: str) -> Optional[ObservedDevice]:
        for dev in self.by_mac.values():
            if ip in dev.ips:
                return dev
        return self.by_ip_without_mac.get(ip)


def normalize_mac(mac: Optional[str]) -> Optional[str]:
    if not mac:
        return None
    mac = str(mac).strip().lower().replace("-", ":")
    if not MAC_RE.fullmatch(mac):
        return None
    return mac


def is_valid_ipv4(value: str) -> bool:
    try:
        ipaddress.IPv4Address(value)
        return True
    except Exception:
        return False


def normalize_hostname(name: str) -> str:
    return HOST_SUFFIX_SANITIZE_RE.sub("-", name.strip().lower()).strip("-")


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def timestamp_now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def _extract_addresses_mapping(host: Dict[str, Any]) -> Dict[str, Any]:
    addresses = host.get("addresses")
    if isinstance(addresses, dict):
        return addresses
    return {}


def extract_ipv4_and_mac(host: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    # Preferred/current MudPi shape
    addresses = _extract_addresses_mapping(host)
    lan_ip = addresses.get("lan")
    vpn_ip = addresses.get("vpn")
    if isinstance(lan_ip, dict):
        lan_ip = lan_ip.get("ipv4") or lan_ip.get("ip")
    if isinstance(vpn_ip, dict):
        vpn_ip = vpn_ip.get("ipv4") or vpn_ip.get("ip")

    # Backward-compatible fallbacks
    network = host.get("network")
    if (not lan_ip or not host.get("mac")) and isinstance(network, dict):
        lan = network.get("lan")
        if isinstance(lan, dict):
            lan_ip = lan_ip or lan.get("ipv4") or lan.get("ip")
            fallback_mac = lan.get("mac")
        else:
            fallback_mac = None
    else:
        fallback_mac = None

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
            name = str(item.get("name", "")).lower()
            if name == "lan":
                lan_ip = item.get("ipv4") or item.get("ip")
                fallback_mac = fallback_mac or item.get("mac")
                break

    if not lan_ip:
        lan_ip = host.get("ip") or host.get("ipv4")
    mac = normalize_mac(host.get("mac")) or normalize_mac(fallback_mac)

    if isinstance(lan_ip, str) and not is_valid_ipv4(lan_ip):
        lan_ip = None
    if isinstance(vpn_ip, str) and not is_valid_ipv4(vpn_ip):
        vpn_ip = None

    return lan_ip, vpn_ip, mac


def load_registry(path: Path) -> Tuple[Dict[str, Any], Dict[str, RegistryHost]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("Registry YAML must be a mapping at top level")
    hosts = data.get("hosts", {})
    if isinstance(hosts, dict):
        host_items = list(hosts.items())
    elif isinstance(hosts, list):
        host_items = []
        for idx, raw in enumerate(hosts):
            if not isinstance(raw, dict):
                continue
            host_id = raw.get("id") or raw.get("name") or raw.get("hostname")
            dns = raw.get("dns") if isinstance(raw.get("dns"), dict) else {}
            if not host_id and isinstance(dns.get("canonical"), str):
                host_id = str(dns["canonical"]).split(".", 1)[0]
            if not host_id:
                addresses = _extract_addresses_mapping(raw)
                fallback_ip = addresses.get("lan") or raw.get("ip") or raw.get("ipv4") or f"host-{idx+1}"
                host_id = f"host-{str(fallback_ip).replace('.', '-')}"
            host_items.append((str(host_id), raw))
    else:
        raise ValueError("Registry YAML 'hosts' must be a mapping or a list of host objects")

    loaded: Dict[str, RegistryHost] = {}
    seen_macs: Dict[str, str] = {}
    seen_ips: Dict[str, str] = {}

    for host_id, raw in host_items:
        if not isinstance(raw, dict):
            continue
        ipv4, vpn_ipv4, mac = extract_ipv4_and_mac(raw)
        dns = raw.get("dns", {}) if isinstance(raw.get("dns"), dict) else {}
        rh = RegistryHost(
            host_id=str(host_id),
            site=raw.get("site"),
            description=str(raw.get("description") or raw.get("notes") or ""),
            category=str(raw.get("category", "unknown")),
            roles=[str(x) for x in raw.get("roles", [])] if isinstance(raw.get("roles"), list) else [],
            ipv4=ipv4,
            vpn_ipv4=vpn_ipv4,
            mac=mac,
            dns_canonical=dns.get("canonical"),
            dns_aliases=[str(x) for x in dns.get("aliases", [])] if isinstance(dns.get("aliases"), list) else [],
            raw=raw,
        )
        loaded[rh.host_id] = rh

        if rh.mac:
            if rh.mac in seen_macs:
                raise ValueError(f"Duplicate MAC in registry: {rh.mac} on {seen_macs[rh.mac]} and {rh.host_id}")
            seen_macs[rh.mac] = rh.host_id
        if rh.ipv4:
            if rh.ipv4 in seen_ips:
                raise ValueError(f"Duplicate IPv4 in registry: {rh.ipv4} on {seen_ips[rh.ipv4]} and {rh.host_id}")
            seen_ips[rh.ipv4] = rh.host_id

    return data, loaded


def parse_arp_scan_text(text: str) -> List[ObservedDevice]:
    devices: List[ObservedDevice] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = re.split(r"\s+", line, maxsplit=2)
        if len(parts) < 2:
            continue
        ip, mac = parts[0], normalize_mac(parts[1])
        if not (is_valid_ipv4(ip) and mac):
            continue
        vendor = parts[2].strip() if len(parts) > 2 else ""
        dev = ObservedDevice(mac=mac)
        dev.add_ip(ip, "arp-scan")
        if vendor:
            dev.add_vendor(vendor, "arp-scan")
        devices.append(dev)
    return devices


def parse_ip_neigh_text(text: str) -> List[ObservedDevice]:
    devices: List[ObservedDevice] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        ip_match = IPV4_RE.search(line)
        mac_match = MAC_RE.search(line)
        if not ip_match:
            continue
        ip = ip_match.group(1)
        if not is_valid_ipv4(ip):
            continue
        dev = ObservedDevice(mac=normalize_mac(mac_match.group(1)) if mac_match else None)
        dev.add_ip(ip, "ip-neigh")
        parts = line.split()
        if len(parts) >= 2:
            dev.interfaces.add(parts[1])
        devices.append(dev)
    return devices


def parse_nmap_ping_scan_text(text: str) -> List[ObservedDevice]:
    devices: List[ObservedDevice] = []
    current_dev: Optional[ObservedDevice] = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("Nmap scan report for "):
            if current_dev:
                devices.append(current_dev)
            current_ip = line.rsplit(" ", 1)[-1]
            current_dev = ObservedDevice()
            if is_valid_ipv4(current_ip):
                current_dev.add_ip(current_ip, "nmap")
        elif line.startswith("MAC Address:") and current_dev:
            mac_match = MAC_RE.search(line)
            if mac_match:
                current_dev.mac = normalize_mac(mac_match.group(1))
            vendor_match = re.search(r"\((.*?)\)\s*$", line)
            if vendor_match:
                vendor = vendor_match.group(1).strip()
                if vendor:
                    current_dev.add_vendor(vendor, "nmap")
    if current_dev:
        devices.append(current_dev)
    return devices


def parse_dnsmasq_leases_text(text: str) -> List[ObservedDevice]:
    devices: List[ObservedDevice] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        _, mac, ip, hostname = parts[:4]
        if not is_valid_ipv4(ip):
            continue
        dev = ObservedDevice(mac=normalize_mac(mac))
        dev.add_ip(ip, "dhcp")
        if hostname != "*":
            dev.add_hostname(hostname, "dhcp")
        devices.append(dev)
    return devices


def parse_avahi_text(text: str) -> List[ObservedDevice]:
    devices: List[ObservedDevice] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        ip_matches = IPV4_RE.findall(line)
        if not ip_matches:
            continue
        ip = ip_matches[-1]
        if not is_valid_ipv4(ip):
            continue
        dev = ObservedDevice()
        dev.add_ip(ip, "avahi")
        m = re.search(r"=+\s*[^\[]*\[([^\]]+)\]", line)
        if m:
            dev.add_mdns_name(m.group(1), "avahi")
        devices.append(dev)
    return devices


def run_command(args: Sequence[str]) -> str:
    proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    return proc.stdout


def collect_live_inputs(cidr: str) -> Dict[str, str]:
    return {
        "arp-scan": run_command(["arp-scan", "--localnet"]),
        "ip-neigh": run_command(["ip", "-br", "neigh"]),
        "nmap": run_command(["nmap", "-sn", "-n", cidr]),
    }


def apply_overrides(index: DeviceIndex, overrides_path: Optional[Path]) -> None:
    if not overrides_path:
        return
    data = yaml.safe_load(overrides_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return
    overrides = data.get("overrides", data)
    if not isinstance(overrides, dict):
        return

    for key, payload in overrides.items():
        if not isinstance(payload, dict):
            continue
        mac = normalize_mac(str(key)) or normalize_mac(payload.get("mac"))
        target: Optional[ObservedDevice] = None
        if mac:
            target = index.by_mac.get(mac)
        else:
            ip = payload.get("ip")
            if isinstance(ip, str):
                target = index.find_by_ip(ip)
        if not target:
            continue
        hostname = payload.get("hostname") or payload.get("name")
        if isinstance(hostname, str) and hostname:
            target.add_hostname(hostname, "override")
        description = payload.get("description")
        if isinstance(description, str) and description:
            target.notes.add(description)
        for field_name in ("category", "role"):
            val = payload.get(field_name)
            if isinstance(val, str) and val:
                target.notes.add(f"{field_name}:{val}")


def compare_registry_to_observed(registry_hosts: Dict[str, RegistryHost], index: DeviceIndex, site: Optional[str] = None) -> ComparisonResult:
    result = ComparisonResult()
    matched_observed_ids: Set[str] = set()

    def observed_key(dev: ObservedDevice) -> str:
        return dev.mac or "|".join(sorted(dev.ips))

    filtered_registry = {
        host_id: host
        for host_id, host in registry_hosts.items()
        if site is None or host.site in (None, site)
    }

    for host in filtered_registry.values():
        dev: Optional[ObservedDevice] = None
        notes: List[str] = []
        if host.mac and host.mac in index.by_mac:
            dev = index.by_mac[host.mac]
        elif host.ipv4:
            dev = index.find_by_ip(host.ipv4)
            if dev:
                notes.append("matched by IP only")

        if not dev:
            result.missing.append(ComparisonRow(
                status="missing",
                host_id=host.host_id,
                registry_ip=host.ipv4,
                observed_ip=None,
                registry_mac=host.mac,
                observed_mac=None,
                vendor=None,
                hostnames=[],
                mdns_names=[],
                notes=["registry host not seen live"],
                raw_registry=host,
            ))
            continue

        matched_observed_ids.add(observed_key(dev))
        observed_ip = dev.best_ip()
        observed_mac = dev.mac
        vendor = dev.best_vendor()

        if host.mac and observed_mac and host.mac != observed_mac:
            notes.append("MAC mismatch")
        if host.ipv4 and observed_ip and host.ipv4 != observed_ip:
            notes.append("IPv4 differs from registry")
        if dev.mac_type == "locally_administered":
            notes.append("locally administered MAC")
        if len(dev.ips) > 1:
            notes.append("multiple observed IPs")
        if len({ip for ip in dev.ips if is_valid_ipv4(ip)}) > 1:
            notes.append("check stale IP observations")

        row = ComparisonRow(
            status="changed" if notes else "matched",
            host_id=host.host_id,
            registry_ip=host.ipv4,
            observed_ip=observed_ip,
            registry_mac=host.mac,
            observed_mac=observed_mac,
            vendor=vendor,
            hostnames=sorted(dev.hostnames),
            mdns_names=sorted(dev.mdns_names),
            notes=sorted(set(notes)),
            raw_registry=host,
            raw_observed=dev,
        )
        if notes:
            result.changed.append(row)
        else:
            result.matched.append(row)

    for dev in index.all_devices():
        if observed_key(dev) in matched_observed_ids:
            continue
        observed_ip = dev.best_ip()
        vendor = dev.best_vendor()
        notes: List[str] = []
        if dev.mac_type == "locally_administered":
            notes.append("locally administered MAC")
        if len(dev.ips) > 1:
            notes.append("multiple observed IPs")
        result.unknown.append(ComparisonRow(
            status="unknown",
            host_id=None,
            registry_ip=None,
            observed_ip=observed_ip,
            registry_mac=None,
            observed_mac=dev.mac,
            vendor=vendor,
            hostnames=sorted(dev.hostnames),
            mdns_names=sorted(dev.mdns_names),
            notes=sorted(set(notes + list(dev.notes))),
            raw_observed=dev,
        ))

    return result


def emit_console_summary(result: ComparisonResult) -> None:
    print(f"Matched : {len(result.matched)}")
    print(f"Changed : {len(result.changed)}")
    print(f"Unknown : {len(result.unknown)}")
    print(f"Missing : {len(result.missing)}")
    print(f"Conflicts: {len(result.conflicts)}")


def _markdown_table(headers: List[str], rows: List[List[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


def emit_markdown_report(result: ComparisonResult, path: Path, site: str, cidr: str, generated_at: str) -> None:
    sections: List[str] = []
    sections.append(f"# Network Discovery Report\n\nDate: {generated_at}\n\nSite: {site}\n\nCIDR: {cidr}\n")
    sections.append(
        "## Summary\n\n"
        f"- Matched: {len(result.matched)}\n"
        f"- Changed: {len(result.changed)}\n"
        f"- Unknown: {len(result.unknown)}\n"
        f"- Missing: {len(result.missing)}\n"
        f"- Conflicts: {len(result.conflicts)}\n"
    )

    def rows_from(items: List[ComparisonRow]) -> List[List[str]]:
        rows: List[List[str]] = []
        for r in items:
            rows.append([
                r.host_id or "",
                r.registry_ip or "",
                r.observed_ip or "",
                r.registry_mac or "",
                r.observed_mac or "",
                r.vendor or "",
                ", ".join(r.hostnames),
                ", ".join(r.mdns_names),
                "; ".join(r.notes),
            ])
        return rows

    headers = ["Host", "Registry IP", "Observed IP", "Registry MAC", "Observed MAC", "Vendor", "Hostnames", "mDNS", "Notes"]
    for title, items in [("Changed", result.changed), ("Unknown", result.unknown), ("Missing", result.missing), ("Matched", result.matched)]:
        sections.append(f"## {title}\n")
        sections.append(_markdown_table(headers, rows_from(items)) if items else "None.\n")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n\n".join(sections) + "\n", encoding="utf-8")


def suggested_host_id(row: ComparisonRow) -> str:
    for candidate in row.hostnames + row.mdns_names:
        clean = normalize_hostname(candidate.replace(".local", ""))
        if clean:
            return clean
    if row.observed_ip:
        return f"unknown-{row.observed_ip.replace('.', '-')}"
    if row.observed_mac:
        return f"unknown-{row.observed_mac.replace(':', '')[-6:]}"
    return "unknown-device"


def classify_vendor(vendor: Optional[str]) -> str:
    if not vendor:
        return "unknown"
    v = vendor.lower()
    if "ubiquiti" in v:
        return "network"
    if "dahua" in v:
        return "camera"
    if "sonos" in v or "apple" in v or "samsung" in v:
        return "media"
    if "brother" in v or "cloud network technology" in v:
        return "printer"
    if "espressif" in v or "microchip" in v or "arduino" in v:
        return "iot"
    if "raspberry pi" in v:
        return "server"
    return "unknown"


def emit_candidate_yaml(result: ComparisonResult, path: Path, site: str, generated_at: str) -> None:
    candidates: Dict[str, Any] = {"generated_at": generated_at, "site": site, "candidates": {}}
    for row in result.unknown + result.changed:
        host_id = row.host_id or suggested_host_id(row)
        candidates["candidates"][host_id] = {
            "status": row.status,
            "suggested_entry": {
                "site": site,
                "description": "Auto-discovered device" if not row.notes else "; ".join(row.notes),
                "category": classify_vendor(row.vendor),
                "mac": row.observed_mac or row.registry_mac,
                "addresses": {"lan": row.observed_ip or row.registry_ip},
                "discovery": {
                    "vendor": row.vendor,
                    "observed_hostnames": row.hostnames,
                    "mdns_names": row.mdns_names,
                    "last_seen": generated_at,
                },
            },
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(candidates, sort_keys=False, allow_unicode=True), encoding="utf-8")


def emit_csv(result: ComparisonResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["status", "host_id", "registry_ip", "observed_ip", "registry_mac", "observed_mac", "vendor", "hostnames", "mdns_names", "notes"])
        for status_name, items in [("matched", result.matched), ("changed", result.changed), ("unknown", result.unknown), ("missing", result.missing), ("conflict", result.conflicts)]:
            for r in items:
                writer.writerow([status_name, r.host_id or "", r.registry_ip or "", r.observed_ip or "", r.registry_mac or "", r.observed_mac or "", r.vendor or "", ", ".join(r.hostnames), ", ".join(r.mdns_names), "; ".join(r.notes)])


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Discover live network devices and compare with network-registry.yaml")
    p.add_argument("--registry", required=True, help="Path to network-registry.yaml")
    p.add_argument("--site", required=True, help="Site key, e.g. reid")
    p.add_argument("--cidr", required=True, help="Target CIDR, e.g. 10.1.1.0/24")
    p.add_argument("--arp-scan-file")
    p.add_argument("--ip-neigh-file")
    p.add_argument("--nmap-file")
    p.add_argument("--dhcp-leases-file")
    p.add_argument("--avahi-file")
    p.add_argument("--overrides")
    p.add_argument("--report-md", default="generate/discovery-report.md")
    p.add_argument("--report-yaml", default="generate/discovered-hosts.yaml")
    p.add_argument("--report-csv", default="generate/discovery.csv")
    p.add_argument("--live", action="store_true", help="Collect live arp-scan/ip-neigh/nmap data")
    return p.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        ipaddress.ip_network(args.cidr, strict=False)
    except ValueError as exc:
        print(f"Invalid CIDR: {args.cidr}: {exc}", file=sys.stderr)
        return 2

    registry_path = Path(args.registry)
    if not registry_path.exists():
        print(f"Registry not found: {registry_path}", file=sys.stderr)
        return 2

    try:
        _, registry_hosts = load_registry(registry_path)
    except Exception as exc:
        print(f"Failed to load registry: {exc}", file=sys.stderr)
        return 2

    index = DeviceIndex()
    generated_at = timestamp_now()

    try:
        if args.live:
            live_outputs = collect_live_inputs(args.cidr)
            index.merge(parse_arp_scan_text(live_outputs.get("arp-scan", "")))
            index.merge(parse_ip_neigh_text(live_outputs.get("ip-neigh", "")))
            index.merge(parse_nmap_ping_scan_text(live_outputs.get("nmap", "")))
        if args.arp_scan_file:
            index.merge(parse_arp_scan_text(load_text(Path(args.arp_scan_file))))
        if args.ip_neigh_file:
            index.merge(parse_ip_neigh_text(load_text(Path(args.ip_neigh_file))))
        if args.nmap_file:
            index.merge(parse_nmap_ping_scan_text(load_text(Path(args.nmap_file))))
        if args.dhcp_leases_file:
            index.merge(parse_dnsmasq_leases_text(load_text(Path(args.dhcp_leases_file))))
        if args.avahi_file:
            index.merge(parse_avahi_text(load_text(Path(args.avahi_file))))
    except FileNotFoundError as exc:
        print(f"Input file not found: {exc}", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as exc:
        print(f"Live discovery command failed: {exc}", file=sys.stderr)
        return 2

    apply_overrides(index, Path(args.overrides) if args.overrides else None)
    result = compare_registry_to_observed(registry_hosts, index, site=args.site)
    emit_console_summary(result)
    emit_markdown_report(result, Path(args.report_md), args.site, args.cidr, generated_at)
    emit_candidate_yaml(result, Path(args.report_yaml), args.site, generated_at)
    emit_csv(result, Path(args.report_csv))
    print(f"Markdown report: {args.report_md}")
    print(f"Candidate YAML : {args.report_yaml}")
    print(f"CSV summary    : {args.report_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
