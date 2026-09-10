"""Cut a range of an L-8 recorder session into a fixture replay.py can drive.

The recorder wrote three separate mono 24-bit files per session. The pipeline
wants one interleaved 3-channel 16-bit file, in CHANNELS order, so this is the
bridge between the two:

    TRACK01.WAV (mono 24-bit)  ES ─┐
    TRACK02.WAV (mono 24-bit)  EN ─┼─→  one 3-channel 16-bit WAV
    TRACK03.WAV (mono 24-bit)  TR ─┘

Ranges may be wall-clock times, read against the session start encoded in the
directory name (260906_150948 → 15:09:48), or plain seconds from the start.

    uv run python scripts/make_fixture.py SESSION_DIR out.wav --from 16:11:00 --to 17:05:00
    uv run python scripts/make_fixture.py SESSION_DIR out.wav --from 3672 --to 6912

Then:  uv run python scripts/replay.py out.wav

Streams in chunks — a full speech block is about a gigabyte and does not want to
be held in memory.
"""

import argparse
import os
import re
import sys
import wave

import numpy as np

# TRACK number -> the channel it becomes in the output, in CHANNELS order.
# Console channel 1 is Spanish, 2 English, 3 Turkish; the recorder numbers its
# tracks the same way, so this is a straight 1:1 and the output drops into
# replay.py with no remapping.
TRACKS = ["TRACK01.WAV", "TRACK02.WAV", "TRACK03.WAV"]
LABELS = ["ES", "EN", "TR"]

RATE = 48000
CHUNK = 48000 * 10          # ten seconds of frames per pass


def parse_point(value: str, session_start_s: float | None) -> float:
    """Seconds from the start of the session, from either '16:11:00' or '3672'."""
    if ":" not in value:
        return float(value)
    if session_start_s is None:
        sys.exit(f"{value!r} is a clock time, but the folder name carries no start time")
    h, m, s = (int(p) for p in value.split(":"))
    offset = h * 3600 + m * 60 + s - session_start_s
    if offset < 0:
        sys.exit(f"{value} is before the session started")
    return offset


def session_start(path: str) -> float | None:
    """260906_150948 -> 15:09:48 as seconds since midnight."""
    m = re.search(r"\d{6}_(\d{2})(\d{2})(\d{2})", os.path.basename(path.rstrip("/")))
    if not m:
        return None
    h, mi, s = (int(g) for g in m.groups())
    return h * 3600 + mi * 60 + s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("session", help="recorder session directory holding TRACK01-03.WAV")
    ap.add_argument("out", help="fixture to write")
    ap.add_argument("--from", dest="start", default="0", help="HH:MM:SS or seconds")
    ap.add_argument("--to", dest="end", default=None, help="HH:MM:SS or seconds")
    args = ap.parse_args()

    paths = [os.path.join(args.session, t) for t in TRACKS]
    missing = [p for p in paths if not os.path.exists(p)]
    if missing:
        sys.exit("missing: " + ", ".join(missing))

    started = session_start(args.session)
    ins = [wave.open(p, "rb") for p in paths]

    for p, w in zip(paths, ins):
        if w.getnchannels() != 1 or w.getframerate() != RATE or w.getsampwidth() != 3:
            sys.exit(f"{p}: expected mono 24-bit {RATE} Hz, got {w.getnchannels()}ch "
                     f"{w.getsampwidth()*8}-bit {w.getframerate()} Hz")

    total = min(w.getnframes() for w in ins)
    first = int(parse_point(args.start, started) * RATE)
    last = int(parse_point(args.end, started) * RATE) if args.end else total
    last = min(last, total)
    if first >= last:
        sys.exit(f"empty range: {first} to {last} frames")

    for w in ins:
        w.setpos(first)

    out = wave.open(args.out, "wb")
    out.setnchannels(len(ins))
    out.setsampwidth(2)
    out.setframerate(RATE)

    if started is not None:
        clock = lambda f: f"{int((started + f/RATE)//3600)%24:02d}:" \
                          f"{int((started + f/RATE)//60)%60:02d}:" \
                          f"{int(started + f/RATE)%60:02d}"
        print(f"session starts {clock(0)}, cutting {clock(first)} to {clock(last)}")
    print(f"{(last-first)/RATE/60:.1f} min, {' '.join(LABELS)} -> {args.out}")

    remaining = last - first
    peak = np.zeros(len(ins))
    while remaining > 0:
        n = min(CHUNK, remaining)
        cols = []
        for w in ins:
            raw = w.readframes(n)
            got = len(raw) // 3
            if got == 0:
                break
            # 24-bit little-endian: the top two bytes of each sample already are
            # the 16-bit value. Truncation, no dither — we are discarding detail
            # 90 dB down, well under the noise floor of a room full of people.
            b = np.frombuffer(raw, dtype=np.uint8).reshape(got, 3)[:, 1:3]
            cols.append(np.ascontiguousarray(b).view("<i2").reshape(got))
        if not cols or min(len(c) for c in cols) == 0:
            break
        n = min(len(c) for c in cols)
        block = np.stack([c[:n] for c in cols], axis=1)
        peak = np.maximum(peak, np.abs(block).max(axis=0) / 32767.0)
        out.writeframes(block.tobytes())
        remaining -= n
        done = (last - first - remaining) / (last - first)
        print(f"\r  {done*100:5.1f}%", end="", flush=True)

    print()
    print("peak per channel: " + "  ".join(f"{l} {p:.3f}" for l, p in zip(LABELS, peak)))
    if min(peak) < 0.001:
        print("WARNING: a channel is essentially silent — check the track mapping")
    out.close()
    for w in ins:
        w.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
