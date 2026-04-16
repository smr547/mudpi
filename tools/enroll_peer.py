#!/usr/bin/env python3
"""
Create WireGuard key material for a named peer and update ./wireguard/registry.yaml.

Usage:
  python3 wireguard/enroll_peer.py james-laptop

What it does:
- loads ./wireguard/registry.yaml
- finds the named peer in peers[]
- creates the directory referenced by key_ref
- generates:
    private.key
    public.key
    preshared.key
  for human peers if they do not already exist
- updates registry fields:
    key_status: existing
    enrollment_status: complete
- writes the updated registry back to disk

Notes:
- This tool is intentionally simple and assumes a single trusted operator.
- It will NOT overwrite existing key files unless --force is supplied.
- It requires the `wg` command to be installed and in PATH.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


def run_checked(cmd: list[str], input_text: str | None = None) -> str:
    result = subprocess.run(
        cmd,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return result.stdout.strip()


def load_registry(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("registry.yaml top-level structure must be a mapping")
    if "peers" not in data or not isinstance(data["peers"], list):
        raise ValueError("registry.yaml must contain a peers list")
    return data


def save_registry(path: Path, data: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            data,
            f,
            default_flow_style=False,
            sort_keys=False,
            indent=2,
        )


def find_peer(data: dict[str, Any], peer_name: str) -> dict[str, Any]:
    matches = [peer for peer in data["peers"] if str(peer.get("name")) == peer_name]
    if not matches:
        raise ValueError(f"Peer not found in registry: {peer_name}")
    if len(matches) > 1:
        raise ValueError(f"Duplicate peer name in registry: {peer_name}")
    peer = matches[0]
    if not isinstance(peer, dict):
        raise ValueError(f"Invalid peer entry for {peer_name}")
    return peer


def write_text_file(path: Path, text: str, mode: int) -> None:
    path.write_text(text + "\n", encoding="utf-8")
    path.chmod(mode)


def generate_key_material(peer_dir: Path, force: bool) -> dict[str, Path]:
    private_key_path = peer_dir / "private.key"
    public_key_path = peer_dir / "public.key"
    preshared_key_path = peer_dir / "preshared.key"

    existing = [p for p in [private_key_path, public_key_path, preshared_key_path] if p.exists()]
    if existing and not force:
        raise FileExistsError(
            "Refusing to overwrite existing key material. "
            "Use --force if you really want to replace it."
        )

    private_key = run_checked(["wg", "genkey"])
    public_key = run_checked(["wg", "pubkey"], input_text=private_key + "\n")
    preshared_key = run_checked(["wg", "genpsk"])

    write_text_file(private_key_path, private_key, 0o600)
    write_text_file(public_key_path, public_key, 0o600)
    write_text_file(preshared_key_path, preshared_key, 0o600)

    return {
        "private.key": private_key_path,
        "public.key": public_key_path,
        "preshared.key": preshared_key_path,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate WireGuard key material for a peer and update registry.yaml"
    )
    parser.add_argument("peer_name", help="Peer name exactly as it appears in wireguard/registry.yaml")
    parser.add_argument(
        "--registry",
        default="wireguard/registry.yaml",
        help="Path to registry.yaml (default: wireguard/registry.yaml)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing key files for the peer",
    )
    args = parser.parse_args()

    if shutil.which("wg") is None:
        print("ERROR: 'wg' command not found in PATH", file=sys.stderr)
        return 2

    repo_root = Path.cwd()
    registry_path = repo_root / args.registry
    if not registry_path.exists():
        print(f"ERROR: Registry file not found: {registry_path}", file=sys.stderr)
        return 2

    data = load_registry(registry_path)
    peer = find_peer(data, args.peer_name)

    peer_type = str(peer.get("peer_type", ""))
    if peer_type != "human":
        print(
            f"ERROR: This tool currently supports human peers only. "
            f"{args.peer_name} has peer_type={peer_type!r}",
            file=sys.stderr,
        )
        return 2

    key_ref = peer.get("key_ref")
    if not key_ref:
        print(f"ERROR: Peer {args.peer_name} has no key_ref", file=sys.stderr)
        return 2

    peer_dir = repo_root / "wireguard" / str(key_ref)
    peer_dir.mkdir(parents=True, exist_ok=True)
    peer_dir.chmod(0o700)

    created = generate_key_material(peer_dir, force=args.force)

    peer["key_status"] = "existing"
    peer["enrollment_status"] = "complete"

    notes = peer.get("notes")
    if notes is None:
        notes = []
        peer["notes"] = notes
    if isinstance(notes, list):
        note = "Key material generated by enroll_peer.py"
        if note not in notes:
            notes.append(note)

    save_registry(registry_path, data)

    print(f"Updated registry: {registry_path}")
    print(f"Peer: {args.peer_name}")
    print(f"Key directory: {peer_dir}")
    print("Generated:")
    for name, path in created.items():
        print(f"  - {name}: {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
