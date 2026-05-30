#!/usr/bin/env python3

import json
import socket
import subprocess

LAN_PREFIX = "10.1.1."
LAN_CIDR = "10.1.1.0/24"
INTERFACE = "eth0"   # change if needed


def run(cmd):
    return subprocess.run(cmd, text=True, capture_output=True)


def reverse_dns(ip):
    try:
        name, _, _ = socket.gethostbyaddr(ip)
        return name.rstrip(".")
    except Exception:
        return ""


def ping_ok(ip):
    result = run(["ping", "-c", "1", "-W", "1", ip])
    return result.returncode == 0


def radio_name(r):
    return {
        "na": "5GHz",
        "ng": "2.4GHz",
        "6e": "6GHz",
    }.get(r, r or "")


def merge_by_ip(base, extra):
    for ip, dev in extra.items():
        if ip not in base:
            base[ip] = dev
        else:
            base[ip].update({k: v for k, v in dev.items() if v})
            base[ip].setdefault("seen_by", set()).update(dev.get("seen_by", set()))


def get_local_addresses():
    devices = {}

    result = run(["ip", "-j", "addr", "show"])
    interfaces = json.loads(result.stdout)

    for iface in interfaces:
        ifname = iface.get("ifname", "")
        mac = iface.get("address", "").lower()

        if not mac or mac == "00:00:00:00:00:00":
            continue

        for addr in iface.get("addr_info", []):
            if addr.get("family") != "inet":
                continue

            ip = addr.get("local", "")
            if not ip.startswith(LAN_PREFIX):
                continue

            devices[ip] = {
                "ip": ip,
                "mac": mac,
                "vendor": "local host",
                "interface": ifname,
                "seen_by": {"local"},
            }

    return devices


def get_arp_scan():
    devices = {}

    result = run(["sudo", "arp-scan", "--interface", INTERFACE, LAN_CIDR])

    for line in result.stdout.splitlines():
        parts = line.split()

        if len(parts) >= 2 and parts[0].startswith(LAN_PREFIX):
            ip = parts[0]
            mac = parts[1].lower()
            vendor = " ".join(parts[2:]) if len(parts) > 2 else ""

            devices[ip] = {
                "ip": ip,
                "mac": mac,
                "vendor": vendor,
                "seen_by": {"arp-scan"},
            }

    return devices


def get_ip_neigh():
    devices = {}

    result = run(["ip", "neigh"])

    for line in result.stdout.splitlines():
        parts = line.split()
        if not parts:
            continue

        ip = parts[0]
        if not ip.startswith(LAN_PREFIX):
            continue

        mac = ""
        if "lladdr" in parts:
            i = parts.index("lladdr")
            if i + 1 < len(parts):
                mac = parts[i + 1].lower()

        state = parts[-1]

        devices[ip] = {
            "ip": ip,
            "mac": mac,
            "neigh_state": state,
            "seen_by": {"ip-neigh"},
        }

    return devices


def get_unifi_clients():
    by_mac = {}

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
).forEach(doc => print(JSON.stringify(doc)))
'''

    result = run([
        "docker", "exec", "unifi-db",
        "mongosh", "unifi", "--quiet", "--eval", js
    ])

    for line in result.stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue

        doc = json.loads(line)
        mac = doc.get("mac", "").lower()
        if not mac:
            continue

        by_mac[mac] = {
            "unifi_ip": doc.get("last_ip", ""),
            "device_says": doc.get("hostname", ""),
            "ap": doc.get("last_uplink_name", ""),
            "radio": radio_name(doc.get("last_radio", "")),
        }

    return by_mac


def ip_sort_key(ip):
    return tuple(int(part) for part in ip.split("."))


def main():
    devices = {}

    merge_by_ip(devices, get_local_addresses())
    merge_by_ip(devices, get_arp_scan())
    merge_by_ip(devices, get_ip_neigh())

    unifi = get_unifi_clients()

    for ip, dev in devices.items():
        mac = dev.get("mac", "").lower()

        dev["dns"] = reverse_dns(ip)
        dev["ping"] = "yes" if ping_ok(ip) else "no"

        if mac in unifi:
            dev.update(unifi[mac])
            dev.setdefault("seen_by", set()).add("unifi")

    print(
        f"{'IP':<15} {'DNS':<34} {'Ping':<4} {'Device says':<24} "
        f"{'Connection':<26} {'Radio':<6} {'MAC':<18} {'Vendor / Seen'}"
    )
    print("-" * 155)

    for ip in sorted(devices, key=ip_sort_key):
        d = devices[ip]
        seen = ",".join(sorted(d.get("seen_by", [])))

        connection = d.get("ap", "")
        if not connection:
            if "local" in d.get("seen_by", set()):
                connection = f"local/{d.get('interface', '')}"
            else:
                connection = "ethernet/unknown"

        print(
            f"{ip:<15} "
            f"{d.get('dns',''):<34} "
            f"{d.get('ping',''):<4} "
            f"{d.get('device_says',''):<24} "
            f"{connection:<26} "
            f"{d.get('radio',''):<6} "
            f"{d.get('mac',''):<18} "
            f"{d.get('vendor','') or seen}"
        )


if __name__ == "__main__":
    main()
