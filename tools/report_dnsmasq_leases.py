#!/usr/bin/env python3
"""
Report active dnsmasq leases, enriched from network-registry.yaml.

Columns:
- Remaining: time until lease expiry as HH:MM:SS
- Expiry: absolute expiry time
- IP
- MAC
- DHCP Name: hostname supplied by client in DHCP, if any
- DNS Name: canonical DNS name from registry, if known
- Status: KNOWN / UNKNOWN

Sorted by descending expiry time.
"""

from __future__ import annotations

import argparse
import datetime as dt
import ipaddress
import sys
import time
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


def load_registry(registry_path: Path) -> dict[str, str]:
    data = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    hosts = data.get("hosts", {})
    mac_to_dns: dict[str, str] = {}

    def process_host(host: dict[str, Any], default_name: str | None = None) -> None:
        dns = host.get("dns") if isinstance(host.get("dns"), dict) else {}
        canonical = dns.get("canonical")
        if not canonical:
            name = host.get("name") or host.get("id") or default_name
            site = host.get("site")
            if name and site:
                canonical = f"{name}.{site}.home.arpa"

        macs: list[str] = []

        top_mac = normalize_mac(host.get("mac"))
        if top_mac:
            macs.append(top_mac)

        mac_dict = host.get("macs")
        if isinstance(mac_dict, dict):
            for value in mac_dict.values():
                mac = normalize_mac(value)
                if mac:
                    macs.append(mac)

        for mac in macs:
            if canonical:
                mac_to_dns[mac] = str(canonical)

    if isinstance(hosts, list):
        for item in hosts:
            if isinstance(item, dict):
                process_host(item)
    elif isinstance(hosts, dict):
        for key, value in hosts.items():
            if isinstance(value, dict):
                process_host(value, default_name=str(key))

    return mac_to_dns


def format_remaining(expiry_epoch: int, now_epoch: int) -> str:
    remaining = max(0, expiry_epoch - now_epoch)
    hours = remaining // 3600
    minutes = (remaining % 3600) // 60
    seconds = remaining % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def parse_leases(leases_path: Path, mac_to_dns: dict[str, str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    now = int(time.time())

    if not leases_path.exists():
        return rows

    for raw_line in leases_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) < 4:
            continue

        expiry = int(parts[0])
        mac = normalize_mac(parts[1]) or parts[1]
        ip = parts[2]
        dhcp_name = parts[3]
        client_id = parts[4] if len(parts) > 4 else "*"

        try:
            ipaddress.IPv4Address(ip)
        except ValueError:
            continue

        dns_name = mac_to_dns.get(mac, "-")
        status = "KNOWN" if dns_name != "-" else "UNKNOWN"

        rows.append(
            {
                "expiry_epoch": str(expiry),
                "remaining": format_remaining(expiry, now),
                "expiry_abs": dt.datetime.fromtimestamp(expiry).strftime("%Y-%m-%d %H:%M:%S"),
                "ip": ip,
                "mac": mac,
                "dhcp_name": dhcp_name,
                "dns_name": dns_name,
                "status": status,
                "client_id": client_id,
            }
        )

    rows.sort(key=lambda r: int(r["expiry_epoch"]), reverse=True)
    return rows


def print_table(rows: list[dict[str, str]], show_client_id: bool) -> None:
    if not rows:
        print("No leases found.")
        return

    headers = ["Remaining", "Expiry", "IP", "MAC", "DHCP Name", "DNS Name", "Status"]
    if show_client_id:
        headers.append("Client ID")

    table_rows: list[list[str]] = []
    for row in rows:
        out = [
            row["remaining"],
            row["expiry_abs"],
            row["ip"],
            row["mac"],
            row["dhcp_name"],
            row["dns_name"],
            row["status"],
        ]
        if show_client_id:
            out.append(row["client_id"])
        table_rows.append(out)

    widths = [len(h) for h in headers]
    for tr in table_rows:
        for i, cell in enumerate(tr):
            widths[i] = max(widths[i], len(cell))

    def fmt_line(cols: list[str]) -> str:
        return "  ".join(col.ljust(widths[i]) for i, col in enumerate(cols))

    print(fmt_line(headers))
    print(fmt_line(["-" * w for w in widths]))
    for tr in table_rows:
        print(fmt_line(tr))

    unknowns = [r for r in rows if r["status"] == "UNKNOWN"]
    if unknowns:
        print()
        print("Unknown devices:")
        for r in unknowns:
            dhcp_label = r["dhcp_name"] if r["dhcp_name"] != "*" else "(no dhcp hostname)"
            print(f"  {r['ip']:15}  {r['mac']:17}  {dhcp_label}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Report dnsmasq leases enriched from network-registry.yaml")
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
        "--show-client-id",
        action="store_true",
        help="Include DHCP client-id column",
    )
    args = parser.parse_args()

    registry_path = Path(args.registry)
    leases_path = Path(args.leases)

    if not registry_path.exists():
        print(f"Registry not found: {registry_path}", file=sys.stderr)
        return 2

    mac_to_dns = load_registry(registry_path)
    rows = parse_leases(leases_path, mac_to_dns)
    print_table(rows, show_client_id=args.show_client_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
