#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

TARGET_BASE="/etc/dnsmasq.d/generated"
BACKUP_BASE="/etc/dnsmasq.d/backup"
STAMP="$(date +%Y%m%d-%H%M%S)"

echo "==> Building generated configs"
./tools/build_mudpi_dns.sh

echo "==> Sanity checks"
test -f generated/dnsmasq/reid/zone.conf
test -f generated/dnsmasq/farm/zone.conf
test -f generated/dhcp/reid/dhcp.conf

echo "==> Creating backup"
sudo mkdir -p "$BACKUP_BASE"
if [ -d "$TARGET_BASE" ]; then
  sudo cp -a "$TARGET_BASE" "$BACKUP_BASE/generated-$STAMP"
fi

echo "==> Preparing target directories"
sudo mkdir -p "$TARGET_BASE/reid" "$TARGET_BASE/farm"

echo "==> Deploying site DNS trees"
sudo rsync -a --delete generated/dnsmasq/reid/ "$TARGET_BASE/reid/"
sudo rsync -a --delete generated/dnsmasq/farm/ "$TARGET_BASE/farm/"

echo "==> Deploying DHCP config"
sudo cp generated/dhcp/reid/dhcp.conf "$TARGET_BASE/dhcp.conf"

echo "==> Writing loader files"
sudo tee "$TARGET_BASE/reid.conf" >/dev/null <<'EOF'
# Generated zone loader for Reid site
conf-file=/etc/dnsmasq.d/generated/reid/zone.conf
EOF

sudo tee "$TARGET_BASE/farm.conf" >/dev/null <<'EOF'
# Generated zone loader for Farm site
conf-file=/etc/dnsmasq.d/generated/farm/zone.conf
EOF

echo "==> Removing obsolete flat DNS snippets"
sudo rm -f \
  "$TARGET_BASE/hosts.conf" \
  "$TARGET_BASE/aliases.conf" \
  "$TARGET_BASE/reverse.conf"

echo "==> Restarting dnsmasq"
sudo systemctl restart dnsmasq

echo "==> Service status"
sudo systemctl --no-pager --full status dnsmasq

echo "==> Smoke tests"
dig @127.0.0.1 mudpi.reid.home.arpa +short
dig @127.0.0.1 shedpi.farm.home.arpa +short
dig @127.0.0.1 router.farm.home.arpa +short
dig @127.0.0.1 -x 10.1.1.3 +short
dig @127.0.0.1 -x 192.168.0.210 +short

echo "==> Deployment complete"
