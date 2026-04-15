#!/usr/bin/env python3
"""
Emit YAML stub entries for DHCP lease MACs not present in network-registry.yaml.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required: pip install pyyaml") from exc


def normalize_mac(value: str | None) -> str | None:
    if not value:
        return None
    return str(value).strip().lower().replace("-", ":")


def load_known_macs(registry_path: Path) -> set[str]:
    data = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    hosts = data.get("hosts", {})
    known: set[str] = set()

    def process_host(host: dict[str, Any]) -> None:
        top_mac = normalize_mac(host.get("mac"))
        if top_mac:
            known.add(top_mac)

        macs = host.get("macs")
        if isinstance(macs, dict):
            for value in macs.values():
                mac = normalize_mac(value)
                if mac:
                    known.add(mac)

    if isinstance(hosts, list):
        for item in hosts:
            if isinstance(item, dict):
                process_host(item)
    elif isinstance(hosts, dict):
        for _, value in hosts.items():
            if isinstance(value, dict):
                process_host(value)

    return known


def load_unknown_leases(leases_path: Path, known_macs: set[str]) -> list[dict[str, str]]:
    unknowns: list[dict[str, str]] = []
    seen: set[str] = set()

    if not leases_path.exists():
        return unknowns

    for line in leases_path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue

        mac = normalize_mac(parts[1])
        ip = parts[2]
        dhcp_name = parts[3]

        if not mac or mac in known_macs or mac in seen:
            continue

        seen.add(mac)
        unknowns.append(
            {
                "mac": mac,
                "ip": ip,
                "dhcp_name": dhcp_name,
            }
        )

    unknowns.sort(key=lambda x: tuple(int(p) for p in x["ip"].split(".")))
    return unknowns


def emit_yaml_stubs(unknowns: list[dict[str, str]], site: str) -> None:
    if not unknowns:
        print("# No unknown DHCP clients found.")
        return

    print("# YAML stubs for unknown DHCP clients")
    print("# Review names, categories, and roles before merging.")
    print()

    for item in unknowns:
        dhcp_name = item["dhcp_name"]
        suggested_name = dhcp_name if dhcp_name != "*" else f"unknown-{item['ip'].replace('.', '-')}"
        print(f"- name: {suggested_name}")
        print(f"  site: {site}")
        print("  category: unknown")
        print("  addressing: dhcp-reservation")
        print(f"  mac: \"{item['mac']}\"")
        print("  addresses:")
        print(f"    lan: {item['ip']}")
        print("  dns:")
        print(f"    canonical: {suggested_name}.{site}.home.arpa")
        if dhcp_name == "*":
            print("  notes: Unknown DHCP client; device did not supply hostname")
        else:
            print(f"  notes: Unknown DHCP client; DHCP hostname '{dhcp_name}'")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit YAML stubs for unknown DHCP lease clients")
    parser.add_argument(
        "--leases",
        default="/var/lib/misc/dnsmasq.leases",
        help="Path to dnsmasq.leases",
    )
    parser.add_argument(
        "--registry",
        default="docs/reference/network-registry.yaml",
        help="Path to network-registry.yaml",
    )
    parser.add_argument(
        "--site",
        required=True,
        help="Site name to use in generated stubs, e.g. reid or farm",
    )
    args = parser.parse_args()

    registry_path = Path(args.registry)
    leases_path = Path(args.leases)

    if not registry_path.exists():
        raise SystemExit(f"Registry not found: {registry_path}")

    known_macs = load_known_macs(registry_path)
    unknowns = load_unknown_leases(leases_path, known_macs)
    emit_yaml_stubs(unknowns, args.site)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
