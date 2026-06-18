#!/usr/bin/env python3
"""
validate_registry_v3_1.py

Validator for the MudPi network registry.

v3.1 features
-------------
- Current-schema validation from v2
- Registry statistics summary
- Generated/emitted DNS collision detection
- Cleaner output suitable for Makefile integration

The registry is the source of truth. Generated files should not be edited.
"""

from __future__ import annotations

import argparse
import ipaddress
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, DefaultDict, Dict, Iterable, List, Optional, Set, Tuple

import yaml


FQDN_RE = re.compile(
    r"^(?=.{1,253}\.?$)(?!-)[A-Za-z0-9-]+(\.(?!-)[A-Za-z0-9-]+)+\.?$"
)

SHORT_NAME_RE = re.compile(
    r"^[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?$"
)

MAC_RE = re.compile(r"^[0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){5}$")

ALLOWED_ADDRESSING = {
    "static",
    "static-on-host",
    "dhcp-reservation",
    "dhcp-reserved",
    "dynamic",
    "manual",
    "unknown",
    "reserved",
    "wireguard-static",
}

DHCP_RESERVATION_MODES = {
    "dhcp-reservation",
    "dhcp-reserved",
}

STATIC_MODES = {
    "static",
    "static-on-host",
    "wireguard-static",
}

ADDRESS_KEYS = {
    "lan",
    "wifi",
    "vpn",
}


@dataclass(frozen=True)
class DnsEmission:
    name: str
    owner_host: str
    source: str
    site: str
    kind: str


class Reporter:
    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def add_info(self, msg: str) -> None:
        self.info.append(msg)

    def print(self, *, show_info: bool = False) -> None:
        for e in self.errors:
            print(f"ERROR: {e}")
        for w in self.warnings:
            print(f"WARNING: {w}")
        if show_info:
            for i in self.info:
                print(f"INFO: {i}")
        print()
        print(f"Summary: {len(self.errors)} error(s), {len(self.warnings)} warning(s)")


def load_yaml(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"YAML load error: {e}", file=sys.stderr)
        sys.exit(2)

    if data is None:
        return {}

    if not isinstance(data, dict):
        print("YAML root must be a mapping", file=sys.stderr)
        sys.exit(2)

    return data


def norm_fqdn(value: str) -> str:
    return value.rstrip(".").lower()


def is_fqdn(value: Any) -> bool:
    return isinstance(value, str) and bool(FQDN_RE.match(value))


def is_short_name(value: Any) -> bool:
    return isinstance(value, str) and bool(SHORT_NAME_RE.match(value))


def is_mac(value: Any) -> bool:
    return isinstance(value, str) and bool(MAC_RE.match(value))


def parse_ip(value: Any) -> Optional[ipaddress.IPv4Address]:
    if not isinstance(value, str):
        return None
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return None
    return ip if isinstance(ip, ipaddress.IPv4Address) else None


def parse_network(value: Any) -> Optional[ipaddress.IPv4Network]:
    if not isinstance(value, str):
        return None
    try:
        net = ipaddress.ip_network(value, strict=False)
    except ValueError:
        return None
    return net if isinstance(net, ipaddress.IPv4Network) else None


def private_root(registry: Dict[str, Any]) -> str:
    value = registry.get("meta", {}).get("private_root", "home.arpa")
    if not isinstance(value, str) or not value.strip():
        return "home.arpa"
    return norm_fqdn(value)


def site_zone(site_name: str, site: Dict[str, Any], root: str) -> str:
    zone = site.get("zone")
    if isinstance(zone, str) and zone.strip():
        return norm_fqdn(zone)
    return f"{site_name}.{root}".lower()


def site_lan_cidr(site: Dict[str, Any]) -> Optional[str]:
    lan = site.get("lan")
    if isinstance(lan, dict):
        cidr = lan.get("cidr") or lan.get("network")
        if isinstance(cidr, str):
            return cidr

    cidr = site.get("cidr") or site.get("network")
    if isinstance(cidr, str):
        return cidr

    return None


