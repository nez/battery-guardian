"""Generate a four-second pulsed industrial alarm without extra dependencies."""
from array import array
import math
from pathlib import Path
import sys
import wave

rate = 44100
samples = array("h")
for index in range(4 * rate):
    seconds = index / rate
    pulse = seconds % 0.8
    fade = max(0, min(1, pulse / 0.01, (0.55 - pulse) / 0.01))
    phase = 2 * math.pi * 185 * seconds
    tone = (math.sin(phase) + 0.6 * math.sin(3 * phase)
            + 0.3 * math.sin(5 * phase) + 0.4 * math.sin(2 * math.pi * 241 * seconds))
    samples.append(round(13000 * tone * fade))
if sys.byteorder != "little":
    samples.byteswap()
destination = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("siren.wav")
with wave.open(str(destination), "wb") as sound:
    sound.setparams((1, 2, rate, 0, "NONE", "not compressed"))
    sound.writeframes(samples.tobytes())
