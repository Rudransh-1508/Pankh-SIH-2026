#!/usr/bin/env bash
# Set up Pankh on a fresh Ubuntu server (Oracle Cloud Always Free Ampere, or any VM).
# Run from the repository's deploy/ folder:  bash setup.sh
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v docker >/dev/null; then
  echo "Installing Docker"
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER"
fi

# Oracle's Ubuntu images block everything but SSH in iptables, as well as in the cloud's
# security list. Open HTTP and HTTPS here; the security list is opened in the console.
if sudo iptables -C INPUT -p tcp --dport 80 -j ACCEPT 2>/dev/null; then :; else
  sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
  sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
  sudo apt-get install -y iptables-persistent >/dev/null 2>&1 || true
  sudo netfilter-persistent save || true
fi

secret() { openssl rand -base64 48 | tr -d '/+=\n' | cut -c1-"${1:-48}"; }

if [ ! -f .env ]; then
  ip=$(curl -fsS https://api.ipify.org)
  dashed=${ip//./-}
  sed \
    -e "s|^API_DOMAIN=.*|API_DOMAIN=api.$dashed.sslip.io|" \
    -e "s|^SIM_DOMAIN=.*|SIM_DOMAIN=sim.$dashed.sslip.io|" \
    -e "s|^DASHBOARD_DOMAIN=.*|DASHBOARD_DOMAIN=dashboard.$dashed.sslip.io|" \
    -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(secret 32)|" \
    -e "s|^S3_SECRET=.*|S3_SECRET=$(secret 32)|" \
    -e "s|^PANKH_SECRET_KEY=.*|PANKH_SECRET_KEY=$(secret 48)|" \
    -e "s|^PANKH_DOCUMENT_MASTER_KEY=.*|PANKH_DOCUMENT_MASTER_KEY=$(openssl rand -base64 32)|" \
    -e "s|^PANKH_PHONE_WEBHOOK_TOKEN=.*|PANKH_PHONE_WEBHOOK_TOKEN=$(secret 32)|" \
    -e "s|^PANKH_VOICE_SERVICE_TOKEN=.*|PANKH_VOICE_SERVICE_TOKEN=$(secret 32)|" \
    env.example > .env
  chmod 600 .env
  echo "Wrote deploy/.env for $ip"
fi

set -a; . ./.env; set +a
cat > s3.json <<JSON
{"identities": [{"name": "pankh", "credentials": [{"accessKey": "pankh", "secretKey": "$S3_SECRET"}],
  "actions": ["Admin", "Read", "Write", "List", "Tagging"]}]}
JSON
chmod 600 s3.json

profiles=()
[ -n "${PANKH_LIVEKIT_URL:-}" ] && [ -n "${PANKH_SARVAM_API_KEY:-}" ] && profiles=(--profile voice)
sudo docker compose "${profiles[@]}" up -d --build

echo
echo "Pankh is starting. In a minute or two:"
echo "  API:        https://$API_DOMAIN/health"
echo "  Dashboard:  https://$DASHBOARD_DOMAIN"
echo "  Simulators: https://$SIM_DOMAIN/health"
echo "Build the app with: flutter build apk --release --dart-define=PANKH_API_URL=https://$API_DOMAIN"
