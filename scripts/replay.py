"""Feed a multichannel WAV through the full pipeline at real-time speed.

After this exists, no change should require talking into a microphone.

    uv run python scripts/replay.py fixtures/rehearsal.wav
    uv run python scripts/replay.py fixtures/rehearsal.wav --fast   # no pacing
"""

import os
import sys
import time
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from captions import (BLOCK, DEVICE_RATE, NCHAN, Pipeline,  # noqa: E402
                      serve_in_background)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    path = sys.argv[1]
    realtime = "--fast" not in sys.argv

    wav = wave.open(path, "rb")
    if wav.getnchannels() < NCHAN:
        print(f"{path} has {wav.getnchannels()} channels, need {NCHAN}")
        return 1
    if wav.getframerate() != DEVICE_RATE:
        print(f"{path} is {wav.getframerate()} Hz, pipeline expects {DEVICE_RATE}")
        return 1
    nch = wav.getnchannels()

    serve_in_background()
    pipe = Pipeline()
    pipe.start()
    print(f"replaying {path} ({wav.getnframes()/DEVICE_RATE:.1f}s)"
          f"{'' if realtime else ' as fast as possible'}\n")

    start = time.monotonic()
    n = 0
    try:
        while True:
            raw = wav.readframes(BLOCK)
            if len(raw) < BLOCK * nch * 2:
                break
            block = (np.frombuffer(raw, "<i2").reshape(-1, nch)[:, :NCHAN]
                     .astype(np.float32) / 32767.0)
            # Replay must be paced. Dumping an hour of audio into Azure in
            # ten seconds does not test the same thing at all.
            if realtime:
                due = start + n * BLOCK / DEVICE_RATE
                while time.monotonic() < due:
                    time.sleep(0.005)
            pipe.process(block, start + n * BLOCK / DEVICE_RATE)
            n += 1
    except KeyboardInterrupt:
        print("\ninterrupted")
    finally:
        # Let the tail of the audio finalize before tearing the sessions down.
        time.sleep(3.0)
        pipe.stop()
        wav.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
