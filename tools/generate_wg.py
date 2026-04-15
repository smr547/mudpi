#!/usr/bin/env python3
"""
Minimal WireGuard config generator for MudPi.

Reads:
  ./wireguard/registry.yaml

Generates:
  ./wireguard/generated/wg0.conf
  ./wireguard/generated/clients/<peer-name>.conf

This minimal version supports:
- one hub
- site peers
- human peers
- existing keys stored under key_ref directories
- generation of client configs for human peers whose private/public/psk exist

Key layout convention:
  <repo_root>/wireguard/
    registry.yaml
    hub/
      mudpi/
        private.key
        public.key
    peers/
      shedpi/
        public.key
      sten-laptop/
        private.key
        public.key
        preshared.key
      sten-phone/
        private.key
        public.key
        preshared.key
      james-laptop/
        private.key
        public.key
        preshared.key

Notes:
- Site peers are expected to have at least a public.key.
- Human peers are expected to have private.key, public.key and preshared.key to generate client configs.
- Hub config uses hub private key and each peer's public key.
- Human peer client configs are generated only when all required key files exist.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


def read_text_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    return path.read_text(encoding="utf-8").strip()


def optional_read_text_file(path: Path) -> str | None:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8").strip()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def format_allowed_ips(items: list[str]) -> str:
    return ", ".join(items)


def load_registry(registry_path: Path) -> dict[str, Any]:
    with registry_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("Top-level YAML structure must be a mapping")
    return data


def validate_registry(data: dict[str, Any]) -> None:
    required_top = ["hub", "zones", "peers"]
    for key in required_top:
        if key not in data:
            raise ValueError(f"registry.yaml missing top-level key: {key}")

    if not isinstance(data["zones"], dict):
        raise ValueError("zones must be a mapping")

    if not isinstance(data["peers"], list):
        raise ValueError("peers must be a list")


def resolve_zone_subnets(peer: dict[str, Any], zones: dict[str, Any]) -> list[str]:
    subnets: list[str] = []
    for zone_name in peer.get("access", []):
        if zone_name not in zones:
            raise ValueError(f"Peer {peer['name']} references unknown zone: {zone_name}")
        subnet = zones[zone_name].get("subnet")
        if not subnet:
            raise ValueError(f"Zone {zone_name} missing subnet")
        subnets.append(str(subnet))
    return subnets


def build_hub_config(base_dir: Path, registry: dict[str, Any]) -> str:
    hub = registry["hub"]
    peers = registry["peers"]

    hub_key_dir = base_dir / str(hub["key_ref"])
    hub_private_key = read_text_file(hub_key_dir / "private.key")

    lines: list[str] = []
    lines.append("[Interface]")
    lines.append(f"Address = {hub['vpn_address']}/24")
    lines.append(f"ListenPort = {hub['listen_port']}")
    lines.append(f"PrivateKey = {hub_private_key}")
    lines.append("")

    for peer in peers:
        peer_name = str(peer["name"])
        peer_type = str(peer["peer_type"])
        peer_key_dir = base_dir / str(peer["key_ref"])

        public_key = read_text_file(peer_key_dir / "public.key")
        preshared_key = optional_read_text_file(peer_key_dir / "preshared.key")

        allowed_ips: list[str] = [f"{peer['vpn_address']}/32"]
        if peer_type == "site":
            allowed_ips.extend([str(x) for x in peer.get("routes", [])])
        elif peer_type == "human":
            pass
        else:
            raise ValueError(f"Unknown peer_type for {peer_name}: {peer_type}")

        lines.append(f"# {peer_name}")
        lines.append("[Peer]")
        lines.append(f"PublicKey = {public_key}")
        if preshared_key:
            lines.append(f"PresharedKey = {preshared_key}")
        lines.append(f"AllowedIPs = {format_allowed_ips(allowed_ips)}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build_human_client_config(base_dir: Path, registry: dict[str, Any], peer: dict[str, Any]) -> str:
    hub = registry["hub"]
    zones = registry["zones"]

    peer_key_dir = base_dir / str(peer["key_ref"])
    private_key = read_text_file(peer_key_dir / "private.key")
    preshared_key = read_text_file(peer_key_dir / "preshared.key")

    hub_public_key = read_text_file((base_dir / str(hub["key_ref"])) / "public.key")

    allowed_ips = resolve_zone_subnets(peer, zones)

    lines: list[str] = []
    lines.append("[Interface]")
    lines.append(f"PrivateKey = {private_key}")
    lines.append(f"Address = {peer['vpn_address']}/32")
    lines.append("DNS = 10.1.1.3")
    lines.append("")
    lines.append("[Peer]")
    lines.append(f"PublicKey = {hub_public_key}")
    lines.append(f"PresharedKey = {preshared_key}")
    lines.append(f"Endpoint = {hub['endpoint']}")
    lines.append(f"AllowedIPs = {format_allowed_ips(allowed_ips)}")
    lines.append("PersistentKeepalive = 25")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    repo_root = Path.cwd()
    wireguard_dir = repo_root / "wireguard"
    registry_path = wireguard_dir / "registry.yaml"
    generated_dir = wireguard_dir / "generated"
    clients_dir = generated_dir / "clients"

    ensure_dir(generated_dir)
    ensure_dir(clients_dir)

    registry = load_registry(registry_path)
    validate_registry(registry)

    # Generate hub config
    wg0_text = build_hub_config(wireguard_dir, registry)
    wg0_path = generated_dir / "wg0.conf"
    wg0_path.write_text(wg0_text, encoding="utf-8")

    # Generate client configs for human peers that have full key material
    generated_clients: list[str] = []
    skipped_clients: list[str] = []

    for peer in registry["peers"]:
        if str(peer.get("peer_type")) != "human":
            continue

        peer_key_dir = wireguard_dir / str(peer["key_ref"])
        required_files = [
            peer_key_dir / "private.key",
            peer_key_dir / "public.key",
            peer_key_dir / "preshared.key",
        ]
        if all(path.exists() for path in required_files):
            client_text = build_human_client_config(wireguard_dir, registry, peer)
            client_path = clients_dir / f"{peer['name']}.conf"
            client_path.write_text(client_text, encoding="utf-8")
            generated_clients.append(str(peer["name"]))
        else:
            skipped_clients.append(str(peer["name"]))

    print(f"Generated hub config: {wg0_path}")
    if generated_clients:
        print("Generated client configs:")
        for name in generated_clients:
            print(f"  - {clients_dir / (name + '.conf')}")
    if skipped_clients:
        print("Skipped human peers missing key material:")
        for name in skipped_clients:
            print(f"  - {name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
