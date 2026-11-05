#!/bin/bash
set -euo pipefail

if (( EUID == 0 )); then
    echo "Run as your desktop user, without sudo." >&2
    exit 1
fi

sudo -v
sudo systemctl disable --now battery-critical-suspend.timer
sudo systemctl stop battery-critical-suspend.service
systemctl --user disable --now battery-alarm.timer
systemctl --user stop battery-alarm.service
sudo rm -f /etc/systemd/system/battery-critical-suspend.{service,timer} /usr/local/libexec/battery-critical-suspend
rm -f "$HOME/.config/systemd/user/"battery-alarm.{service,timer} "$HOME/.local/bin/battery-alarm" "$HOME/.local/share/battery-alarm/siren.wav"
if [[ -n ${XDG_RUNTIME_DIR:-} ]]; then
    rm -f "$XDG_RUNTIME_DIR/battery-alarm-notified"
fi
sudo systemctl daemon-reload
systemctl --user daemon-reload
echo "Battery Guardian removed. Existing audio settings were left as they are."
