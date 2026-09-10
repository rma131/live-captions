"""Phase 0: what does PortAudio actually see?

Run this at the venue before anything else. It answers one question: does the L-8
show up with enough input channels to read three mics separately?
"""

import os
import sys

import sounddevice as sd
from dotenv import load_dotenv

load_dotenv()
MATCH = os.getenv("AUDIO_DEVICE_MATCH", "L-8")


def main() -> int:
    devices = sd.query_devices()

    print(f"{'idx':>3}  {'in':>3}  {'rate':>7}  name")
    print("-" * 60)
    inputs = []
    for idx, dev in enumerate(devices):
        if dev["max_input_channels"] < 1:
            continue
        inputs.append((idx, dev))
        print(
            f"{idx:>3}  {dev['max_input_channels']:>3}  "
            f"{dev['default_samplerate']:>7.0f}  {dev['name']}"
        )

    # The whole point of the exercise: does our .env substring find one usable device?
    print()
    print(f"matching AUDIO_DEVICE_MATCH={MATCH!r} ...")
    hits = [(i, d) for i, d in inputs if MATCH.lower() in d["name"].lower()]

    if not hits:
        print(f"  NO MATCH. Nothing with an input matches {MATCH!r}.")
        return 1
    if len(hits) > 1:
        print(f"  AMBIGUOUS. {len(hits)} devices match {MATCH!r}:")
        for i, d in hits:
            print(f"    [{i}] {d['name']} ({d['max_input_channels']} in)")
        return 1

    idx, dev = hits[0]
    print(f"  [{idx}] {dev['name']}")
    print(f"       {dev['max_input_channels']} input channels @ {dev['default_samplerate']:.0f} Hz")
    if dev["max_input_channels"] < 3:
        print("  FAIL: fewer than 3 input channels. Is the L-8 in Audio I/F mode?")
        print("  (Mixer mode, then function button 8.)")
        return 1
    print("  OK: enough channels for three mics.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
