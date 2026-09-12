#!/usr/bin/env bash
set -euo pipefail

UUID="zorin-shot@local"
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
EXT_SRC="$HERE/extension/$UUID"
EXT_DST="$HOME/.local/share/gnome-shell/extensions/$UUID"
APP_DST="$HOME/.local/lib/zorin-shot"
DESKTOP_DST="$HOME/.local/share/applications"
ICON_DST="$HOME/.local/share/icons/hicolor/scalable/apps"
ACTION_ICON_DST="$HOME/.local/share/icons/hicolor/scalable/actions"
AUTOSTART_DST="$HOME/.config/autostart"
SCHEMA="org.gnome.shell.extensions.zorin-shot"
UPDATE_MODE=false
SHOW_POPUP=true

for arg in "$@"; do
  case "$arg" in
    --update) UPDATE_MODE=true ;;
    --no-popup) SHOW_POPUP=false ;;
    *) printf 'Nieznana opcja instalatora: %s\n' "$arg" >&2; exit 2 ;;
  esac
done

# A downloaded newer release can be installed by double-clicking/running
# install.sh directly. Detect an existing installation and automatically use
# update semantics so user preferences are not reset.
if [[ "$UPDATE_MODE" == false && ( -d "$EXT_DST" || -d "$APP_DST" ) ]]; then
  UPDATE_MODE=true
fi

printf '\nZorin Shot — instalacja dla Zorin OS 18 / GNOME Shell 46\n\n'

if command -v gnome-shell >/dev/null 2>&1; then
  ver="$(gnome-shell --version 2>/dev/null || true)"
  printf 'Wykryto: %s\n' "$ver"
  if [[ "$ver" != *" 46."* && "$ver" != *" 46" ]]; then
    printf '\nUWAGA: ta wersja jest przygotowana pod GNOME Shell 46.\n'
    printf 'Twój wynik nie wygląda na GNOME 46. Przerywam, żeby nie ryzykować powłoki.\n'
    exit 2
  fi
fi

for cmd in python3 gnome-extensions gsettings; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    printf 'Brak wymaganego polecenia: %s\n' "$cmd" >&2
    exit 2
  fi
done

if ! python3 - <<'PY' >/dev/null 2>&1
import gi
gi.require_version('Gtk','4.0')
from gi.repository import Gtk
import cairo
PY
then
  cat >&2 <<'MSG'
Brakuje bibliotek Zorin Shot.
Zainstaluj je poleceniem:

  sudo apt install python3-gi python3-cairo gir1.2-gtk-4.0

Potem uruchom instalator ponownie.
MSG
  exit 2
fi

mkdir -p "$(dirname "$EXT_DST")" "$APP_DST" "$DESKTOP_DST" "$ICON_DST" "$ACTION_ICON_DST" "$AUTOSTART_DST"

# Keep user GSettings values during updates. Replacing the extension directory
# does not remove them because they live in dconf, not inside this directory.
rm -rf "$EXT_DST"
cp -a "$EXT_SRC" "$EXT_DST"

if command -v glib-compile-schemas >/dev/null 2>&1; then
  glib-compile-schemas "$EXT_DST/schemas"
else
  printf 'Brak glib-compile-schemas. Zainstaluj libglib2.0-bin.\n' >&2
  exit 2
fi

install -m 0755 "$HERE/app/zorin-shot-editor.py" "$APP_DST/zorin-shot-editor.py"
install -m 0755 "$HERE/app/zorin-shot-control.py" "$APP_DST/zorin-shot-control.py"
install -m 0644 "$HERE/app/i18n.py" "$APP_DST/i18n.py"
install -m 0755 "$HERE/app/zorin-shot-first-login.sh" "$APP_DST/zorin-shot-first-login.sh"
install -m 0644 "$HERE/app/build-info.json" "$APP_DST/build-info.json"
install -m 0644 "$HERE/VERSION" "$APP_DST/VERSION"
install -m 0644 "$HERE/CHANGELOG.md" "$APP_DST/CHANGELOG.md"
# Desktop IDs must match Gtk.Application IDs so GNOME/Wayland associates
# application windows with the Zorin Shot icon instead of a generic icon.
rm -f \
  "$DESKTOP_DST/io.local.ZorinShot.desktop" \
  "$DESKTOP_DST/io.local.ZorinShot.Control.desktop" \
  "$DESKTOP_DST/io.local.ZorinShot.Editor.desktop" \
  "$DESKTOP_DST/zorin-shot-settings.desktop"
