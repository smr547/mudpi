#!/usr/bin/env python3
"""
validate_registry_multi_fqdn.py

Validator for the MudPi network registry supporting multiple FQDNs per host.

Key idea
--------
Hosts may define DNS names explicitly:

    dns:
        canonical: mudpi.reid.home.arpa
        aliases:
            - mudpi.vpn.home.arpa

Reverse DNS authorities must match one of the host FQDNs collected from:

    dns.canonical
    dns.aliases

If dns.canonical is missing, the validator falls back to the legacy rule:

    {host.name}.{host.site}.home.arpa

This preserves compatibility with the original registry design.

The validator also checks that explicit FQDNs are not assigned to more than one host.
"""

import argparse
import ipaddress
import re
import sys
from pathlib import Path
from typing import Dict, Any, List, Set, DefaultDict

import yaml


FQDN_RE = re.compile(r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]+(\.(?!-)[A-Za-z0-9-]+)+\.?$")


def is_fqdn(value: str) -> bool:
    return isinstance(value, str) and bool(FQDN_RE.match(value))


def derive_legacy_fqdn(host: Dict[str, Any], private_root: str) -> str | None:
    name = host.get("name")
    site = host.get("site")

    if name and site:
        return f"{name}.{site}.{private_root}".lower()

    return None


def collect_host_fqdns(registry: Dict[str, Any]) -> Set[str]:
    fqdns: Set[str] = set()
    private_root = registry.get("meta", {}).get("private_root", "home.arpa")

    for host in registry.get("hosts", []):
        dns = host.get("dns", {})

        canonical = dns.get("canonical")
        if canonical:
            fqdns.add(canonical.lower())

        for alias in dns.get("aliases", []):
            fqdns.add(alias.lower())

        if not canonical:
            legacy = derive_legacy_fqdn(host, private_root)
            if legacy:
                fqdns.add(legacy)

    return fqdns

def explain_reverse_dns(registry):
    """
    Print each reverse DNS zone and show whether its authority matches
    a known host FQDN.
    """
    valid_fqdns = collect_host_fqdns(registry)

    for i, entry in enumerate(registry.get("reverse_dns", [])):
        cidr = entry.get("cidr", "<missing-cidr>")
        zone = entry.get("zone", "<missing-zone>")
        authority = entry.get("authority", "<missing-authority>")

        authority_key = authority.rstrip(".").lower() if isinstance(authority, str) else None
        status = "OK" if authority_key in valid_fqdns else "UNKNOWN"

        print(f"reverse_dns[{i}]")
        print(f"  cidr:      {cidr}")
        print(f"  zone:      {zone}")
        print(f"  authority: {authority}")
        print(f"  status:    {status}")
        print()

def explain_host_fqdns(registry):
    """
    Print the canonical and alias FQDNs for each host.
    Useful for debugging DNS generation.
    """
    private_root = registry.get("meta", {}).get("private_root", "home.arpa")

    for host in registry.get("hosts", []):
        name = host.get("name")
        site = host.get("site")
        dns = host.get("dns", {})

        print(f"{name}")

        canonical = dns.get("canonical")
        if canonical:
            print(f"  canonical: {canonical}")

        aliases = dns.get("aliases", [])
        if aliases:
            print("  aliases:")
            for a in aliases:
                print(f"    - {a}")

        if not canonical:
            legacy = derive_legacy_fqdn(host, private_root)
            if legacy:
                print(f"  derived: {legacy}")

        print()


def validate_duplicate_host_fqdns(registry: Dict[str, Any], errors: List[str]):
    """
    Ensure that no explicit FQDN is assigned to more than one host.

    Only explicit names are checked here:
        dns.canonical
        dns.aliases

    The legacy derived fallback is intentionally not collision-checked in this
    first lightweight validator, because it is deterministic from name+site.
    """
    owners: Dict[str, List[str]] = {}

    for i, host in enumerate(registry.get("hosts", [])):
        host_name = host.get("name", f"<host[{i}]>")
        dns = host.get("dns", {})

        canonical = dns.get("canonical")
        if isinstance(canonical, str) and canonical.strip():
            key = canonical.rstrip(".").lower()
            owners.setdefault(key, []).append(str(host_name))

        for alias in dns.get("aliases", []):
            if isinstance(alias, str) and alias.strip():
                key = alias.rstrip(".").lower()
                owners.setdefault(key, []).append(str(host_name))

    for fqdn, host_names in sorted(owners.items()):
        uniq = sorted(set(host_names))
        if len(uniq) > 1:
            errors.append(
                f"hosts: explicit FQDN '{fqdn}' is assigned to multiple hosts: {uniq}"
            )


def validate_reverse_dns_authorities(registry: Dict[str, Any], errors: List[str]):
    valid_fqdns = collect_host_fqdns(registry)

    for i, entry in enumerate(registry.get("reverse_dns", [])):
        authority = entry.get("authority")

        if authority is None:
            continue

        authority_lc = authority.lower()

        if authority_lc not in valid_fqdns:
            errors.append(
                f"reverse_dns[{i}].authority: authority FQDN does not match any known host FQDN: '{authority}'"
            )


def validate_host_dns(registry: Dict[str, Any], errors: List[str]):
    for i, host in enumerate(registry.get("hosts", [])):
        dns = host.get("dns", {})

        canonical = dns.get("canonical")
        if canonical and not is_fqdn(canonical):
            errors.append(
                f"hosts[{i}].dns.canonical: invalid FQDN '{canonical}'"
            )

        seen_aliases: Set[str] = set()
        for j, alias in enumerate(dns.get("aliases", [])):
            if not is_fqdn(alias):
                errors.append(
                    f"hosts[{i}].dns.aliases[{j}]: invalid FQDN '{alias}'"
                )
                continue

            alias_key = alias.rstrip(".").lower()
            if alias_key in seen_aliases:
                errors.append(
                    f"hosts[{i}].dns.aliases[{j}]: duplicate alias within host '{alias}'"
                )
            else:
                seen_aliases.add(alias_key)


def load_yaml(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"YAML load error: {e}")
        sys.exit(2)


def main():
    parser = argparse.ArgumentParser(description="Validate MudPi registry")
    parser.add_argument("yaml_file")
    parser.add_argument(
        "--explain-fqdns",
        action="store_true",
        help="Print the resolved FQDNs for each host and exit",
    )
    parser.add_argument(
        "--explain-reverse",
        action="store_true",
        help="Print reverse DNS zones and whether each authority matches a known host FQDN",
    )
    args = parser.parse_args()

    registry = load_yaml(Path(args.yaml_file))

    if args.explain_fqdns:
        explain_host_fqdns(registry)
        sys.exit(0)

    if args.explain_reverse:
        explain_reverse_dns(registry)
        sys.exit(0)

    errors: List[str] = []
    warnings: List[str] = []

    validate_host_dns(registry, errors)
    validate_duplicate_host_fqdns(registry, errors)
    validate_reverse_dns_authorities(registry, errors)

    for e in errors:
        print(f"ERROR: {e}")

    for w in warnings:
        print(f"WARNING: {w}")

    print()
    print(f"Summary: {len(errors)} error(s), {len(warnings)} warning(s)")

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
