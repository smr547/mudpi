#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

echo "==> Building DNS zone: reid"
python3 tools/generate_dnsmasq.py \
  --registry docs/reference/network-registry.yaml \
  --site reid \
  --domain reid.home.arpa \
  --interfaces eth0 \
  --install-root /etc/dnsmasq.d/generated \
  --outdir generated/dnsmasq/reid

echo "==> Building DNS zone: farm"
python3 tools/generate_dnsmasq.py \
  --registry docs/reference/network-registry.yaml \
  --site farm \
  --domain farm.home.arpa \
  --interfaces eth0 \
  --install-root /etc/dnsmasq.d/generated \
  --outdir generated/dnsmasq/farm

echo "==> Building DHCP config: reid"
python3 tools/generate_dhcp_dnsmasq.py \
  --registry docs/reference/network-registry.yaml \
  --site reid \
  --outdir generated/dhcp/reid \
  --interface eth0 \
  --cidr 10.1.1.0/24 \
  --range-start 10.1.1.100 \
  --range-end 10.1.1.199 \
  --router 10.1.1.1 \
  --dns-server 10.1.1.3 \
  --domain reid.home.arpa

echo "==> Build complete"
