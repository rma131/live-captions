"""Mute regression test. Mute is the most important feature in this project.

Uses a REAL websocket client against a REAL server, deliberately: an earlier
version of this test used a fake client object and therefore did not notice that
uvicorn had no websocket library installed at all.

    uv run python scripts/test_mute.py
"""

import asyncio
import json
import os
import sys
import threading
import urllib.request

import websockets

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import captions as C  # noqa: E402

PORT = 8123
BASE = f"http://127.0.0.1:{PORT}"


def get(path: str) -> dict:
    return json.loads(urllib.request.urlopen(BASE + path).read())


def caption(text: str) -> None:
    # pushed from a plain thread, exactly as the Azure SDK callbacks do
    C.BUS.send({"type": "caption", "final": True, "ch": "EN",
                "source": text, "translations": {"tr": text, "es": text}})


async def drain(ws, seconds: float = 0.6) -> list[dict]:
    out = []
    try:
        while True:
            out.append(json.loads(await asyncio.wait_for(ws.recv(), seconds)))
    except (asyncio.TimeoutError, TimeoutError):
        pass
    return out


async def main() -> int:
    cfg = C.uvicorn.Config(C.app, host="127.0.0.1", port=PORT, log_level="error")
    threading.Thread(target=C.uvicorn.Server(cfg).run, daemon=True).start()
    await asyncio.sleep(1.5)

    async with websockets.connect(f"ws://127.0.0.1:{PORT}/ws") as ws:
        await drain(ws)
        print("PASS  websocket actually connects")

        threading.Thread(target=caption, args=("before mute",)).start()
        msgs = await drain(ws)
        assert any(m.get("source") == "before mute" for m in msgs), msgs
        print("PASS  captions flow when unmuted")

        assert get("/mute")["muted"] is True
        msgs = await drain(ws)
        assert any(m["type"] == "clear" for m in msgs), msgs
        print("PASS  HTTP /mute sets state and clears the screen")

        threading.Thread(target=caption, args=("DURING MUTE",)).start()
        leaked = [m for m in await drain(ws) if m["type"] == "caption"]
        assert not leaked, f"CAPTION LEAKED WHILE MUTED: {leaked}"
        print("PASS  no caption reaches the page while muted")

        # the page's own M key must reach the same flag as the HTTP endpoint
        await ws.send(json.dumps({"type": "mute", "toggle": True}))
        await drain(ws)
        assert get("/status")["muted"] is False
        print("PASS  M on the page toggles the same server-side flag")

        threading.Thread(target=caption, args=("after unmute",)).start()
        msgs = await drain(ws)
        assert any(m.get("source") == "after unmute" for m in msgs), msgs
        print("PASS  captions resume after unmute")

    print("\nALL MUTE TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
