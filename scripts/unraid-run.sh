#!/bin/bash
# Script User Scripts unRAID — lance SonicSort sur bibliothèque musicale.
# À copier dans plugin "User Scripts" + planifier (cron).

APP_DIR="/mnt/user/appdata/sonic-sort"
MUSIC_DIR="/mnt/user/Music"
LOG_FILE="/var/log/sonic-sort.log"

# Options pipeline
EXTRA_ARGS="--plex-scan --plex-section 1"
# Pour dry-run: EXTRA_ARGS="--dry-run"

cd "$APP_DIR" || exit 1

echo "=== $(date) — SonicSort start ===" >> "$LOG_FILE"
python3 -m src run "$MUSIC_DIR" $EXTRA_ARGS >> "$LOG_FILE" 2>&1
echo "=== $(date) — SonicSort end ===" >> "$LOG_FILE"
