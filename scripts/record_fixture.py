"""Record all three channels to a multichannel WAV, for regression fixtures.

Use this at Friday's rehearsal. Once a fixture exists, scripts/replay.py can
exercise the whole pipeline without anyone talking into a microphone.

    uv run python scripts/record_fixture.py fixtures/rehearsal.wav [seconds]
"""

import os
import sys
import time
import wave

import numpy as np
import sounddevice as sd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from captions import (BLOCK, DEVICE_RATE, MAX_USB, NCHAN, USB_CHANNELS,  # noqa: E402
                      find_device)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    path = sys.argv[1]
    limit = float(sys.argv[2]) if len(sys.argv) > 2 else None

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    device = find_device(MAX_USB)

    wav = wave.open(path, "wb")
    wav.setnchannels(NCHAN)
    wav.setsampwidth(2)
    wav.setframerate(DEVICE_RATE)

    started = time.monotonic()
    peak = np.zeros(NCHAN, dtype=np.float32)

    def callback(indata, frames, time_info, status):
        if status:
            print(f"audio status: {status}", file=sys.stderr)
        # Record the three MAPPED mics, so replay needs no mapping and a
        # fixture stays valid even if the USB layout changes later.
        mics = indata[:, [c - 1 for c in USB_CHANNELS]]
        np.maximum(peak, np.abs(mics).max(axis=0), out=peak)
        wav.writeframes((np.clip(mics, -1, 1) * 32767).astype("<i2").tobytes())

    print(f"recording mics on USB {USB_CHANNELS} -> {NCHAN} ch @ {DEVICE_RATE} Hz -> {path}")
    try:
        with sd.InputStream(device=device, channels=MAX_USB, samplerate=DEVICE_RATE,
                            blocksize=BLOCK, dtype="float32", callback=callback):
            while limit is None or time.monotonic() - started < limit:
                sd.sleep(200)
                el = time.monotonic() - started
                lvl = "  ".join(f"ch{i+1} {20*np.log10(max(p,1e-6)):6.1f} dBFS"
                                for i, p in enumerate(peak))
                print(f"\r{el:6.1f}s   {lvl}", end="", flush=True)
                peak[:] = 0
    except KeyboardInterrupt:
        pass
    finally:
        wav.close()
    print(f"\nwrote {path} ({os.path.getsize(path)/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
