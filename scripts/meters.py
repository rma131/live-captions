"""Live level meter for EVERY input channel on the device.

Diagnostic for "one mic works and the others don't". Tap each capsule in turn
and watch which channel number moves. Do not assume the L-8's USB channel order
matches the console's channel numbering — verify it.

    uv run python scripts/meters.py
"""

import os
import sys

import numpy as np
import sounddevice as sd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from captions import DEVICE_RATE, GATE_THRESHOLD, MATCH  # noqa: E402

BLOCK = 2400  # 50 ms


def main() -> int:
    hits = [
        (i, d) for i, d in enumerate(sd.query_devices())
        if d["max_input_channels"] >= 2 and MATCH.lower() in d["name"].lower()
    ]
    if len(hits) != 1:
        print(f"device match {MATCH!r} found {len(hits)} candidates")
        return 1
    idx, dev = hits[0]
    nch = int(dev["max_input_channels"])
    print(f"device [{idx}] {dev['name']} — {nch} input channels @ {DEVICE_RATE} Hz")
    print(f"gate threshold is {GATE_THRESHOLD}. A channel must exceed it to be forwarded.")
    print("\nTap each mic capsule in turn. Watch which channel number moves.\n")

    peak = np.zeros(nch, dtype=np.float32)

    def callback(indata, frames, time_info, status):
        np.maximum(peak, np.sqrt(np.mean(indata * indata, axis=0)), out=peak)

    with sd.InputStream(device=idx, channels=nch, samplerate=DEVICE_RATE,
                        blocksize=BLOCK, dtype="float32", callback=callback):
        try:
            while True:
                sd.sleep(150)
                row = []
                for i in range(nch):
                    r = float(peak[i])
                    bar = "#" * min(20, int(60 * r))
                    over = "*" if r >= GATE_THRESHOLD else " "
                    row.append(f"{i+1:2d}{over}{r:.4f} {bar:<20}")
                print("\033[2J\033[H" + "\n".join(row), flush=True)
                print("\n* = above gate threshold. ctrl-c to stop.")
                peak[:] = 0
        except KeyboardInterrupt:
            print("\nstopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
