"""Guest fan-out regression test — can a phone read captions, and nothing else?

Opening the server to the venue network puts it in front of every guest, and the
same process serves mute. This proves the separation holds, using a REAL server
reached over a REAL network address, because a guest attacking it would use one
too: connecting over the LAN address is what makes request.client.host something
other than 127.0.0.1.

    uv run python scripts/test_guest.py
"""

import asyncio
import json
import os
import sys
import threading
import urllib.error
import urllib.request

import websockets

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import captions as C  # noqa: E402

PORT = 8124


def get(base: str, path: str):
    """Returns the parsed body, or the HTTP status code if it was refused."""
    try:
        return json.loads(urllib.request.urlopen(base + path, timeout=5).read())
    except urllib.error.HTTPError as e:
        return e.code


def caption(text: str) -> None:
    C.BUS.send({"type": "caption", "final": True, "ch": "EN",
                "source": text, "translations": {"tr": "TR " + text, "es": "ES " + text}})


async def drain(ws, seconds: float = 0.6) -> list[dict]:
    out = []
    try:
        while True:
            out.append(json.loads(await asyncio.wait_for(ws.recv(), seconds)))
    except (asyncio.TimeoutError, TimeoutError):
        pass
    return out


async def main() -> int:
    cfg = C.uvicorn.Config(C.app, host="0.0.0.0", port=PORT, log_level="error")
    threading.Thread(target=C.uvicorn.Server(cfg).run, daemon=True).start()
    await asyncio.sleep(1.5)

    local = f"http://127.0.0.1:{PORT}"
    lan_ip = C.lan_address()
    lan = f"http://{lan_ip}:{PORT}" if lan_ip else None

    C.STATE.muted = False

    async with websockets.connect(f"ws://127.0.0.1:{PORT}/ws/guest") as g:
        first = await drain(g)
        assert any(m.get("guest") for m in first), first
        print("PASS  guest socket connects and is told it is a guest")

        threading.Thread(target=caption, args=("hello",)).start()
        msgs = await drain(g)
        got = [m for m in msgs if m.get("type") == "caption"]
        assert got and got[0]["translations"]["tr"] == "TR hello", msgs
        print("PASS  guest receives captions with all translations")

        # A guest with the console open sending the operator's own messages.
        for hostile in ({"type": "mute", "on": True},
                        {"type": "primary", "ch": 3},
                        {"type": "gate", "up": True},
                        {"type": "reconnect"}):
            await g.send(json.dumps(hostile))
        await drain(g)
        await g.send(json.dumps({"type": "flag"}))
        await drain(g)
        assert C.STATE.muted is False, "a guest muted the screen"
        assert C.STATE.primary is None, "a guest changed the round"
        assert C.STATE.flags == 0, "a guest flagged a caption"
        print("PASS  guest socket ignores mute, rounds, gate, flag and reconnect")

        # Mute still has to cover them, and it is enforced before fan-out.
        C.set_mute(True)
        await drain(g)
        threading.Thread(target=caption, args=("SECRET",)).start()
        leaked = [m for m in await drain(g) if m.get("type") == "caption"]
        assert not leaked, f"CAPTION LEAKED TO A GUEST WHILE MUTED: {leaked}"
        print("PASS  no caption reaches a guest phone while muted")
        C.set_mute(False)

    if not lan:
        print("SKIP  no LAN address on this machine; remote-refusal checks skipped")
    else:
        assert get(lan, "/mute") == 403, "a phone on the venue network could MUTE"
        assert C.STATE.muted is False
        print(f"PASS  /mute refused from {lan_ip} (403)")

        for path in ("/unmute", "/round/3", "/gate/up", "/reconnect", "/flag"):
            assert get(lan, path) == 403, f"{path} was reachable from the network"
        print("PASS  round, gate, unmute, reconnect and flag all refused from the network")

        band = urllib.request.urlopen(lan + "/band", timeout=5)
        assert band.status == 200
        print("PASS  /band is readable from the network (it is read-only by construction)")

        try:
            async with websockets.connect(f"ws://{lan_ip}:{PORT}/ws") as ws:
                await drain(ws)
                raise AssertionError("operator socket accepted a non-local client")
        except (websockets.exceptions.WebSocketException, OSError):
            print("PASS  operator socket refuses a non-local client")

        async with websockets.connect(f"ws://{lan_ip}:{PORT}/ws/guest") as g2:
            assert await drain(g2), "guest socket should still work over the LAN"
            print("PASS  guest socket still works over the LAN")

    # ...and the operator, at this laptop, is unaffected by any of it.
    assert get(local, "/mute")["muted"] is True
    assert get(local, "/unmute")["muted"] is False
    print("PASS  operator controls still work from localhost")

    print("\nALL GUEST TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
