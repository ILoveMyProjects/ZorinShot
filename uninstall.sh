#!/usr/bin/env bash
set -euo pipefail
UUID="zorin-shot@local"
EXT_DST="$HOME/.local/share/gnome-shell/extensions/$UUID"
APP_DST="$HOME/.local/lib/zorin-shot"
SCHEMA="org.gnome.shell.extensions.zorin-shot"

gnome-extensions disable "$UUID" >/dev/null 2>&1 || true
sleep 1

if [[ -d "$EXT_DST/schemas" ]] && command -v gsettings >/dev/null 2>&1; then
  valid="$(gsettings --schemadir "$EXT_DST/schemas" get "$SCHEMA" saved-native-valid 2>/dev/null || echo false)"
  if [[ "$valid" == "true" ]]; then
    saved="$(gsettings --schemadir "$EXT_DST/schemas" get "$SCHEMA" saved-native-shortcut 2>/dev/null || true)"
    if [[ -n "$saved" ]]; then
      gsettings set org.gnome.shell.keybindings show-screenshot-ui "$saved" || true
    fi
  fi
fi

if command -v python3 >/dev/null 2>&1; then
python3 - "$UUID" <<'PY' || true
import sys
from gi.repository import Gio
uuid = sys.argv[1]
settings = Gio.Settings.new('org.gnome.shell')
enabled = list(settings.get_strv('enabled-extensions'))
if uuid in enabled:
    settings.set_strv('enabled-extensions', [x for x in enabled if x != uuid])
PY
fi

rm -rf "$EXT_DST" "$APP_DST"
rm -f "$HOME/.local/share/applications/io.local.ZorinShot.desktop"
rm -f "$HOME/.local/share/applications/zorin-shot-settings.desktop"
rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/zorin-shot.svg"
rm -f "$HOME/.config/autostart/zorin-shot-first-login.desktop"
printf 'Zorin Shot usunięty. Wyloguj się i zaloguj ponownie, jeśli ikona nadal jest widoczna.\n'