def site_dhcp_config(site: Dict[str, Any]) -> Dict[str, Any]:
    dhcp = site.get("dhcp")
    return dhcp if isinstance(dhcp, dict) else {}


def site_has_no_dhcp(site: Dict[str, Any]) -> bool:
    dhcp = site_dhcp_config(site)
    return dhcp.get("mode") == "none"


def dhcp_pool(site: Dict[str, Any]) -> Tuple[Optional[ipaddress.IPv4Address], Optional[ipaddress.IPv4Address]]:
    dhcp = site_dhcp_config(site)

    dynamic_pool = dhcp.get("dynamic_pool")
    if isinstance(dynamic_pool, dict):
        return parse_ip(dynamic_pool.get("start")), parse_ip(dynamic_pool.get("end"))

    start = (
        dhcp.get("range_start")
        or dhcp.get("range-start")
        or dhcp.get("pool_start")
        or dhcp.get("pool-start")
        or dhcp.get("start")
    )
    end = (
        dhcp.get("range_end")
        or dhcp.get("range-end")
        or dhcp.get("pool_end")
        or dhcp.get("pool-end")
        or dhcp.get("end")
    )

    return parse_ip(start), parse_ip(end)


def iter_hosts(registry: Dict[str, Any]) -> Iterable[Tuple[int, Dict[str, Any]]]:
    hosts = registry.get("hosts", [])
    if not isinstance(hosts, list):
        return []
    return [(i, h) for i, h in enumerate(hosts) if isinstance(h, dict)]


def host_label(host: Dict[str, Any], idx: int) -> str:
    return str(host.get("name") or f"hosts[{idx}]")


def host_addresses(host: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}

    addresses = host.get("addresses")
    if isinstance(addresses, dict):
        for key, value in addresses.items():
            if isinstance(value, str) and value.strip():
                out[str(key)] = value.strip()

    for legacy_key in ("ip", "ipv4"):
        value = host.get(legacy_key)
        if isinstance(value, str) and value.strip() and "lan" not in out:
            out["lan"] = value.strip()

    return out


def host_macs(host: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}

    mac = host.get("mac")
    if isinstance(mac, str) and mac.strip():
        out["primary"] = mac.strip().lower()

    macs = host.get("macs")
    if isinstance(macs, dict):
        for key, value in macs.items():
            if isinstance(value, str) and value.strip():
                out[str(key)] = value.strip().lower()

    return out


def emitted_dns_name(alias_or_fqdn: str) -> str:
    value = alias_or_fqdn.strip().lower()
    if "." in value:
        return norm_fqdn(value)
    return value


def host_explicit_dns_names(host: Dict[str, Any]) -> List[Tuple[str, str]]:
    names: List[Tuple[str, str]] = []

    dns = host.get("dns")
    if not isinstance(dns, dict):
        return names

    canonical = dns.get("canonical")
    if isinstance(canonical, str) and canonical.strip():
        names.append((emitted_dns_name(canonical), "dns.canonical"))

    aliases = dns.get("aliases")
    if isinstance(aliases, list):
        for i, alias in enumerate(aliases):
            if isinstance(alias, str) and alias.strip():
                names.append((emitted_dns_name(alias), f"dns.aliases[{i}]"))

    interfaces = dns.get("interfaces")
    if isinstance(interfaces, dict):
        for ifname, ifdns in interfaces.items():
            if not isinstance(ifdns, dict):
                continue
            if_canonical = ifdns.get("canonical")
            if isinstance(if_canonical, str) and if_canonical.strip():
                names.append((emitted_dns_name(if_canonical), f"dns.interfaces.{ifname}.canonical"))
            if_aliases = ifdns.get("aliases")
            if isinstance(if_aliases, list):
                for j, alias in enumerate(if_aliases):
                    if isinstance(alias, str) and alias.strip():
                        names.append((emitted_dns_name(alias), f"dns.interfaces.{ifname}.aliases[{j}]"))

    return names


