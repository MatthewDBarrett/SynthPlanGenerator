#!/usr/bin/env bash
# Installs/updates the Family Tree app as a systemd service on a Raspberry Pi
# (or any Debian-based Linux). Safe to re-run after `git pull` to upgrade.
#
# Run this as your normal user (NOT with sudo) from anywhere -- it figures
# out the repo location itself and calls sudo only for the steps that need it:
#
#   ./deploy/install.sh
#
# Override defaults with environment variables, e.g.:
#   PORT=9000 WORKERS=1 ./deploy/install.sh

set -euo pipefail

if [ "$(id -u)" -eq 0 ]; then
  echo "Please run this script as your normal user, not as root/sudo." >&2
  echo "It will call sudo itself for the specific steps that need it." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
APP_USER="$(id -un)"
APP_GROUP="$(id -gn)"
PORT="${PORT:-8080}"
BIND_HOST="${BIND_HOST:-0.0.0.0}"
WORKERS="${WORKERS:-2}"
SERVICE_NAME="family-tree"

echo "==> Installing Family Tree from $APP_DIR"
echo "    Service will run as $APP_USER:$APP_GROUP on $BIND_HOST:$PORT with $WORKERS worker(s)"

echo "==> Installing system packages (python3-venv, python3-pip)"
sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip

if [ ! -d "$APP_DIR/.venv" ]; then
  echo "==> Creating virtual environment"
  python3 -m venv "$APP_DIR/.venv"
fi

echo "==> Installing Python dependencies (this can take a few minutes on a Pi)"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install --extra-index-url https://www.piwheels.org/simple -r "$APP_DIR/requirements.txt"

echo "==> Writing systemd service"
sed \
  -e "s#__APP_USER__#${APP_USER}#g" \
  -e "s#__APP_GROUP__#${APP_GROUP}#g" \
  -e "s#__APP_DIR__#${APP_DIR}#g" \
  -e "s#__PORT__#${PORT}#g" \
  -e "s#__BIND_HOST__#${BIND_HOST}#g" \
  -e "s#__WORKERS__#${WORKERS}#g" \
  "$SCRIPT_DIR/family-tree.service.template" | sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" > /dev/null

echo "==> Enabling and starting the service"
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

sleep 2
if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
  IP="$(hostname -I | awk '{print $1}')"
  echo ""
  echo "==> Family Tree is running."
  echo "    Visit: http://${IP}:${PORT}"
  echo "    Logs:  sudo journalctl -u ${SERVICE_NAME} -f"
else
  echo ""
  echo "==> Service failed to start. Check logs with:"
  echo "    sudo journalctl -u ${SERVICE_NAME} -e"
  exit 1
fi
