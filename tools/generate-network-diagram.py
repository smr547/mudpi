#!/usr/bin/env python3
from __future__ import annotations
import argparse, html, shutil, subprocess
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

def esc(value: str) -> str:
    return html.escape(str(value), quote=True)

def site_sort_key(site_name: str) -> Tuple[int, str]:
    order = {"reid": 10, "barkingowl": 20, "trilogy": 30, "testboat": 40, "vpn": 50}
    return (order.get(site_name, 999), site_name)

def host_fqdn(host: Dict[str, Any], root: str) -> str:
    return f'{host["name"]}.{host["site"]}.{root}'

def host_vpn_fqdn(host: Dict[str, Any], root: str) -> str:
    return f'{host["name"]}.vpn.{root}'

def classify(host: Dict[str, Any]) -> str:
    roles = set(host.get("roles", []))
    if "gateway" in roles:
        return "gateway"
    if {"dns", "dhcp", "wireguard-hub"} & roles:
        return "infra"
    if {"grafana", "influxdb", "signalk", "app-host", "print-server"} & roles:
        return "app"
    if {"weather", "appliance", "printer", "solar-monitor"} & roles:
        return "appliance"
    if "roaming-client" in roles:
        return "client"
    return "host"

def importance(host: Dict[str, Any]) -> str:
    return host.get("diagram", {}).get("importance", "secondary")

def include(host: Dict[str, Any], view: str) -> bool:
    if host.get("diagram", {}).get("include") is False:
        return False
    if view == "full":
        return importance(host) != "hidden"
    return importance(host) in {"primary", "secondary"}

def node_id_for_host(host: Dict[str, Any]) -> str:
    return f'host_{host["site"]}_{host["name"]}'

def node_id_for_site(site: str) -> str:
    return f"site_{site}"

def style_for(host: Dict[str, Any]) -> Dict[str, str]:
    c = classify(host)
    if c == "gateway":
        return {"shape":"box3d","style":'"rounded,filled"',"fillcolor":"white","penwidth":"1.8"}
    if c == "infra":
        return {"shape":"plain","style":'"filled"',"fillcolor":"white","penwidth":"2.1"}
    if c == "app":
        return {"shape":"plain","style":'"filled"',"fillcolor":"white","penwidth":"1.5"}
    if c == "appliance":
        return {"shape":"plain","style":'"filled"',"fillcolor":"white","penwidth":"1.2"}
    return {"shape":"plain","style":'"filled"',"fillcolor":"white","penwidth":"1.0"}