def host_known_fqdns(
    host: Dict[str, Any],
    site_name: str,
    site: Dict[str, Any],
    root: str,
) -> Set[str]:
    names: Set[str] = set()
    zone = site_zone(site_name, site, root)

    dns = host.get("dns")
    dns = dns if isinstance(dns, dict) else {}

    def add_name(value: Any) -> None:
        if not isinstance(value, str) or not value.strip():
            return
        value = value.strip()
        if "." in value:
            names.add(norm_fqdn(value))
        else:
            names.add(f"{value.lower()}.{zone}")

    add_name(dns.get("canonical"))

    aliases = dns.get("aliases")
    if isinstance(aliases, list):
        for alias in aliases:
            add_name(alias)

    interfaces = dns.get("interfaces")
    if isinstance(interfaces, dict):
        for ifdns in interfaces.values():
            if not isinstance(ifdns, dict):
                continue
            add_name(ifdns.get("canonical"))
            if_aliases = ifdns.get("aliases")
            if isinstance(if_aliases, list):
                for alias in if_aliases:
                    add_name(alias)

    if not names:
        name = host.get("name")
        if isinstance(name, str) and name.strip():
            names.add(f"{name.lower()}.{zone}")

    return names


def collect_emitted_dns_names(
    registry: Dict[str, Any],
    sites: Dict[str, Dict[str, Any]],
) -> List[DnsEmission]:
    """
    Approximate the generated DNS namespace.

    This catches cases such as:

      host name: printer
      alias: printer

    which would both emit the short name `printer`.

    The generator may emit both short names and FQDNs; this validator models the
    important collision cases without depending on generated files.
    """
    root = private_root(registry)
    emissions: List[DnsEmission] = []

    for idx, host in iter_hosts(registry):
        label = host_label(host, idx)
        site_name = host.get("site")
        if not isinstance(site_name, str) or site_name not in sites:
            continue

        site = sites[site_name]
        zone = site_zone(site_name, site, root)

        addrs = host_addresses(host)
        dns = host.get("dns")
        dns = dns if isinstance(dns, dict) else {}

        def emit(name: str, source: str, kind: str) -> None:
            emissions.append(
                DnsEmission(
                    name=emitted_dns_name(name),
                    owner_host=label,
                    source=source,
                    site=site_name,
                    kind=kind,
                )
            )

        # Top-level canonical.
        canonical = dns.get("canonical")
        if isinstance(canonical, str) and canonical.strip():
            emit(canonical, "dns.canonical", "canonical")
        else:
            host_name = host.get("name")
            if isinstance(host_name, str) and host_name.strip():
                emit(f"{host_name}.{zone}", "derived canonical", "canonical")

        # Generator-style short names for local convenience where explicit
        # address material exists.
        host_name = host.get("name")
        if isinstance(host_name, str) and host_name.strip():
            if "lan" in addrs or "wifi" in addrs:
                emit(host_name, "derived short name", "short-name")

        # Interface-specific canonical names.
        interfaces = dns.get("interfaces")
        if isinstance(interfaces, dict):
            for ifname, ifdns in interfaces.items():
                if not isinstance(ifdns, dict):
                    continue
                if_canonical = ifdns.get("canonical")
                if isinstance(if_canonical, str) and if_canonical.strip():
                    emit(if_canonical, f"dns.interfaces.{ifname}.canonical", "interface-canonical")
                if_aliases = ifdns.get("aliases")
                if isinstance(if_aliases, list):
                    for j, alias in enumerate(if_aliases):
                        if isinstance(alias, str) and alias.strip():
                            emit(alias, f"dns.interfaces.{ifname}.aliases[{j}]", "interface-alias")

        # Explicit aliases.
        aliases = dns.get("aliases")
        if isinstance(aliases, list):
            for j, alias in enumerate(aliases):
                if isinstance(alias, str) and alias.strip():
                    emit(alias, f"dns.aliases[{j}]", "alias")

    return emissions


def validate_top_level(registry: Dict[str, Any], r: Reporter) -> None:
    for key in ("meta", "sites", "hosts"):
        if key not in registry:
            r.error(f"top-level: missing required section '{key}'")

    if "sites" in registry and not isinstance(registry["sites"], dict):
        r.error("top-level: 'sites' must be a mapping")

    if "hosts" in registry and not isinstance(registry["hosts"], list):
        r.error("top-level: 'hosts' must be a list")


