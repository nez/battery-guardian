#!/bin/bash
set -euo pipefail

if (( EUID == 0 )); then
    echo "Run as your desktop user, without sudo. The installer requests sudo when needed." >&2
    exit 1
fi

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
for dependency in python3 pactl paplay notify-send systemctl sudo; do
    command -v "$dependency" >/dev/null || {
        echo "Missing dependency: $dependency. See README.md for installation instructions." >&2
        exit 1
    }
done

echo "Installing: alarm at 5% (100% volume); forced suspend at 2%, ignoring inhibitors."
sudo -v

install -d "$HOME/.local/bin" "$HOME/.local/share/battery-alarm" "$HOME/.config/systemd/user"
install -m 755 src/battery-alarm "$HOME/.local/bin/battery-alarm"
python3 src/make-siren.py "$HOME/.local/share/battery-alarm/siren.wav"
install -m 644 systemd/battery-alarm.{service,timer} "$HOME/.config/systemd/user/"

sudo install -D -o root -g root -m 755 src/battery-critical-suspend.py /usr/local/libexec/battery-critical-suspend
sudo install -o root -g root -m 644 systemd/battery-critical-suspend.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
systemctl --user daemon-reload
sudo systemctl enable --now battery-critical-suspend.timer
systemctl --user enable --now battery-alarm.timer
echo "Battery Guardian is active. See README.md for status and uninstall commands."