def host_label(host: Dict[str, Any], root: str) -> str:
    addrs = host.get("addresses", {})
    roles = " • ".join(host.get("roles", [])) if host.get("roles") else "host"
    rows = [
        f'<TR><TD ALIGN="CENTER"><B>{esc(host["name"])}</B></TD></TR>',
        f'<TR><TD ALIGN="CENTER"><FONT POINT-SIZE="10">{esc(host_fqdn(host, root))}</FONT></TD></TR>',
    ]
    if "lan" in addrs:
        rows.append(f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="10">LAN {esc(addrs["lan"])}</FONT></TD></TR>')
    if "vpn" in addrs:
        rows.append(f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="10">VPN {esc(addrs["vpn"])} ({esc(host_vpn_fqdn(host, root))})</FONT></TD></TR>')
    rows.append(f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="10">{esc(roles)}</FONT></TD></TR>')
    if importance(host) == "tertiary":
        rows.append('<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="10">overview: hidden</FONT></TD></TR>')
    border = "2" if classify(host) in {"infra","gateway"} else "1"
    return f'<<TABLE BORDER="{border}" CELLBORDER="1" CELLSPACING="0" CELLPADDING="5">{"".join(rows)}</TABLE>>'

def site_label(name: str, site: Dict[str, Any]) -> str:
    lines = [f"<B>{esc(name)}</B>"]
    if site.get("zone"):
        lines.append(esc(site["zone"]))
    if "lan" in site:
        if site["lan"].get("cidr"):
            lines.append(esc(f'LAN {site["lan"]["cidr"]}'))
        if site["lan"].get("gateway"):
            lines.append(esc(f'GW {site["lan"]["gateway"]}'))
    if "overlay" in site:
        if site["overlay"].get("cidr"):
            lines.append(esc(f'Overlay {site["overlay"]["cidr"]}'))
        if site["overlay"].get("hub"):
            lines.append(esc(f'Hub {site["overlay"]["hub"]}'))
    if site.get("dns", {}).get("server_host"):
        lines.append(esc(f'DNS {site["dns"]["server_host"]}'))
    if site.get("dhcp", {}).get("authority"):
        lines.append(esc(f'DHCP {site["dhcp"]["authority"]}'))
    return "<" + "<BR/>".join(lines) + ">"

def choose_anchor(site_name: str, hosts: List[Dict[str, Any]], sites: Dict[str, Any]) -> str | None:
    server_host = sites.get(site_name, {}).get("dns", {}).get("server_host")
    if server_host:
        for host in hosts:
            if host["name"] == server_host:
                return node_id_for_host(host)
    for host in hosts:
        if "vpn" in host.get("addresses", {}):
            return node_id_for_host(host)
    return None

def generate_dot(registry: Dict[str, Any], view: str) -> str:
    root = registry["meta"]["private_root"]
    sites = registry.get("sites", {})
    hosts = [h for h in registry.get("hosts", []) if include(h, view)]
    hosts_by_site: Dict[str, List[Dict[str, Any]]] = {}
    for host in hosts:
        hosts_by_site.setdefault(host["site"], []).append(host)
    title = "MudPi Distributed Network" if view == "overview" else "MudPi Distributed Network (Full)"
    out = [
        "digraph mudpi_network {",
        "  graph [rankdir=\"TB\", splines=\"polyline\", overlap=false, nodesep=0.5, ranksep=1.0, pad=0.25, labelloc=\"t\", label=" + q(title) + ", fontsize=20, fontname=\"Helvetica\"];",
        '  node [fontname="Helvetica", fontsize=10, margin=0.12];',
        '  edge [fontname="Helvetica", fontsize=9];',
        "",
    ]
    vpn_site = sites.get("vpn", {})
    out += ["  subgraph cluster_vpn {", "    label=" + site_label("vpn", vpn_site) + ";", '    style="rounded,dashed";', '    penwidth=1.5;']
    for host in sorted(hosts_by_site.get("vpn", []), key=lambda h: h["name"]):
        s = style_for(host)
        out.append(f"    {node_id_for_host(host)} [label={host_label(host, root)}, shape={s['shape']}, style={s['style']}, fillcolor={q(s['fillcolor'])}, penwidth={s['penwidth']}];")
    for host in sorted(hosts_by_site.get("reid", []), key=lambda h: h["name"]):
        if host["name"] == "mudpi" and "vpn" in host.get("addresses", {}):
            s = style_for(host)
            out.append(f"    {node_id_for_host(host)} [label={host_label(host, root)}, shape={s['shape']}, style={s['style']}, fillcolor={q(s['fillcolor'])}, penwidth={s['penwidth']}];")
    out += ["  }", ""]
    for site_name in sorted((s for s in sites if s != "vpn"), key=site_sort_key):
        site = sites[site_name]
        out += [f"  subgraph cluster_{site_name} {{", "    label=" + site_label(site_name, site) + ";", '    style="rounded";', '    penwidth=1.5;']
        shosts = sorted(hosts_by_site.get(site_name, []), key=lambda h: h["name"])
        for host in shosts:
            s = style_for(host)
            out.append(f"    {node_id_for_host(host)} [label={host_label(host, root)}, shape={s['shape']}, style={s['style']}, fillcolor={q(s['fillcolor'])}, penwidth={s['penwidth']}];")
        if "lan" in site:
            out.append(f'    {node_id_for_site(site_name)} [label={q(site["lan"].get("cidr","LAN"))}, shape=ellipse, style="dashed", penwidth=1.0];')
            for host in shosts:
                if "lan" in host.get("addresses", {}):
                    out.append(f"    {node_id_for_site(site_name)} -> {node_id_for_host(host)} [arrowhead=none, penwidth=1.0];")
        out += ["  }", ""]
    mudpi_node = None
    for host in hosts_by_site.get("reid", []):
        if host["name"] == "mudpi" and "vpn" in host.get("addresses", {}):
            mudpi_node = node_id_for_host(host)
            break
    if mudpi_node:
        for site_name in sorted((s for s in sites if s not in {"reid", "vpn"}), key=site_sort_key):
            anchor = choose_anchor(site_name, hosts_by_site.get(site_name, []), sites)
            if anchor:
                out.append(f'  {mudpi_node} -> {anchor} [dir=both, style=dashed, penwidth=1.4, label="WireGuard"];')
        for host in hosts_by_site.get("vpn", []):
            if "vpn" in host.get("addresses", {}) and host["name"] != "mudpi":
                out.append(f'  {mudpi_node} -> {node_id_for_host(host)} [dir=both, style=dashed, penwidth=1.4, label="WireGuard"];')
        for zone, _ip in sorted(registry.get("forwarding", {}).get("mudpi", {}).get("conditional_forwarders", {}).items()):
            for site_name, site in sites.items():
                if site.get("zone") == zone:
                    anchor = choose_anchor(site_name, hosts_by_site.get(site_name, []), sites)
                    if anchor:
                        out.append(f'  {mudpi_node} -> {anchor} [style=dotted, penwidth=1.0, label={q("DNS forward " + zone)}];')
    out.append("}")
    return "\n".join(out) + "\n"

def render_svg(dot_path: Path, svg_path: Path) -> bool:
    dot_bin = shutil.which("dot")
    if not dot_bin:
        return False
    subprocess.run([dot_bin, "-Tsvg", str(dot_path), "-o", str(svg_path)], check=True)
    return True

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default="docs/reference/network-registry.yaml")
    ap.add_argument("--output", default="generated/diagrams")
    args = ap.parse_args()
    registry = load_registry(Path(args.registry))
    outdir = Path(args.output)
    ensure_dir(outdir)
    for view, base in [("overview", "mudpi-network"), ("full", "mudpi-network-full")]:
        dot_path = outdir / f"{base}.dot"
        svg_path = outdir / f"{base}.svg"
        dot_path.write_text(generate_dot(registry, view), encoding="utf-8")
        print(f"Wrote {dot_path}")
        if render_svg(dot_path, svg_path):
            print(f"Wrote {svg_path}")
        else:
            print("Graphviz 'dot' not found; generated DOT files only.")
            break
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
