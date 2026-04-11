#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <reid|farm>" >&2
  exit 2
fi

SITE="$1"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

TARGET_BASE="/etc/dnsmasq.d/generated"
BACKUP_BASE="/etc/dnsmasq.d/backup"
STAMP="$(date +%Y%m%d-%H%M%S)"
SITE_DIR="generated/dnsmasq/${SITE}"

case "$SITE" in
  reid)
    HOST_FQDN="mudpi.reid.home.arpa"
    PTR_IP="10.1.1.3"
    ;;
  farm)
    HOST_FQDN="shedpi.farm.home.arpa"
    PTR_IP="192.168.0.210"
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
if [ -d "$TARGET_BASE" ]; then
  sudo cp -a "$TARGET_BASE" "$BACKUP_BASE/generated-$STAMP"
fi

echo "==> Preparing target directories"
sudo mkdir -p "$TARGET_BASE/$SITE"

echo "==> Deploying site DNS/DHCP tree"
sudo rsync -a --delete "${SITE_DIR}/" "$TARGET_BASE/$SITE/"

echo "==> Writing loader file"
sudo tee "$TARGET_BASE/${SITE}.conf" >/dev/null <<EOF
# Generated zone loader for ${SITE} site
conf-file=/etc/dnsmasq.d/generated/${SITE}/zone.conf
conf-file=/etc/dnsmasq.d/generated/${SITE}/dhcp.conf
EOF

echo "==> Restarting dnsmasq"
sudo dnsmasq --test
sudo systemctl restart dnsmasq

echo "==> Service status"
sudo systemctl --no-pager --full status dnsmasq || true

echo "==> Smoke tests"
dig @127.0.0.1 "${HOST_FQDN}" +short
dig @127.0.0.1 -x "${PTR_IP}" +short

echo "==> Deployment complete"
