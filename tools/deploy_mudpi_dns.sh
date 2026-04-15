#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

GEN_ROOT="generated/dnsmasq"
TARGET_ROOT="/etc/dnsmasq.d"
TARGET_GEN="${TARGET_ROOT}/generated"
BACKUP_BASE="${TARGET_ROOT}/backup"
STAMP="$(date +%Y%m%d-%H%M%S)"

echo "==> Building and validating generated configs"
make preflight-dnsmasq

echo "==> Sanity checks"
test -f "${GEN_ROOT}/reid/zone.conf"
test -f "${GEN_ROOT}/reid/dhcp.conf"
test -f "${GEN_ROOT}/farm/zone.conf"

echo "==> Creating backup"
sudo mkdir -p "$BACKUP_BASE/$STAMP"
[[ -f "$TARGET_ROOT/reid.conf" ]] && sudo cp -a "$TARGET_ROOT/reid.conf" "$BACKUP_BASE/$STAMP/" || true
[[ -f "$TARGET_ROOT/farm.conf" ]] && sudo cp -a "$TARGET_ROOT/farm.conf" "$BACKUP_BASE/$STAMP/" || true
[[ -f "$TARGET_ROOT/dhcp.conf" ]] && sudo cp -a "$TARGET_ROOT/dhcp.conf" "$BACKUP_BASE/$STAMP/" || true
[[ -d "$TARGET_GEN/reid" ]] && sudo cp -a "$TARGET_GEN/reid" "$BACKUP_BASE/$STAMP/" || true
[[ -d "$TARGET_GEN/farm" ]] && sudo cp -a "$TARGET_GEN/farm" "$BACKUP_BASE/$STAMP/" || true

echo "==> Preparing target directories"
sudo mkdir -p "$TARGET_GEN/reid" "$TARGET_GEN/farm"

echo "==> Deploying generated site trees"
sudo rsync -a --delete "${GEN_ROOT}/reid/" "$TARGET_GEN/reid/"
sudo rsync -a --delete "${GEN_ROOT}/farm/" "$TARGET_GEN/farm/"

echo "==> Installing active DHCP config for Reid LAN"
sudo cp "${GEN_ROOT}/reid/dhcp.conf" "$TARGET_ROOT/dhcp.conf"

echo "==> Writing top-level zone loaders"
sudo tee "$TARGET_ROOT/reid.conf" >/dev/null <<'EOF'
# Generated zone loader for reid site
conf-file=/etc/dnsmasq.d/generated/reid/zone.conf
EOF

sudo tee "$TARGET_ROOT/farm.conf" >/dev/null <<'EOF'
# Generated zone loader for farm site
conf-file=/etc/dnsmasq.d/generated/farm/zone.conf
EOF

echo "==> Testing dnsmasq config"
sudo dnsmasq --test

echo "==> Restarting dnsmasq"
sudo systemctl restart dnsmasq

echo "==> Smoke tests"
dig @127.0.0.1 mudpi.reid.home.arpa +short
dig @127.0.0.1 shedpi.farm.home.arpa +short
dig @127.0.0.1 router.farm.home.arpa +short
