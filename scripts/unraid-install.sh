#!/bin/bash
# Install one-shot SonicSort sur unRAID via NerdTools.
# Prérequis: plugin "NerdTools" (Apps) avec python3 + python-pip + git activés.
# Run: bash unraid-install.sh

set -e

APP_DIR="/mnt/user/appdata/sonic-sort"
FPCALC_VERSION="1.5.1"
FPCALC_URL="https://github.com/acoustid/chromaprint/releases/download/v${FPCALC_VERSION}/chromaprint-fpcalc-${FPCALC_VERSION}-linux-x86_64.tar.gz"
REPO_URL="https://github.com/amchiri/sonic-sort.git"

echo "[1/5] Vérif dépendances..."
command -v python3 >/dev/null || { echo "ERR: python3 absent. Active python3 dans NerdTools."; exit 1; }
command -v pip3 >/dev/null || { echo "ERR: pip3 absent. Active python-pip dans NerdTools."; exit 1; }
command -v git >/dev/null || { echo "ERR: git absent. Active git dans NerdTools."; exit 1; }

echo "[2/5] Install fpcalc..."
if ! command -v fpcalc >/dev/null; then
    cd /tmp
    wget -q "$FPCALC_URL" -O fpcalc.tar.gz
    tar xzf fpcalc.tar.gz
    cp chromaprint-fpcalc-*/fpcalc /usr/local/bin/
    chmod +x /usr/local/bin/fpcalc
    rm -rf fpcalc.tar.gz chromaprint-fpcalc-*
    echo "  fpcalc installé."
else
    echo "  fpcalc déjà présent."
fi

echo "[3/5] Clone / update repo..."
if [ ! -d "$APP_DIR" ]; then
    git clone "$REPO_URL" "$APP_DIR"
else
    cd "$APP_DIR"
    git pull
fi

echo "[4/5] Install deps Python..."
cd "$APP_DIR"
pip3 install -e . --break-system-packages 2>/dev/null || pip3 install -e .

echo "[5/5] Setup .env..."
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo ""
    echo "ACTION REQUISE: édite $APP_DIR/.env"
    echo "  - ACOUSTID_API_KEY (clé app AcoustID, ex: v8pQ6oyB)"
    echo "  - MB_CONTACT (ton email)"
    echo "  - PLEX_URL + PLEX_TOKEN (optionnel)"
else
    echo "  .env déjà présent."
fi

echo ""
echo "Install OK. Test:"
echo "  cd $APP_DIR && python3 -m src scan /mnt/user/Music"
