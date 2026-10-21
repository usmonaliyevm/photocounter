#!/bin/zsh
# Botni Mac'da launchd orqali avtomatik ishga tushadigan qilib o'rnatish.
# Ishlatish: ./deploy/mac-install.sh
set -e
cd "$(dirname "$0")/.."
PLIST=deploy/uz.telegram-bot.photo-counter.plist
LABEL=uz.telegram-bot.photo-counter

[ -d venv ] || { python3 -m venv venv && ./venv/bin/pip install -q -r requirements.txt; }
mkdir -p ~/Library/LaunchAgents ~/Library/Logs
cp "$PLIST" ~/Library/LaunchAgents/
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/$LABEL.plist
echo "O'rnatildi. Log: ~/Library/Logs/telegram-bot.log"
