import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]


@unittest.skipIf(os.geteuid() == 0, "Installer deliberately rejects root desktop sessions")
class InstallTests(unittest.TestCase):
    def test_install_and_uninstall_in_isolated_home(self):
        with tempfile.TemporaryDirectory() as folder:
            staging = Path(folder)
            home = staging / "desktop user"
            commands = staging / "bin"
            root = staging / "root"
            commands.mkdir()
            home.mkdir()
            (root / "etc/systemd/system").mkdir(parents=True)
            runtime = staging / "runtime"
            runtime.mkdir()
            # Redirect privileged file operations and never invoke real systemctl.
            (commands / "sudo").write_text('''#!/usr/bin/python3
import os
from pathlib import Path
import subprocess
import sys
args = sys.argv[1:]
if args[0] in {"-v", "systemctl"}:
    sys.exit(0)
assert args[0] in {"install", "rm"}, args
if args[0] == "install":
    for option in ("-o", "-g"):
        index = args.index(option)
        del args[index:index + 2]
for index, arg in enumerate(args):
    if arg.startswith(("/usr/local/", "/etc/systemd/system/")):
        args[index] = str(Path(os.environ["TEST_ROOT"]) / arg.lstrip("/"))
sys.exit(subprocess.run(args).returncode)
''')
            for name in ("systemctl", "pactl", "paplay", "notify-send"):
                (commands / name).write_text("#!/bin/sh\nexit 0\n")
            for command in commands.iterdir():
                command.chmod(0o755)
            environment = dict(os.environ, HOME=str(home), TEST_ROOT=str(root),
                               XDG_RUNTIME_DIR=str(runtime),
                               PATH=f"{commands}:{os.environ['PATH']}")
            result = subprocess.run(["bash", str(REPO / "install.sh")], env=environment,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

            alarm = home / ".local/bin/battery-alarm"
            helper = root / "usr/local/libexec/battery-critical-suspend"
            self.assertEqual(alarm.read_bytes(), (REPO / "src/battery-alarm").read_bytes())
            self.assertEqual(helper.read_bytes(), (REPO / "src/battery-critical-suspend.py").read_bytes())
            self.assertTrue(os.access(alarm, os.X_OK))
            self.assertTrue((home / ".local/share/battery-alarm/siren.wav").is_file())
            self.assertIn('"%h/.local/bin/battery-alarm"',
                          (home / ".config/systemd/user/battery-alarm.service").read_text())
            (runtime / "battery-alarm-notified").touch()
            unrelated = home / ".local/share/battery-alarm/keep.txt"
            unrelated.write_text("Unrelated file")

            result = subprocess.run(["bash", str(REPO / "uninstall.sh")], env=environment,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(alarm.exists())
            self.assertFalse(helper.exists())
            self.assertFalse((home / ".local/share/battery-alarm/siren.wav").exists())
            self.assertFalse((runtime / "battery-alarm-notified").exists())
            self.assertFalse(any((root / "etc/systemd/system").iterdir()))
            self.assertEqual(unrelated.read_text(), "Unrelated file")


if __name__ == "__main__":
    unittest.main()