def validate_sites(registry: Dict[str, Any], r: Reporter) -> Dict[str, Dict[str, Any]]:
    sites_raw = registry.get("sites", {})
    sites: Dict[str, Dict[str, Any]] = {}

    if not isinstance(sites_raw, dict):
        return sites

    root = private_root(registry)

    for site_name, site in sites_raw.items():
        if not isinstance(site_name, str):
            r.error("sites: site key must be a string")
            continue

        if not isinstance(site, dict):
            r.error(f"sites.{site_name}: site definition must be a mapping")
            continue

        sites[site_name] = site

        zone = site_zone(site_name, site, root)
        if not is_fqdn(zone):
            r.error(f"sites.{site_name}.zone: invalid zone '{zone}'")

        if site_name == "vpn" and site.get("overlay"):
            pass
        else:
            cidr = site_lan_cidr(site)
            if cidr is None:
                r.warning(f"sites.{site_name}: no LAN CIDR found")
            elif parse_network(cidr) is None:
                r.error(f"sites.{site_name}.lan.cidr: invalid IPv4 CIDR '{cidr}'")

        dhcp = site_dhcp_config(site)
        if dhcp and not site_has_no_dhcp(site):
            pool_start, pool_end = dhcp_pool(site)
            if pool_start is None or pool_end is None:
                r.warning(f"sites.{site_name}.dhcp: no complete dynamic range found")
            elif int(pool_start) > int(pool_end):
                r.error(
                    f"sites.{site_name}.dhcp: range start {pool_start} is after end {pool_end}"
                )

    return sites


