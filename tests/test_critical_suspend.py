import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import wave


spec = importlib.util.spec_from_file_location(
    "critical_suspend", Path(__file__).resolve().parents[1] / "src/battery-critical-suspend.py"
)
suspend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(suspend)


class CriticalSuspendTests(unittest.TestCase):
    def test_threshold_charging_and_invalid_capacity(self):
        with tempfile.TemporaryDirectory() as folder:
            battery = Path(folder)
            with patch.object(suspend.subprocess, "run") as run:
                for capacity, status, should_suspend in [
                    (5, "Discharging", False), (3, "Discharging", False),
                    (2, "Discharging", True), (1, "Discharging", True),
                    (0, "Discharging", True), (2, "Charging", False),
                    (1, "Full", False), (1, "Unknown", False),
                ]:
                    run.reset_mock()
                    (battery / "capacity").write_text(str(capacity))
                    (battery / "status").write_text(status)
                    suspend.check_battery(battery)
                    self.assertEqual(run.called, should_suspend, (capacity, status))
                    if should_suspend:
                        run.assert_called_once_with([
                            "/usr/bin/systemctl", "--no-ask-password", "--check-inhibitors=no", "suspend",
                        ], check=True)
                (battery / "capacity").write_text("-1")
                with self.assertRaises(ValueError):
                    suspend.check_battery(battery)

    def test_suspend_failure_is_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            battery = Path(folder)
            (battery / "capacity").write_text("2")
            (battery / "status").write_text("Discharging")
            with patch.object(suspend.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "systemctl")):
                with self.assertRaises(subprocess.CalledProcessError):
                    suspend.check_battery(battery)

    def test_siren_asset(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "siren.wav"
            subprocess.run([
                "/usr/bin/python3",
                str(Path(__file__).resolve().parents[1] / "src/make-siren.py"),
                str(output),
            ], check=True)
            with wave.open(str(output)) as sound:
                self.assertEqual(sound.getnchannels(), 1)
                self.assertEqual(sound.getsampwidth(), 2)
                self.assertEqual(sound.getnframes() / sound.getframerate(), 4)


if __name__ == "__main__":
    unittest.main()
