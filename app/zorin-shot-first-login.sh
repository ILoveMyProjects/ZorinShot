#!/usr/bin/env bash
set -u

UUID="zorin-shot@local"
AUTOSTART="$HOME/.config/autostart/zorin-shot-first-login.desktop"
CONTROL="$HOME/.local/lib/zorin-shot/zorin-shot-control.py"

sleep 3

for _ in $(seq 1 20); do
    if gnome-extensions info "$UUID" >/dev/null 2>&1; then
        gnome-extensions enable "$UUID" >/dev/null 2>&1 || true
        break
    fi
    sleep 1
done

# First login after a fresh install: open the normal Zorin Shot application.
if [[ -x "$CONTROL" ]]; then
    sleep 1
    "$CONTROL" >/dev/null 2>&1 &
fi

rm -f "$AUTOSTART"
exit 0