def validate_hosts(registry: Dict[str, Any], sites: Dict[str, Dict[str, Any]], r: Reporter) -> None:
    root = private_root(registry)

    seen_host_names: DefaultDict[str, List[str]] = defaultdict(list)
    seen_ips: DefaultDict[str, List[str]] = defaultdict(list)
    seen_macs: DefaultDict[str, List[str]] = defaultdict(list)
    seen_dns: DefaultDict[str, List[str]] = defaultdict(list)

    for idx, host in iter_hosts(registry):
        label = host_label(host, idx)

        name = host.get("name")
        if not isinstance(name, str) or not name.strip():
            r.error(f"hosts[{idx}].name: missing or invalid host name")
        elif not is_short_name(name):
            r.error(f"hosts[{idx}].name: invalid short hostname '{name}'")
        else:
            seen_host_names[name.lower()].append(label)

        site_name = host.get("site")
        if not isinstance(site_name, str) or not site_name.strip():
            r.error(f"{label}: missing site")
            site = {}
        elif site_name not in sites:
            r.error(f"{label}: site '{site_name}' is not defined in sites")
            site = {}
        else:
            site = sites[site_name]

        addressing = host.get("addressing")
        if addressing is not None:
            if not isinstance(addressing, str):
                r.error(f"{label}.addressing: must be a string")
            elif addressing not in ALLOWED_ADDRESSING:
                r.error(
                    f"{label}.addressing: unsupported value '{addressing}' "
                    f"(allowed: {sorted(ALLOWED_ADDRESSING)})"
                )

        addrs = host_addresses(host)
        if not addrs:
            r.warning(f"{label}: no addresses defined")

        site_net = None
        cidr = site_lan_cidr(site) if site else None
        if cidr:
            site_net = parse_network(cidr)

        for addr_key, value in addrs.items():
            ip = parse_ip(value)
            if ip is None:
                r.error(f"{label}.addresses.{addr_key}: invalid IPv4 address '{value}'")
                continue

            seen_ips[str(ip)].append(f"{label}.addresses.{addr_key}")

            if addr_key not in ADDRESS_KEYS:
                r.warning(f"{label}.addresses.{addr_key}: non-standard address key")

            if addr_key in ("lan", "wifi") and site_net and ip not in site_net:
                r.error(
                    f"{label}.addresses.{addr_key}: {ip} is outside site LAN CIDR {site_net}"
                )

        macs = host_macs(host)
        for mac_key, mac in macs.items():
            if not is_mac(mac):
                r.error(f"{label}.macs.{mac_key}: invalid MAC address '{mac}'")
                continue
            seen_macs[mac.lower()].append(f"{label}.macs.{mac_key}")

        dns = host.get("dns")
        if "dns" in host and not isinstance(dns, dict):
            r.error(f"{label}.dns: must be a mapping")
            dns = None

        if isinstance(dns, dict):
            canonical = dns.get("canonical")
            if canonical is not None:
                if not is_fqdn(canonical):
                    r.error(f"{label}.dns.canonical: invalid FQDN '{canonical}'")
                elif site and isinstance(site_name, str):
                    canonical_key = norm_fqdn(canonical)
                    zone = site_zone(site_name, site, root)
                    if not canonical_key.endswith("." + zone) and canonical_key != zone:
                        r.warning(
                            f"{label}.dns.canonical: '{canonical}' is outside site zone '{zone}'"
                        )

            aliases = dns.get("aliases")
            if aliases is not None and not isinstance(aliases, list):
                r.error(f"{label}.dns.aliases: must be a list")
            elif isinstance(aliases, list):
                exact_aliases_seen: Set[str] = set()
                for alias_idx, alias in enumerate(aliases):
                    if not isinstance(alias, str) or not alias.strip():
                        r.error(f"{label}.dns.aliases[{alias_idx}]: alias must be a non-empty string")
                        continue

                    alias_text = alias.strip()
                    if "." in alias_text:
                        if not is_fqdn(alias_text):
                            r.error(f"{label}.dns.aliases[{alias_idx}]: invalid FQDN '{alias_text}'")
                            continue
                    else:
                        if not is_short_name(alias_text):
                            r.error(f"{label}.dns.aliases[{alias_idx}]: invalid short alias '{alias_text}'")
                            continue

                    emitted = emitted_dns_name(alias_text)
                    if emitted in exact_aliases_seen:
                        r.warning(
                            f"{label}.dns.aliases[{alias_idx}]: exact duplicate alias '{alias_text}' within host"
                        )
                    exact_aliases_seen.add(emitted)

            interfaces = dns.get("interfaces")
            if interfaces is not None and not isinstance(interfaces, dict):
                r.error(f"{label}.dns.interfaces: must be a mapping")
            elif isinstance(interfaces, dict):
                for ifname, ifdns in interfaces.items():
                    if not isinstance(ifdns, dict):
                        r.error(f"{label}.dns.interfaces.{ifname}: must be a mapping")
                        continue
                    if_canonical = ifdns.get("canonical")
                    if if_canonical is not None and not is_fqdn(if_canonical):
                        r.error(
                            f"{label}.dns.interfaces.{ifname}.canonical: invalid FQDN '{if_canonical}'"
                        )

            for emitted, source in host_explicit_dns_names(host):
                seen_dns[emitted].append(f"{label}.{source}")

        if addressing in DHCP_RESERVATION_MODES:
            if not addrs.get("lan") and not addrs.get("wifi"):
                r.error(f"{label}: {addressing} requires addresses.lan or addresses.wifi")
            if not macs:
                r.error(f"{label}: {addressing} requires mac or macs")

            pool_start, pool_end = dhcp_pool(site) if site else (None, None)
            service_ip = parse_ip(addrs.get("lan") or addrs.get("wifi"))
            if service_ip and pool_start and pool_end:
                if int(pool_start) <= int(service_ip) <= int(pool_end):
                    r.warning(
                        f"{label}: fixed lease {service_ip} overlaps dynamic pool {pool_start}-{pool_end}"
                    )

    for host_name, owners in sorted(seen_host_names.items()):
        if len(set(owners)) > 1:
            r.error(f"hosts: duplicate host name '{host_name}': {sorted(set(owners))}")

    for ip, owners in sorted(seen_ips.items(), key=lambda item: tuple(int(x) for x in item[0].split("."))):
        uniq = sorted(set(owners))
        if len(uniq) > 1:
            r.error(f"addresses: duplicate IP {ip}: {uniq}")

    for mac, owners in sorted(seen_macs.items()):
        uniq = sorted(set(owners))
        if len(uniq) > 1:
            r.error(f"macs: duplicate MAC {mac}: {uniq}")

    dns_owners_by_host: DefaultDict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
    for dns_name, owners in seen_dns.items():
        for owner in owners:
            host_part = owner.split(".", 1)[0]
            dns_owners_by_host[dns_name][host_part].append(owner)

    for dns_name, host_map in sorted(dns_owners_by_host.items()):
        if len(host_map) > 1:
            flattened = sorted(o for owners in host_map.values() for o in owners)
            r.error(f"dns: duplicate explicit name '{dns_name}' across hosts: {flattened}")