sed "s|__ZORIN_SHOT_CONTROL__|$APP_DST/zorin-shot-control.py|g" "$HERE/app/io.local.ZorinShot.Control.desktop" > "$DESKTOP_DST/io.local.ZorinShot.Control.desktop"
chmod 0644 "$DESKTOP_DST/io.local.ZorinShot.Control.desktop"
sed "s|__ZORIN_SHOT_EDITOR__|$APP_DST/zorin-shot-editor.py|g" "$HERE/app/io.local.ZorinShot.Editor.desktop" > "$DESKTOP_DST/io.local.ZorinShot.Editor.desktop"
chmod 0644 "$DESKTOP_DST/io.local.ZorinShot.Editor.desktop"
install -m 0644 "$HERE/icons/zorin-shot.svg" "$ICON_DST/zorin-shot.svg"
install -m 0644 "$HERE/icons/zorin-shot-symbolic.svg" "$ICON_DST/zorin-shot-symbolic.svg"
# GTK4 uses the application-id as the default window icon. Install aliases
# matching both application IDs so GNOME/Zorin does not show a generic puzzle.
install -m 0644 "$HERE/icons/zorin-shot.svg" "$ICON_DST/io.local.ZorinShot.Control.svg"
install -m 0644 "$HERE/icons/zorin-shot.svg" "$ICON_DST/io.local.ZorinShot.Editor.svg"
install -m 0644 "$HERE/icons/zorin-shot-symbolic.svg" "$EXT_DST/zorin-shot-symbolic.svg"
for icon in "$HERE"/icons/tools/*-symbolic.svg; do
  install -m 0644 "$icon" "$ACTION_ICON_DST/$(basename "$icon")"
done

# Detect the current desktop language once. LANGUAGE is checked first because
# GNOME may use it even when LANG/LC_* differ. Only Polish and English are
# supported; every other locale falls back to English.
DETECTED_LANG="$(python3 - <<'PYLANG'
import os
values = [
    os.environ.get('LANGUAGE', ''),
    os.environ.get('LC_ALL', ''),
    os.environ.get('LC_MESSAGES', ''),
    os.environ.get('LANG', ''),
]
for value in values:
    for part in str(value).split(':'):
        code = part.strip().lower().replace('-', '_')
        if code.startswith('pl'):
            print('pl')
            raise SystemExit
        if code.startswith('en'):
            print('en')
            raise SystemExit
print('en')
PYLANG
)"

if [[ "$UPDATE_MODE" == false ]]; then
  # Fresh-install defaults.
  gsettings --schemadir "$EXT_DST/schemas" set "$SCHEMA" show-action-button true
  gsettings --schemadir "$EXT_DST/schemas" set "$SCHEMA" replace-print-screen true
  gsettings --schemadir "$EXT_DST/schemas" set "$SCHEMA" capture-mode 'native'
  gsettings --schemadir "$EXT_DST/schemas" set "$SCHEMA" language "$DETECTED_LANG"
  gsettings --schemadir "$EXT_DST/schemas" set "$SCHEMA" language-initialized true
  gsettings --schemadir "$EXT_DST/schemas" set "$SCHEMA" auto-check-updates true
else
  # Keep user choices on updates, except for one-time migration from versions
  # that hard-coded Polish on first install. The new key does not exist in old
  # dconf data, so false means we still need to initialize from the OS locale.
  if [[ "$(gsettings --schemadir "$EXT_DST/schemas" get "$SCHEMA" language-initialized 2>/dev/null || echo false)" != "true" ]]; then
    gsettings --schemadir "$EXT_DST/schemas" set "$SCHEMA" language "$DETECTED_LANG"
    gsettings --schemadir "$EXT_DST/schemas" set "$SCHEMA" language-initialized true
  fi
  gsettings --schemadir "$EXT_DST/schemas" set "$SCHEMA" capture-mode 'native'
  gsettings --schemadir "$EXT_DST/schemas" set "$SCHEMA" show-action-button true
  gsettings --schemadir "$EXT_DST/schemas" set "$SCHEMA" replace-print-screen true
fi

# Disable the old Gradia bridge if it is still present. Keep its files intact.
if gnome-extensions info zorin-gradia-capture@local >/dev/null 2>&1; then
  gnome-extensions disable zorin-gradia-capture@local >/dev/null 2>&1 || true
fi

# Register the extension as enabled before GNOME Shell necessarily knows about
# the freshly copied directory. This makes a fresh install activate after the
# required logout/login without asking the user to type another command.
python3 - "$UUID" <<'PY'
import sys
from gi.repository import Gio
uuid = sys.argv[1]
settings = Gio.Settings.new('org.gnome.shell')
enabled = list(settings.get_strv('enabled-extensions'))
if uuid not in enabled:
    enabled.append(uuid)
    settings.set_strv('enabled-extensions', enabled)
try:
    disabled = list(settings.get_strv('disabled-extensions'))
    if uuid in disabled:
        settings.set_strv('disabled-extensions', [x for x in disabled if x != uuid])
except Exception:
    pass
PY

gnome-extensions enable "$UUID" >/dev/null 2>&1 || true

if [[ "$UPDATE_MODE" == false ]]; then
  cat > "$AUTOSTART_DST/zorin-shot-first-login.desktop" <<EOF2
[Desktop Entry]
Type=Application
Name=Zorin Shot — first login setup
Exec=$APP_DST/zorin-shot-first-login.sh
Terminal=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
EOF2
fi

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$DESKTOP_DST" >/dev/null 2>&1 || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true

if [[ "$DETECTED_LANG" == "en" ]]; then
  if [[ "$UPDATE_MODE" == true ]]; then
    MESSAGE='The Zorin Shot update has been installed.\n\nLog out and sign back in so GNOME Shell can load the new extension version.'
  else
    MESSAGE='Zorin Shot has been installed.\n\nLog out of Zorin OS and sign back in.\n\nAfter signing in again:\n• Zorin Shot will enable automatically,\n• the new icon will appear next to the original screenshot button,\n• Print Screen will launch Zorin Shot,\n• Super + Print Screen will remain available for the original screenshot / screen recording tool,\n• the Zorin Shot application will open automatically the first time.\n\nYou do not need to enter any additional commands.'
  fi
  POPUP_TITLE='Zorin Shot — installation complete'
  NOTIFY_TEXT='Log out and sign back in.'
else
  if [[ "$UPDATE_MODE" == true ]]; then
    MESSAGE='Aktualizacja Zorin Shot została zainstalowana.\n\nWyloguj się i zaloguj ponownie, aby GNOME Shell załadował nową wersję rozszerzenia.'
  else
    MESSAGE='Zorin Shot został zainstalowany.\n\nWyloguj się z Zorina i zaloguj ponownie.\n\nPo ponownym logowaniu:\n• Zorin Shot włączy się automatycznie,\n• nowa ikona pojawi się obok oryginalnego aparatu,\n• Print Screen będzie uruchamiał Zorin Shot,\n• Super + Print Screen zostanie dla oryginalnego screenshotu / nagrywania,\n• aplikacja Zorin Shot otworzy się automatycznie pierwszy raz.\n\nNie musisz wpisywać żadnych dodatkowych komend.'
  fi
  POPUP_TITLE='Zorin Shot — instalacja zakończona'
  NOTIFY_TEXT='Wyloguj się i zaloguj ponownie.'
fi

if [[ "$SHOW_POPUP" == true ]]; then
  if command -v zenity >/dev/null 2>&1 && [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
    zenity --info --title="$POPUP_TITLE" --width=540 --text="$MESSAGE" || true
  elif command -v notify-send >/dev/null 2>&1 && [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
    notify-send -u normal -t 15000 "$POPUP_TITLE" "$NOTIFY_TEXT" || true
  fi
fi

printf '\n%b\n\n' "$MESSAGE"
