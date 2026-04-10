#!/bin/bash
set -e

python3 tools/generate_dnsmasq.py \
  --registry docs/reference/network-registry.yaml \
  --site reid \
  --domain reid.home.arpa \
  --interfaces eth0,wg0 \
  --install-root /etc/dnsmasq.d/generated \
  --outdir generated/dnsmasq/reid

python3 tools/generate_dnsmasq.py \
  --registry docs/reference/network-registry.yaml \
  --site farm \
  --domain farm.home.arpa \
  --interfaces eth0,wg0 \
  --install-root /etc/dnsmasq.d/generated \
  --outdir generated/dnsmasq/farm