def validate_generated_dns_collisions(
    registry: Dict[str, Any],
    sites: Dict[str, Dict[str, Any]],
    r: Reporter,
) -> None:
    emissions = collect_emitted_dns_names(registry, sites)

    owners_by_name: DefaultDict[str, Dict[str, List[DnsEmission]]] = defaultdict(lambda: defaultdict(list))
    for emission in emissions:
        owners_by_name[emission.name][emission.owner_host].append(emission)

    for name, host_map in sorted(owners_by_name.items()):
        if len(host_map) <= 1:
            continue

        detail_parts: List[str] = []
        for host, items in sorted(host_map.items()):
            sources = ", ".join(sorted({f"{i.source} ({i.kind})" for i in items}))
            detail_parts.append(f"{host}: {sources}")

        r.error(
            "dns: generated name collision "
            f"'{name}' is emitted by multiple hosts: " + "; ".join(detail_parts)
        )


def collect_known_fqdns(registry: Dict[str, Any], sites: Dict[str, Dict[str, Any]]) -> Set[str]:
    root = private_root(registry)
    known: Set[str] = set()

    for idx, host in iter_hosts(registry):
        site_name = host.get("site")
        if isinstance(site_name, str) and site_name in sites:
            known.update(host_known_fqdns(host, site_name, sites[site_name], root))

    return known


def validate_reverse_dns(registry: Dict[str, Any], sites: Dict[str, Dict[str, Any]], r: Reporter) -> None:
    reverse = registry.get("reverse_dns", [])
    if reverse is None:
        return
    if not isinstance(reverse, list):
        r.error("reverse_dns: must be a list")
        return

    known_fqdns = collect_known_fqdns(registry, sites)
    seen_cidrs: Set[str] = set()

    for idx, entry in enumerate(reverse):
        if not isinstance(entry, dict):
            r.error(f"reverse_dns[{idx}]: must be a mapping")
            continue

        cidr = entry.get("cidr")
        net = parse_network(cidr)
        if net is None:
            r.error(f"reverse_dns[{idx}].cidr: invalid or missing IPv4 CIDR '{cidr}'")
        else:
            key = str(net)
            if key in seen_cidrs:
                r.warning(f"reverse_dns[{idx}].cidr: duplicate reverse CIDR {key}")
            seen_cidrs.add(key)

        zone = entry.get("zone")
        if zone is not None and not is_fqdn(str(zone)):
            r.error(f"reverse_dns[{idx}].zone: invalid reverse zone '{zone}'")

        authority = entry.get("authority")
        if authority is None:
            r.warning(f"reverse_dns[{idx}].authority: missing")
        elif not is_fqdn(authority):
            r.error(f"reverse_dns[{idx}].authority: invalid FQDN '{authority}'")
        else:
            authority_key = norm_fqdn(authority)
            if authority_key not in known_fqdns:
                r.error(
                    f"reverse_dns[{idx}].authority: authority '{authority}' "
                    "does not match any known host canonical name or alias"
                )


