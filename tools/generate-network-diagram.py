\
#!/usr/bin/env python3
"""
generate-network-diagram.py

Generate a Graphviz DOT file and, when Graphviz is available, an SVG network diagram
from docs/reference/network-registry.yaml.

Outputs into ./generated/diagrams by default:

- generated/diagrams/mudpi-network.dot
- generated/diagrams/mudpi-network.svg   (if `dot` is installed)

The diagram is intended to be an authoritative engineering view of the estate:
- site clusters
- site zones and subnets
- key hosts
- VPN overlay identities
- cross-site WireGuard relationships

Usage:
    python tools/generate-network-diagram.py
    python tools/generate-network-diagram.py \
        --registry docs/reference/network-registry.yaml \
        --output generated/diagrams
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml


def load_registry(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def site_sort_key(site_name: str) -> Tuple[int, str]:
    order = {
        "reid": 10,
        "barkingowl": 20,
        "trilogy": 30,
        "testboat": 40,
        "vpn": 50,
    }
    return (order.get(site_name, 999), site_name)


def label_for_site(site_name: str, site: Dict[str, Any]) -> str:
    lines = [site_name]
    if site.get("zone"):
        lines.append(site["zone"])
    if "lan" in site:
        lan = site["lan"]
        if lan.get("cidr"):
            lines.append(f'LAN {lan["cidr"]}')
        if lan.get("gateway"):
            lines.append(f'GW {lan["gateway"]}')
    if "overlay" in site:
        overlay = site["overlay"]
        if overlay.get("cidr"):
            lines.append(f'Overlay {overlay["cidr"]}')
        if overlay.get("hub"):
            lines.append(f'Hub {overlay["hub"]}')
    return "\\n".join(lines)


def label_for_host(host: Dict[str, Any], registry: Dict[str, Any]) -> str:
    lines: List[str] = [host["name"]]
    addresses = host.get("addresses", {})
    if "lan" in addresses:
        lines.append(f'LAN {addresses["lan"]}')
    if "vpn" in addresses:
        lines.append(f'VPN {addresses["vpn"]}')
    roles = host.get("roles", [])
    if roles:
        lines.append(", ".join(roles))
    return "\\n".join(lines)


def node_id_for_site(site_name: str) -> str:
    return f"site_{site_name}"


def node_id_for_host(host: Dict[str, Any]) -> str:
    return f'host_{host["site"]}_{host["name"]}'


def choose_site_anchor(site_name: str, hosts: List[Dict[str, Any]], sites: Dict[str, Any]) -> str | None:
    """
    Choose the best representative node in a site cluster for VPN linkage.
    Prefer the configured DNS server host for the site, otherwise first host with a VPN IP.
    """
    site = sites.get(site_name, {})
    dns_server_host = site.get("dns", {}).get("server_host")
    if dns_server_host:
        for host in hosts:
            if host["name"] == dns_server_host:
                return node_id_for_host(host)

    for host in hosts:
        if "vpn" in host.get("addresses", {}):
            return node_id_for_host(host)

    return None


def generate_dot(registry: Dict[str, Any]) -> str:
    sites = registry.get("sites", {})
    all_hosts = registry.get("hosts", [])

    hosts_by_site: Dict[str, List[Dict[str, Any]]] = {}
    for host in all_hosts:
        hosts_by_site.setdefault(host["site"], []).append(host)

    lines: List[str] = []
    lines.append("digraph mudpi_network {")
    lines.append("  graph [")
    lines.append('    rankdir="TB",')
    lines.append('    splines="ortho",')
    lines.append('    overlap=false,')
    lines.append('    nodesep=0.5,')
    lines.append('    ranksep=0.9,')
    lines.append('    pad=0.2,')
    lines.append('    labelloc="t",')
    lines.append('    label="MudPi Distributed Network",')
    lines.append('    fontsize=20')
    lines.append("  ];")
    lines.append("  node [shape=box, style=rounded, fontsize=10, margin=0.15];")
    lines.append("  edge [fontsize=9];")
    lines.append("")

    # VPN overlay cluster first
    vpn_site = sites.get("vpn", {})
    lines.append("  subgraph cluster_vpn {")
    lines.append('    label=' + quote(label_for_site("vpn", vpn_site)) + ";")
    lines.append('    style="rounded,dashed";')
    lines.append('    fontsize=12;')
    for host in sorted(hosts_by_site.get("vpn", []), key=lambda h: h["name"]):
        node_id = node_id_for_host(host)
        lines.append(f"    {node_id} [label={quote(label_for_host(host, registry))}];")
    # Include MudPi in overlay if it has VPN address even though it's a reid host.
    for host in sorted(hosts_by_site.get("reid", []), key=lambda h: h["name"]):
        if host["name"] == "mudpi" and "vpn" in host.get("addresses", {}):
            node_id = node_id_for_host(host)
            lines.append(f"    {node_id} [label={quote(label_for_host(host, registry))}];")
    lines.append("  }")
    lines.append("")

    # Site clusters (excluding vpn)
    for site_name in sorted((s for s in sites.keys() if s != "vpn"), key=site_sort_key):
        site = sites[site_name]
        lines.append(f"  subgraph cluster_{site_name} {{")
        lines.append("    label=" + quote(label_for_site(site_name, site)) + ";")
        lines.append('    style="rounded";')
        lines.append('    fontsize=12;')

        for host in sorted(hosts_by_site.get(site_name, []), key=lambda h: h["name"]):
            node_id = node_id_for_host(host)
            attrs = []
            attrs.append(f"label={quote(label_for_host(host, registry))}")
            if "gateway" in host.get("roles", []):
                attrs.append('shape=box3d')
            lines.append(f"    {node_id} [{', '.join(attrs)}];")

        # Local LAN backbone node for readability.
        if "lan" in site:
            lan_node = node_id_for_site(site_name)
            cidr = site["lan"].get("cidr", "LAN")
            lines.append(f"    {lan_node} [label={quote(cidr)}, shape=ellipse];")

            for host in sorted(hosts_by_site.get(site_name, []), key=lambda h: h["name"]):
                if "lan" in host.get("addresses", {}):
                    lines.append(f"    {lan_node} -> {node_id_for_host(host)} [arrowhead=none];")

        lines.append("  }")
        lines.append("")

    # Cross-site VPN links
    # Anchor from MudPi VPN presence.
    mudpi_node = None
    for host in hosts_by_site.get("reid", []):
        if host["name"] == "mudpi" and "vpn" in host.get("addresses", {}):
            mudpi_node = node_id_for_host(host)
            break

    if mudpi_node:
        for site_name in sorted((s for s in sites.keys() if s not in {"reid", "vpn"}), key=site_sort_key):
            anchor = choose_site_anchor(site_name, hosts_by_site.get(site_name, []), sites)
            if anchor:
                lines.append(f"  {mudpi_node} -> {anchor} [dir=both, style=dashed, label=\"WireGuard\"];")
        for host in hosts_by_site.get("vpn", []):
            if "vpn" in host.get("addresses", {}) and host["name"] != "mudpi":
                lines.append(f"  {mudpi_node} -> {node_id_for_host(host)} [dir=both, style=dashed, label=\"WireGuard\"];")

    # Optional forwarding relationships from registry
    forwarding = registry.get("forwarding", {})
    mudpi_forward = forwarding.get("mudpi", {}).get("conditional_forwarders", {})
    if mudpi_forward:
        zone_to_anchor: Dict[str, str] = {}
        for site_name, site in sites.items():
            zone = site.get("zone")
            anchor = choose_site_anchor(site_name, hosts_by_site.get(site_name, []), sites)
            if zone and anchor:
                zone_to_anchor[zone] = anchor
        for zone, _server_ip in sorted(mudpi_forward.items()):
            target = zone_to_anchor.get(zone)
            if mudpi_node and target:
                lines.append(f"  {mudpi_node} -> {target} [style=dotted, label=\"DNS forward {zone}\"];")

    lines.append("}")
    return "\n".join(lines) + "\n"


def render_svg(dot_path: Path, svg_path: Path) -> bool:
    dot_bin = shutil.which("dot")
    if not dot_bin:
        return False
    subprocess.run([dot_bin, "-Tsvg", str(dot_path), "-o", str(svg_path)], check=True)
    return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Graphviz network diagram from YAML registry")
    parser.add_argument(
        "--registry",
        default="docs/reference/network-registry.yaml",
        help="Path to YAML registry (default: docs/reference/network-registry.yaml)",
    )
    parser.add_argument(
        "--output",
        default="generated/diagrams",
        help="Output directory (default: generated/diagrams)",
    )
    parser.add_argument(
        "--name",
        default="mudpi-network",
        help="Base name for DOT/SVG outputs (default: mudpi-network)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    registry_path = Path(args.registry)
    output_dir = Path(args.output)
    ensure_dir(output_dir)

    registry = load_registry(registry_path)
    dot_text = generate_dot(registry)

    dot_path = output_dir / f"{args.name}.dot"
    svg_path = output_dir / f"{args.name}.svg"

    dot_path.write_text(dot_text, encoding="utf-8")
    print(f"Wrote {dot_path}")

    try:
        rendered = render_svg(dot_path, svg_path)
    except subprocess.CalledProcessError as exc:
        print(f"Graphviz failed while rendering SVG: {exc}")
        return 1

    if rendered:
        print(f"Wrote {svg_path}")
    else:
        print("Graphviz 'dot' not found; DOT file was generated but SVG was not rendered.")
        print("Install graphviz to enable SVG output.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
