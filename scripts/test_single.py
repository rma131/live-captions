"""Single-feed mode (spec 006): does each sentence land in its language's column?

Real server, real guest websocket, real speech service — the same stance as
test_mute and test_reconnect. Fed with fixtures/bilingual_tts.wav (built by
make_tts_fixture.py if missing): English and Québec French, alternating.

Proves:
  1. with detection on, captions alternate EN, FR, EN, FR — each sentence lands
     in its own column, translated into the other;
  2. forcing French (key 2 / /round/2) puts EVERYTHING in the French column,
     and 0 returns to detection;
  3. W / {type:'flag'} writes a flag event naming the last caption;
  4. the transcript carries detected language, switch and since-switch fields;
  5. /band is served.

    uv run python scripts/test_single.py
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import wave

os.environ["MODE"] = "single"
os.environ.setdefault("LANGS", "en-US,fr-FR")
os.environ["TRANSCRIPT_DIR"] = tempfile.mkdtemp(prefix="test_single_")

import numpy as np          # noqa: E402
import websockets           # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import captions as C        # noqa: E402

PORT = 8125
BASE = f"http://127.0.0.1:{PORT}"
FIXTURE = os.path.join(ROOT, "fixtures", "bilingual_tts.wav")
EXPECTED = ["EN", "FR", "EN", "FR"]


def get(path: str):
    return json.loads(urllib.request.urlopen(BASE + path, timeout=5).read())


def feed(pipe: "C.Pipeline") -> None:
    """Replay the fixture at real-time speed, as scripts/replay.py does."""
    w = wave.open(FIXTURE, "rb")
    start, n = time.monotonic(), 0
    while True:
        raw = w.readframes(C.BLOCK)
        if len(raw) < C.BLOCK * 2:
            break
        block = (np.frombuffer(raw, "<i2").astype(np.float32) / 32767.0).reshape(-1, 1)
        due = start + n * C.BLOCK / C.DEVICE_RATE
        while time.monotonic() < due:
            time.sleep(0.005)
        pipe.process(block, due)
        n += 1
    w.close()


def collapse(seq):
    out = []
    for x in seq:
        if not out or out[-1] != x:
            out.append(x)
    return out


async def run_phase(pipe, ws, label: str) -> list[dict]:
    """Feed the fixture once and collect every final caption the guest sees."""
    finals = []
    t = threading.Thread(target=feed, args=(pipe,), daemon=True)
    t.start()
    deadline = time.monotonic() + 60
    while (t.is_alive() or time.monotonic() < quiet_until[0]) and time.monotonic() < deadline:
        try:
            m = json.loads(await asyncio.wait_for(ws.recv(), 0.5))
        except (asyncio.TimeoutError, TimeoutError):
            if not t.is_alive() and quiet_until[0] == 0:
                quiet_until[0] = time.monotonic() + 4   # let the last final land
            continue
        if m.get("type") == "caption" and m.get("final"):
            finals.append(m)
            print(f"   [{label}] {m['ch']}  {m['source'][:60]}")
    quiet_until[0] = 0
    return finals


quiet_until = [0.0]


async def main() -> int:
    if not os.path.exists(FIXTURE):
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "make_tts_fixture.py"), FIXTURE],
                       check=True)

    cfg = C.uvicorn.Config(C.app, host="127.0.0.1", port=PORT, log_level="error")
    threading.Thread(target=C.uvicorn.Server(cfg).run, daemon=True).start()
    await asyncio.sleep(1.5)

    pipe = C.Pipeline()
    pipe.start()
    await asyncio.sleep(2.0)

    status = get("/status")
    assert status["mode"] == "single", status
    assert [c["ch"] for c in status["columns"]] == ["EN", "FR"], status["columns"]
    print("PASS  single-feed mode, columns EN · FR")

    assert urllib.request.urlopen(BASE + "/band", timeout=5).status == 200
    print("PASS  /band is served")

    failures = 0
    async with websockets.connect(f"ws://127.0.0.1:{PORT}/ws/guest") as ws:
        # 1. detection
        finals = await run_phase(pipe, ws, "auto")
        got = collapse([m["ch"] for m in finals])
        if got == EXPECTED:
            print(f"PASS  detection: captions alternate {' '.join(got)}")
        else:
            failures += 1
            print(f"FAIL  detection: expected {EXPECTED}, got {got}")
        for m in finals:
            other = "fr" if m["ch"] == "EN" else "en"
            if not m["translations"].get(other):
                failures += 1
                print(f"FAIL  no {other} translation for: {m['source'][:50]}")
                break
        else:
            print("PASS  every caption carries the translation into the other language")

        # 2. force French
        get("/round/2")
        assert get("/status")["forced"] == "FR"
        await asyncio.sleep(3.0)                 # supervisor rebuilds the session
        forced = await run_phase(pipe, ws, "forced FR")
        chs = set(m["ch"] for m in forced)
        if forced and chs == {"FR"}:
            print("PASS  forcing French puts every caption in the French column")
        else:
            failures += 1
            print(f"FAIL  forced French, got columns {chs}")
        get("/round/0")
        assert get("/status")["forced"] is None
        print("PASS  0 returns to automatic detection")

    # 3. flag from the operator socket
    async with websockets.connect(f"ws://127.0.0.1:{PORT}/ws") as op:
        await op.recv()
        await op.send(json.dumps({"type": "flag"}))
        await asyncio.sleep(0.5)
    assert get("/status")["flags"] == 1
    print("PASS  W flags the last caption")

    pipe.stop()

    # 4. the transcript
    rows = [json.loads(l) for l in open(C.LOG.path, encoding="utf-8") if l.strip()]
    caps = [r for r in rows if "event" not in r]
    events = [r for r in rows if "event" in r]
    assert all("since_switch_s" in r and "detected" in r for r in caps), caps[:1]
    assert any(r.get("switched") for r in caps), "no switch was logged"
    flag = [e for e in events if e["event"] == "flag"]
    assert flag and flag[0]["last"] and flag[0]["last"]["heard"], flag
    assert sum(1 for e in events if e["event"] == "override") == 2
    print("PASS  transcript: detected language, switches, since-switch, overrides, flag")

    switch_rows = [r for r in caps if r.get("switched") and not r.get("forced")]
    print(f"\n   {len(caps)} captions, {len(switch_rows)} after a switch; transcript {C.LOG.path}")

    if failures:
        print(f"\n{failures} SINGLE-FEED CHECK(S) FAILED")
        return 1
    print("\nALL SINGLE-FEED TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
