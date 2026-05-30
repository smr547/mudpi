#!/usr/bin/env python3

import socket
import subprocess
from dataclasses import dataclass
from typing import Optional


MONGO_CONTAINER = "unifi-db"
MONGO_DB = "unifi"


@dataclass
class Client:
    ip: str
    mac: str
    hostname: str
    uplink: str
    radio: str
    canonical: str


def reverse_dns(ip: str) -> str:
    try:
        name, _, _ = socket.gethostbyaddr(ip)
        return name.rstrip(".")
    except Exception:
        return ""


def mongo_query() -> str:
    js = r'''
db.user.find(
  { last_ip: { $exists: true } },
  {
    _id: 0,
    last_ip: 1,
    mac: 1,
    hostname: 1,
    last_uplink_name: 1,
    last_radio: 1
  }
).sort({last_ip:1}).forEach(doc => print(JSON.stringify(doc)))
'''
    result = subprocess.run(
        [
            "docker", "exec", MONGO_CONTAINER,
            "mongosh", MONGO_DB, "--quiet", "--eval", js
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout

def parse_mongo_output(text: str) -> list[Client]:
    import json

    clients = []

    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue

        try:
            doc = json.loads(line)
        except json.JSONDecodeError:
            continue

        ip = doc.get("last_ip", "")
        if not ip:
            continue

        clients.append(Client(
            ip=ip,
            mac=doc.get("mac", ""),
            hostname=doc.get("hostname", ""),
            uplink=doc.get("last_uplink_name", ""),
            radio=doc.get("last_radio", ""),
            canonical=reverse_dns(ip),
        ))

    return clients

def radio_label(radio: str) -> str:
    return {
        "ng": "2.4GHz",
        "na": "5GHz",
    }.get(radio, radio)


def main() -> None:
    clients = parse_mongo_output(mongo_query())

    print(f"{'IP':<15} {'Canonical DNS':<34} {'Device says':<28} {'AP':<26} {'Radio':<7} {'MAC'}")
    print("-" * 130)

    for c in sorted(clients, key=lambda x: tuple(map(int, x.ip.split(".")))):
        print(
            f"{c.ip:<15} "
            f"{c.canonical:<34} "
            f"{c.hostname:<28} "
            f"{c.uplink:<26} "
            f"{radio_label(c.radio):<7} "
            f"{c.mac}"
        )


if __name__ == "__main__":
    main()
