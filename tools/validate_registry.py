#!/usr/bin/env python3
"""
validate_registry.py

Validator for the MudPi network registry.

This version tracks the current MudPi registry schema used by the DNS/DHCP
generation workflow.

The validator checks:

- top-level structure
- site definitions and zones
- LAN CIDRs and DHCP dynamic pools
- host names and site membership
- addressing mode values
- IPv4 address syntax
- LAN/Wi-Fi addresses inside the site's LAN CIDR
- duplicate IP addresses
- MAC address syntax
- duplicate MAC addresses
- DNS canonical names and aliases
- duplicate DNS names across different hosts
- reverse DNS authority references
- DHCP reservation preconditions
- DHCP reservation overlap with the registry's dynamic pool

Notes:

- Short aliases and FQDN aliases are treated as distinct emitted DNS forms.
  For example, `nas` and `nas.reid.home.arpa` are intentionally allowed on
  the same host because the dnsmasq generator emits both.
- Duplicate DNS names within the same host are ignored unless they are exact
  duplicates of the same emitted form.
- The registry is the source of truth. Generated files should not be edited.
"""

from __future__ import annotations

import argparse
import ipaddress
import re
import sys
from collections import defaultdict
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
    "dhcp-reserved",      # legacy synonym currently present in registry
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

ADDRESS_KEYS = {
    "lan",
    "wifi",
    "vpn",
}


class Reporter:
    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def print(self) -> None:
        for e in self.errors:
            print(f"ERROR: {e}")
        for w in self.warnings:
            print(f"WARNING: {w}")
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


def site_zone(site_name: str, site: Dict[str, Any], private_root: str) -> str:
    zone = site.get("zone")
    if isinstance(zone, str) and zone.strip():
        return norm_fqdn(zone)
    return f"{site_name}.{private_root}".lower()


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

    # Current registry schema:
    #
    # dhcp:
    #   dynamic_pool:
    #     start: ...
    #     end: ...
    dynamic_pool = dhcp.get("dynamic_pool")
    if isinstance(dynamic_pool, dict):
        start = dynamic_pool.get("start")
        end = dynamic_pool.get("end")
        return parse_ip(start), parse_ip(end)

    # Older / alternate forms accepted for compatibility.
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

    # Legacy compatibility
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
    """
    Return the actual dnsmasq-emitted name identity.

    Important: short names and FQDNs are distinct emitted names.
    We therefore do NOT expand a short alias into the site zone for duplicate
    detection.
    """
    value = alias_or_fqdn.strip().lower()
    if "." in value:
        return norm_fqdn(value)
    return value


def host_explicit_dns_names(host: Dict[str, Any]) -> List[Tuple[str, str]]:
    """
    Return explicit DNS names as (emitted_name_key, source_label).

    This intentionally does not derive legacy host.site.home.arpa names.
    """
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

    return names


def host_known_fqdns(
    host: Dict[str, Any],
    site_name: str,
    site: Dict[str, Any],
    private_root: str,
) -> Set[str]:
    """
    Return FQDNs associated with a host for reverse DNS authority matching.

    Short aliases are expanded into the local zone here because an authority
    must be an FQDN.
    """
    names: Set[str] = set()
    zone = site_zone(site_name, site, private_root)

    dns = host.get("dns")
    dns = dns if isinstance(dns, dict) else {}

    canonical = dns.get("canonical")
    if isinstance(canonical, str) and canonical.strip() and "." in canonical:
        names.add(norm_fqdn(canonical))

    aliases = dns.get("aliases")
    if isinstance(aliases, list):
        for alias in aliases:
            if not isinstance(alias, str) or not alias.strip():
                continue
            alias = alias.strip()
            if "." in alias:
                names.add(norm_fqdn(alias))
            else:
                names.add(f"{alias.lower()}.{zone}")

    if not names:
        name = host.get("name")
        if isinstance(name, str) and name.strip():
            names.add(f"{name.lower()}.{zone}")

    return names


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

    private_root = registry.get("meta", {}).get("private_root", "home.arpa")
    if not isinstance(private_root, str) or not private_root.strip():
        private_root = "home.arpa"

    for site_name, site in sites_raw.items():
        if not isinstance(site_name, str):
            r.error("sites: site key must be a string")
            continue

        if not isinstance(site, dict):
            r.error(f"sites.{site_name}: site definition must be a mapping")
            continue

        sites[site_name] = site

        zone = site_zone(site_name, site, private_root)
        if not is_fqdn(zone):
            r.error(f"sites.{site_name}.zone: invalid zone '{zone}'")

        if site_name == "vpn" and site.get("overlay"):
            # VPN-only site does not necessarily have a LAN CIDR.
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
    private_root = registry.get("meta", {}).get("private_root", "home.arpa")
    if not isinstance(private_root, str) or not private_root.strip():
        private_root = "home.arpa"

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
        else:
            r.warning(f"{label}: missing addressing")

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

            # A host may have the same value in legacy ip and addresses.lan;
            # host_addresses() already collapses that to one entry.
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
                    zone = site_zone(site_name, site, private_root)
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

            # Only explicit emitted names are checked globally.
            # Duplicates within the same host are allowed; duplicates across
            # different hosts are errors.
            for emitted, source in host_explicit_dns_names(host):
                seen_dns[emitted].append(f"{label}.{source}")

        # DHCP reservation checks.
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


def collect_known_fqdns(registry: Dict[str, Any], sites: Dict[str, Dict[str, Any]]) -> Set[str]:
    private_root = registry.get("meta", {}).get("private_root", "home.arpa")
    if not isinstance(private_root, str) or not private_root.strip():
        private_root = "home.arpa"

    known: Set[str] = set()

    for idx, host in iter_hosts(registry):
        site_name = host.get("site")
        if isinstance(site_name, str) and site_name in sites:
            known.update(host_known_fqdns(host, site_name, sites[site_name], private_root))

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


def explain_fqdns(registry: Dict[str, Any], sites: Dict[str, Dict[str, Any]]) -> None:
    private_root = registry.get("meta", {}).get("private_root", "home.arpa")
    if not isinstance(private_root, str) or not private_root.strip():
        private_root = "home.arpa"

    for idx, host in iter_hosts(registry):
        label = host_label(host, idx)
        site_name = host.get("site")
        print(label)

        if isinstance(site_name, str) and site_name in sites:
            names = sorted(host_known_fqdns(host, site_name, sites[site_name], private_root))
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

    validate_hosts(registry, sites, reporter)
    validate_reverse_dns(registry, sites, reporter)

    reporter.print()

    if reporter.errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
