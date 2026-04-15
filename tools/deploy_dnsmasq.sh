#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <reid|farm>" >&2
  exit 2
fi

SITE="$1"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

GEN_ROOT="generated/dnsmasq"
SITE_DIR="${GEN_ROOT}/${SITE}"

TARGET_ROOT="/etc/dnsmasq.d"
TARGET_GEN="${TARGET_ROOT}/generated"
BACKUP_BASE="${TARGET_ROOT}/backup"
STAMP="$(date +%Y%m%d-%H%M%S)"

case "$SITE" in
  reid)
    HOST_FQDN="mudpi.reid.home.arpa"
    PTR_IP="10.1.1.3"
    STALE_SITE="farm"
    ;;
  farm)
    HOST_FQDN="shedpi.farm.home.arpa"
    PTR_IP="192.168.0.210"
    STALE_SITE="reid"
    ;;
  *)
    echo "Unsupported site: $SITE" >&2
    exit 2
    ;;
esac

echo "==> Building and validating generated configs"
make preflight-dnsmasq

echo "==> Sanity checks"
test -f "${SITE_DIR}/zone.conf"
test -f "${SITE_DIR}/dhcp.conf"

echo "==> Creating backup"
sudo mkdir -p "$BACKUP_BASE"
if [[ -d "$TARGET_ROOT" ]]; then
  sudo mkdir -p "$BACKUP_BASE/$STAMP"
  [[ -f "$TARGET_ROOT/${SITE}.conf" ]] && sudo cp -a "$TARGET_ROOT/${SITE}.conf" "$BACKUP_BASE/$STAMP/" || true
  [[ -f "$TARGET_ROOT/dhcp.conf" ]] && sudo cp -a "$TARGET_ROOT/dhcp.conf" "$BACKUP_BASE/$STAMP/" || true
  [[ -d "$TARGET_GEN/$SITE" ]] && sudo cp -a "$TARGET_GEN/$SITE" "$BACKUP_BASE/$STAMP/" || true
fi

echo "==> Preparing target directories"
sudo mkdir -p "$TARGET_GEN/$SITE"

echo "==> Deploying site DNS tree"
sudo rsync -a --delete "${SITE_DIR}/" "$TARGET_GEN/$SITE/"

echo "==> Installing active DHCP config at top level"
sudo cp "${SITE_DIR}/dhcp.conf" "$TARGET_ROOT/dhcp.conf"

echo "==> Writing top-level site loader"
sudo tee "$TARGET_ROOT/${SITE}.conf" >/dev/null <<EOF
# Generated zone loader for ${SITE} site
conf-file=/etc/dnsmasq.d/generated/${SITE}/zone.conf
EOF

echo "==> Removing stale top-level site loader"
sudo rm -f "$TARGET_ROOT/${STALE_SITE}.conf"

echo "==> Testing dnsmasq config"
sudo dnsmasq --test

echo "==> Restarting dnsmasq"
sudo systemctl restart dnsmasq

echo "==> Service status"
sudo systemctl --no-pager --full status dnsmasq || true

echo "==> Smoke tests"
dig @127.0.0.1 "${HOST_FQDN}" +short
dig @127.0.0.1 -x "${PTR_IP}" +short
dig @127.0.0.1 google.com +short | head

echo "==> Deployment complete"
