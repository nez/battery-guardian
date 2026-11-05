#!/usr/bin/python3
"""Root-owned guard for forced suspension at critically low battery."""
from pathlib import Path
import subprocess
import sys


def check_battery(battery):
    capacity = int((battery / "capacity").read_text().strip())
    if not 0 <= capacity <= 100:
        raise ValueError(f"Invalid battery capacity: {capacity}")
    if capacity <= 2 and (battery / "status").read_text().strip() == "Discharging":
        subprocess.run([
            "/usr/bin/systemctl", "--no-ask-password", "--check-inhibitors=no", "suspend",
        ], check=True)


if __name__ == "__main__":
    batteries = sorted(Path("/sys/class/power_supply").glob("BAT*"))
    if len(batteries) != 1:
        sys.exit("Expected one BAT* battery in /sys/class/power_supply")
    check_battery(batteries[0])
