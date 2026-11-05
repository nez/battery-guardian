import importlib.machinery
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


loader = importlib.machinery.SourceFileLoader(
    "battery_alarm", str(Path(__file__).resolve().parents[1] / "src/battery-alarm")
)
spec = importlib.util.spec_from_loader(loader.name, loader)
alarm = importlib.util.module_from_spec(spec)
loader.exec_module(alarm)


class BatteryAlarmTests(unittest.TestCase):
    def test_threshold_repeat_and_rearm(self):
        with tempfile.TemporaryDirectory() as folder:
            battery = Path(folder)
            state = battery / "notified"
            with patch.object(alarm, "sound_alarm") as sound, patch.object(alarm.subprocess, "run") as run:
                run.return_value.returncode = 0
                for capacity, status, expected in [
                    (6, "Discharging", 0),
                    (5, "Discharging", 1),
                    (4, "Discharging", 1),
                    (2, "Charging", 1),
                    (2, "Discharging", 2),
                    (10, "Discharging", 2),
                    (3, "Unknown", 2),
                    (3, "Discharging", 3),
                ]:
                    (battery / "capacity").write_text(str(capacity))
                    (battery / "status").write_text(status)
                    alarm.check_battery(battery, state)
                    self.assertEqual(sound.call_count, expected, (capacity, status))

    def test_failed_audio_is_retried(self):
        with tempfile.TemporaryDirectory() as folder:
            battery = Path(folder)
            state = battery / "notified"
            (battery / "capacity").write_text("5")
            (battery / "status").write_text("Discharging")
            with patch.object(alarm, "sound_alarm", side_effect=RuntimeError("audio unavailable")):
                with self.assertRaises(RuntimeError):
                    alarm.check_battery(battery, state)
            self.assertFalse(state.exists())

    def test_audio_unmutes_and_sets_volume_before_playing(self):
        with patch.object(alarm.subprocess, "run") as run, patch.object(alarm.time, "sleep"):
            alarm.sound_alarm()
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(commands[0], ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"])
        self.assertEqual(commands[1], ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "100%"])
        self.assertEqual(len(commands), 5)
        self.assertTrue(all(command[0] == "paplay" for command in commands[2:]))

    def test_invalid_capacity_does_not_play_audio(self):
        with tempfile.TemporaryDirectory() as folder:
            battery = Path(folder)
            (battery / "status").write_text("Discharging")
            with patch.object(alarm, "sound_alarm") as sound:
                for capacity in ["-1", "101", "invalid"]:
                    (battery / "capacity").write_text(capacity)
                    with self.assertRaises(ValueError):
                        alarm.check_battery(battery, battery / "notified")
                sound.assert_not_called()


if __name__ == "__main__":
    unittest.main()
