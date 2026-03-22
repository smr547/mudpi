\
#!/usr/bin/env python3
"""
generate-network-diagram.py

Generate Graphviz DOT and SVG network diagrams from docs/reference/network-registry.yaml.

Outputs into ./generated/diagrams by default:

- generated/diagrams/mudpi-network.dot
- generated/diagrams/mudpi-network.svg   (if Graphviz `dot` is installed)

This version adds:
- HTML-style node labels for a cleaner engineering look
- role-based node styling
- clearer site cluster labels
- selective inclusion of hosts (default: all current hosts)
- more deliberate control-plane / data-plane visual separation

Usage:
    python tools/generate-network-diagram.py
    python tools/generate-network-diagram.py \
        --registry docs/reference/network-registry.yaml \
        --output generated/diagrams
"""

from __future__ import annotations

import argparse
import html
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


def q(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def html_escape(value: str) -> str:
    return html.escape(str(value), quote=True)


def site_sort_key(site_name: str) -> Tuple[int, str]:
    order = {
        "reid": 10,
        "barkingowl": 20,
        "trilogy": 30,
        "testboat": 40,
        "vpn": 50,
    }
    return (order.get(site_name, 999), site_name)


def node_id_for_site(site_name: str) -> str:
    return f"site_{site_name}"


def node_id_for_host(host: Dict[str, Any]) -> str:
    return f'host_{host["site"]}_{host["name"]}'


def host_fqdn(host: Dict[str, Any], registry: Dict[str, Any]) -> str:
    private_root = registry["meta"]["private_root"]
    return f'{host["name"]}.{host["site"]}.{private_root}'


def host_vpn_fqdn(host: Dict[str, Any], registry: Dict[str, Any]) -> str:
    private_root = registry["meta"]["private_root"]
    return f'{host["name"]}.vpn.{private_root}'


def classify_host(host: Dict[str, Any]) -> str:
    roles = set(host.get("roles", []))
    name = host.get("name", "")

    if "gateway" in roles:
        return "gateway"
    if {"dns", "dhcp", "wireguard-hub"} & roles:
        return "infra"
    if "app-host" in roles or {"grafana", "influxdb", "signalk"} & roles:
        return "app"
    if {"weather", "sensor"} & roles:
        return "appliance"
    if "roaming-client" in roles or name in {"laptop", "phone", "tablet"}:
        return "client"
    return "host"


def node_style(host: Dict[str, Any]) -> Dict[str, str]:
    cls = classify_host(host)

    if cls == "gateway":
        return {
            "shape": "box3d",
            "style": '"rounded,filled"',
            "fillcolor": "white",
            "penwidth": "1.6",
        }
    if cls == "infra":
        return {
            "shape": "plain",
            "style": '"filled"',
            "fillcolor": "white",
            "penwidth": "2.0",
        }
    if cls == "app":
        return {
            "shape": "plain",
            "style": '"filled"',
            "fillcolor": "white",
            "penwidth": "1.4",
        }
    if cls == "appliance":
        return {
            "shape": "plain",
            "style": '"filled"',
            "fillcolor": "white",
            "penwidth": "1.2",
        }
    if cls == "client":
        return {
            "shape": "plain",
            "style": '"filled"',
            "fillcolor": "white",
            "penwidth": "1.0",
        }
    return {
        "shape": "plain",
        "style": '"filled"',
        "fillcolor": "white",
        "penwidth": "1.0",
    }


def build_host_label(host: Dict[str, Any], registry: Dict[str, Any]) -> str:
    cls = classify_host(host)
    addresses = host.get("addresses", {})
    roles = host.get("roles", [])
    role_text = " • ".join(roles) if roles else "host"

    title = host.get("diagram", {}).get("label", host["name"])
    fqdn = host_fqdn(host, registry)

    rows: List[str] = []
    rows.append(
        f'<TR><TD ALIGN="CENTER"><B>{html_escape(title)}</B></TD></TR>'
    )
    rows.append(
        f'<TR><TD ALIGN="CENTER"><FONT POINT-SIZE="10">{html_escape(fqdn)}</FONT></TD></TR>'
    )

    if "lan" in addresses:
        rows.append(
            f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="10">LAN {html_escape(addresses["lan"])}</FONT></TD></TR>'
        )
    if "vpn" in addresses:
        vpn_name = host_vpn_fqdn(host, registry)
        rows.append(
            f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="10">VPN {html_escape(addresses["vpn"])} ({html_escape(vpn_name)})</FONT></TD></TR>'
        )

    rows.append(
        f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="10">{html_escape(role_text)}</FONT></TD></TR>'
    )

    border = "1"
    cellborder = "1"
    cellpadding = "5"

    if cls == "infra":
        border = "2"
        cellborder = "1"
    elif cls == "gateway":
        border = "2"
    elif cls == "appliance":
        cellpadding = "4"

    return (
        "<<TABLE BORDER=\"{border}\" CELLBORDER=\"{cellborder}\" "
        "CELLSPACING=\"0\" CELLPADDING=\"{cellpadding}\">"
        "{rows}"
        "</TABLE>>"
    ).format(border=border, cellborder=cellborder, cellpadding=cellpadding, rows="".join(rows))


def build_site_cluster_label(site_name: str, site: Dict[str, Any]) -> str:
    lines = [f"<B>{html_escape(site_name)}</B>"]

    zone = site.get("zone")
    if zone:
        lines.append(html_escape(zone))

    if "lan" in site:
        lan = site["lan"]
        if lan.get("cidr"):
            lines.append(html_escape(f'LAN {lan["cidr"]}'))
        if lan.get("gateway"):
            lines.append(html_escape(f'GW {lan["gateway"]}'))
    if "overlay" in site:
        overlay = site["overlay"]
        if overlay.get("cidr"):
            lines.append(html_escape(f'Overlay {overlay["cidr"]}'))
        if overlay.get("hub"):
            lines.append(html_escape(f'Hub {overlay["hub"]}'))

    dns = site.get("dns", {})
    if dns.get("server_host"):
        lines.append(html_escape(f'DNS {dns["server_host"]}'))
    dhcp = site.get("dhcp", {})
    if dhcp.get("authority"):
        lines.append(html_escape(f'DHCP {dhcp["authority"]}'))

    return "<" + "<BR/>".join(lines) + ">"


def include_host_in_diagram(host: Dict[str, Any]) -> bool:
    diagram_cfg = host.get("diagram", {})
    if "include" in diagram_cfg:
        return bool(diagram_cfg["include"])
    return True


def choose_site_anchor(site_name: str, hosts: List[Dict[str, Any]], sites: Dict[str, Any]) -> str | None:
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
    all_hosts = [h for h in registry.get("hosts", []) if include_host_in_diagram(h)]

    hosts_by_site: Dict[str, List[Dict[str, Any]]] = {}
    for host in all_hosts:
        hosts_by_site.setdefault(host["site"], []).append(host)

    lines: List[str] = []
    lines.append("digraph mudpi_network {")
    lines.append("  graph [")
    lines.append('    rankdir="TB",')
    lines.append('    splines="polyline",')
    lines.append('    overlap=false,')
    lines.append('    nodesep=0.5,')
    lines.append('    ranksep=1.0,')
    lines.append('    pad=0.25,')
    lines.append('    labelloc="t",')
    lines.append('    label="MudPi Distributed Network",')
    lines.append('    fontsize=20,')
    lines.append('    fontname="Helvetica"')
    lines.append("  ];")
    lines.append('  node [fontname="Helvetica", fontsize=10, margin=0.12];')
    lines.append('  edge [fontname="Helvetica", fontsize=9];')
    lines.append("")

    # VPN cluster
    vpn_site = sites.get("vpn", {})
    lines.append("  subgraph cluster_vpn {")
    lines.append("    label=" + build_site_cluster_label("vpn", vpn_site) + ";")
    lines.append('    style="rounded,dashed";')
    lines.append('    penwidth=1.5;')
    lines.append('    fontsize=12;')

    vpn_hosts = sorted(hosts_by_site.get("vpn", []), key=lambda h: h["name"])
    reid_hosts = sorted(hosts_by_site.get("reid", []), key=lambda h: h["name"])

    for host in vpn_hosts:
        nid = node_id_for_host(host)
        style = node_style(host)
        lines.append(
            f"    {nid} [label={build_host_label(host, registry)}, shape={style['shape']}, "
            f"style={style['style']}, fillcolor={q(style['fillcolor'])}, penwidth={style['penwidth']}];"
        )

    # Also show MudPi in VPN cluster if it has a VPN identity.
    for host in reid_hosts:
        if host["name"] == "mudpi" and "vpn" in host.get("addresses", {}):
            nid = node_id_for_host(host)
            style = node_style(host)
            lines.append(
                f"    {nid} [label={build_host_label(host, registry)}, shape={style['shape']}, "
                f"style={style['style']}, fillcolor={q(style['fillcolor'])}, penwidth={style['penwidth']}];"
            )
    lines.append("  }")
    lines.append("")

    # Site clusters
    for site_name in sorted((s for s in sites.keys() if s != "vpn"), key=site_sort_key):
        site = sites[site_name]
        lines.append(f"  subgraph cluster_{site_name} {{")
        lines.append("    label=" + build_site_cluster_label(site_name, site) + ";")
        lines.append('    style="rounded";')
        lines.append('    penwidth=1.5;')
        lines.append('    fontsize=12;')

        site_hosts = sorted(hosts_by_site.get(site_name, []), key=lambda h: h["name"])
        for host in site_hosts:
            nid = node_id_for_host(host)
            style = node_style(host)
            lines.append(
                f"    {nid} [label={build_host_label(host, registry)}, shape={style['shape']}, "
                f"style={style['style']}, fillcolor={q(style['fillcolor'])}, penwidth={style['penwidth']}];"
            )

        # local LAN backbone
        if "lan" in site:
            lan_node = node_id_for_site(site_name)
            cidr = site["lan"].get("cidr", "LAN")
            lines.append(
                f"    {lan_node} [label={q(cidr)}, shape=ellipse, style=\"dashed\", penwidth=1.0];"
            )
            for host in site_hosts:
                if "lan" in host.get("addresses", {}):
                    lines.append(
                        f"    {lan_node} -> {node_id_for_host(host)} [arrowhead=none, penwidth=1.0];"
                    )
        lines.append("  }")
        lines.append("")

    # Cross-site WG links
    mudpi_node = None
    for host in hosts_by_site.get("reid", []):
        if host["name"] == "mudpi" and "vpn" in host.get("addresses", {}):
            mudpi_node = node_id_for_host(host)
            break

    if mudpi_node:
        for site_name in sorted((s for s in sites.keys() if s not in {"reid", "vpn"}), key=site_sort_key):
            anchor = choose_site_anchor(site_name, hosts_by_site.get(site_name, []), sites)
            if anchor:
                lines.append(
                    f"  {mudpi_node} -> {anchor} [dir=both, style=dashed, penwidth=1.4, label=\"WireGuard\"];"
                )
        for host in hosts_by_site.get("vpn", []):
            if "vpn" in host.get("addresses", {}) and host["name"] != "mudpi":
                lines.append(
                    f"  {mudpi_node} -> {node_id_for_host(host)} [dir=both, style=dashed, penwidth=1.4, label=\"WireGuard\"];"
                )

    # DNS forwarding hints
    mudpi_forward = registry.get("forwarding", {}).get("mudpi", {}).get("conditional_forwarders", {})
    if mudpi_forward and mudpi_node:
        zone_to_anchor: Dict[str, str] = {}
        for site_name, site in sites.items():
            zone = site.get("zone")
            anchor = choose_site_anchor(site_name, hosts_by_site.get(site_name, []), sites)
            if zone and anchor:
                zone_to_anchor[zone] = anchor

        for zone, _server_ip in sorted(mudpi_forward.items()):
            anchor = zone_to_anchor.get(zone)
            if anchor:
                lines.append(
                    f"  {mudpi_node} -> {anchor} [style=dotted, penwidth=1.0, label={q('DNS forward ' + zone)}];"
                )

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
        help="Base name for output files (default: mudpi-network)",
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