def registry_statistics(registry: Dict[str, Any], sites: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
    stats: Counter[str] = Counter()

    stats["sites"] = len(sites)

    emissions = collect_emitted_dns_names(registry, sites)
    stats["generated_dns_names"] = len({e.name for e in emissions})

    for idx, host in iter_hosts(registry):
        stats["hosts"] += 1

        dns = host.get("dns")
        if isinstance(dns, dict):
            if isinstance(dns.get("canonical"), str):
                stats["dns_canonicals"] += 1
            aliases = dns.get("aliases")
            if isinstance(aliases, list):
                stats["dns_aliases"] += sum(1 for a in aliases if isinstance(a, str) and a.strip())

            interfaces = dns.get("interfaces")
            if isinstance(interfaces, dict):
                for ifdns in interfaces.values():
                    if isinstance(ifdns, dict) and isinstance(ifdns.get("canonical"), str):
                        stats["interface_canonicals"] += 1

        addressing = host.get("addressing")
        if addressing in DHCP_RESERVATION_MODES:
            stats["dhcp_reservations"] += 1
        if addressing in STATIC_MODES:
            stats["static_hosts"] += 1

        addrs = host_addresses(host)
        if "vpn" in addrs:
            stats["hosts_with_vpn_address"] += 1

        roles = host.get("roles")
        if isinstance(roles, list) and any("wireguard" in str(role) or "vpn" in str(role) for role in roles):
            stats["wireguard_or_vpn_role_hosts"] += 1

    return dict(stats)


def print_statistics(registry: Dict[str, Any], sites: Dict[str, Dict[str, Any]]) -> None:
    stats = registry_statistics(registry, sites)

    print("Registry Statistics")
    print("-------------------")
    print(f"Sites:                       {stats.get('sites', 0)}")
    print(f"Hosts:                       {stats.get('hosts', 0)}")
    print(f"DNS canonicals:              {stats.get('dns_canonicals', 0)}")
    print(f"DNS aliases:                 {stats.get('dns_aliases', 0)}")
    print(f"Interface canonicals:        {stats.get('interface_canonicals', 0)}")
    print(f"Generated DNS names:         {stats.get('generated_dns_names', 0)}")
    print(f"DHCP reservations:           {stats.get('dhcp_reservations', 0)}")
    print(f"Static hosts:                {stats.get('static_hosts', 0)}")
    print(f"Hosts with VPN address:      {stats.get('hosts_with_vpn_address', 0)}")
    print(f"WireGuard/VPN role hosts:    {stats.get('wireguard_or_vpn_role_hosts', 0)}")
    print()


def print_site_report(registry: Dict[str, Any], sites: Dict[str, Dict[str, Any]]) -> None:
    emissions = collect_emitted_dns_names(registry, sites)
    dns_by_site: DefaultDict[str, Set[str]] = defaultdict(set)
    for e in emissions:
        dns_by_site[e.site].add(e.name)

    rows: List[Tuple[str, int, int, int, int, str]] = []

    for site_name, site in sites.items():
        host_count = 0
        dhcp_count = 0
        static_count = 0

        for _, host in iter_hosts(registry):
            if host.get("site") != site_name:
                continue
            host_count += 1
            if host.get("addressing") in DHCP_RESERVATION_MODES:
                dhcp_count += 1
            if host.get("addressing") in STATIC_MODES:
                static_count += 1

        pool_start, pool_end = dhcp_pool(site)
        pool = f"{pool_start}-{pool_end}" if pool_start and pool_end else "-"

        rows.append((site_name, host_count, len(dns_by_site[site_name]), dhcp_count, static_count, pool))

    print("Site Report")
    print("-----------")
    print(f"{'Site':12} {'Hosts':>5} {'DNS':>5} {'DHCP':>5} {'Static':>6} {'Dynamic pool'}")
    for site_name, host_count, dns_count, dhcp_count, static_count, pool in sorted(rows):
        print(f"{site_name:12} {host_count:5} {dns_count:5} {dhcp_count:5} {static_count:6} {pool}")
    print()


def explain_fqdns(registry: Dict[str, Any], sites: Dict[str, Dict[str, Any]]) -> None:
    root = private_root(registry)

    for idx, host in iter_hosts(registry):
        label = host_label(host, idx)
        site_name = host.get("site")
        print(label)

        if isinstance(site_name, str) and site_name in sites:
            names = sorted(host_known_fqdns(host, site_name, sites[site_name], root))
            for name in names:
                print(f"  - {name}")
        else:
            print("  - <no valid site>")

        print()


def explain_dhcp(registry: Dict[str, Any], sites: Dict[str, Dict[str, Any]]) -> None:
    for site_name, site in sites.items():
        pool_start, pool_end = dhcp_pool(site)
        print(site_name)
        print(f"  dynamic pool: {pool_start or '<missing>'} - {pool_end or '<missing>'}")
        print("  reservations:")

        rows: List[Tuple[ipaddress.IPv4Address, str, str]] = []
        for idx, host in iter_hosts(registry):
            if host.get("site") != site_name:
                continue
            if host.get("addressing") not in DHCP_RESERVATION_MODES:
                continue
            addrs = host_addresses(host)
            service_ip = parse_ip(addrs.get("lan") or addrs.get("wifi"))
            if service_ip is None:
                continue
            rows.append((service_ip, host_label(host, idx), "yes" if host_macs(host) else "no"))

        for ip, name, has_mac in sorted(rows, key=lambda row: int(row[0])):
            overlap = ""
            if pool_start and pool_end and int(pool_start) <= int(ip) <= int(pool_end):
                overlap = "  OVERLAPS-POOL"
            print(f"    {str(ip):15} {name:28} mac={has_mac}{overlap}")

        print()


def explain_host(registry: Dict[str, Any], sites: Dict[str, Dict[str, Any]], host_name: str) -> int:
    root = private_root(registry)
    found = False

    for idx, host in iter_hosts(registry):
        if host.get("name") != host_name:
            continue

        found = True
        label = host_label(host, idx)
        site_name = host.get("site")
        print(f"Host: {label}")
        print(f"Site: {site_name}")
        print(f"Category: {host.get('category', '-')}")
        print(f"Addressing: {host.get('addressing', '-')}")
        print()

        print("Addresses:")
        for key, value in sorted(host_addresses(host).items()):
            print(f"  {key}: {value}")
        print()

        print("MACs:")
        for key, value in sorted(host_macs(host).items()):
            print(f"  {key}: {value}")
        print()

        print("DNS:")
        if isinstance(site_name, str) and site_name in sites:
            for name in sorted(host_known_fqdns(host, site_name, sites[site_name], root)):
                print(f"  - {name}")
        print()

        roles = host.get("roles")
        print("Roles:")
        if isinstance(roles, list):
            for role in roles:
                print(f"  - {role}")
        print()

    if not found:
        print(f"Host not found: {host_name}", file=sys.stderr)
        return 1

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate MudPi network registry")
    parser.add_argument(
        "yaml_file",
        nargs="?",
        default="docs/reference/network-registry.yaml",
        help="Path to network-registry.yaml",
    )
    parser.add_argument(
        "--explain-fqdns",
        action="store_true",
        help="Print resolved FQDNs for each host and exit",
    )
    parser.add_argument(
        "--explain-dhcp",
        action="store_true",
        help="Print DHCP reservations and dynamic pools and exit",
    )
    parser.add_argument(
        "--explain-host",
        metavar="HOST",
        help="Print details for a single host and exit",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Print registry statistics",
    )
    parser.add_argument(
        "--site-report",
        action="store_true",
        help="Print per-site inventory report",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Print INFO lines as well as warnings and errors",
    )
    args = parser.parse_args()

    registry = load_yaml(Path(args.yaml_file))
    reporter = Reporter()

    validate_top_level(registry, reporter)
    sites = validate_sites(registry, reporter)

    if args.explain_fqdns:
        explain_fqdns(registry, sites)
        return

    if args.explain_dhcp:
        explain_dhcp(registry, sites)
        return

    if args.explain_host:
        sys.exit(explain_host(registry, sites, args.explain_host))

    if args.stats:
        print_statistics(registry, sites)

    if args.site_report:
        print_site_report(registry, sites)

    validate_hosts(registry, sites, reporter)
    validate_generated_dns_collisions(registry, sites, reporter)
    validate_reverse_dns(registry, sites, reporter)

    if not args.stats and not args.site_report:
        print_statistics(registry, sites)

    reporter.print(show_info=args.info)

    if reporter.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
