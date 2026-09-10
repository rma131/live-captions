"""Kill live Azure sessions and prove they come back by themselves.

This is the automated half of the resilience requirement. The other half — the
real one — is pulling the network mid-sentence, which only a human can do.

    uv run python scripts/test_reconnect.py
"""
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import captions as C  # noqa: E402


def states(pipe):
    return {c.label: ("up" if c.alive else "down") for c in pipe.channels}


def wait_until(fn, timeout, what):
    end = time.time() + timeout
    while time.time() < end:
        if fn():
            return True
        time.sleep(0.2)
    print(f"FAIL  timed out waiting for {what}")
    return False


def main() -> int:
    pipe = C.Pipeline()
    pipe.start()
    time.sleep(4)
    assert all(c.alive for c in pipe.channels), states(pipe)
    print(f"PASS  three sessions up: {states(pipe)}")

    ids = {c.label: id(c.recognizer) for c in pipe.channels}

    # Simulate exactly what a dropped uplink does: the SDK cancels the session.
    print("\n--- killing all three sessions ---")
    for c in pipe.channels:
        c.mark_down("simulated uplink drop")
    assert not any(c.alive for c in pipe.channels)
    print(f"PASS  all three marked down: {states(pipe)}")

    # audio must keep flowing without raising while sessions are dead
    block = (np.random.default_rng(0).normal(0, 0.05, (C.BLOCK, 3))).astype(np.float32)
    for _ in range(5):
        pipe.process(block, time.monotonic())
    print("PASS  audio path keeps running while sessions are down")

    if not wait_until(lambda: all(c.alive for c in pipe.channels), 45, "recovery"):
        return 1
    print(f"PASS  all three recovered unaided: {states(pipe)}")

    rebuilt = [c.label for c in pipe.channels if id(c.recognizer) != ids[c.label]]
    assert len(rebuilt) == 3, rebuilt
    print(f"PASS  recognizers actually rebuilt, not reused: {rebuilt}")

    # backoff must reset after a healthy reconnect, or the next outage waits longer
    if not wait_until(lambda: all(c.backoff == C.RETRY_BASE_S for c in pipe.channels),
                      10, "backoff reset"):
        return 1
    print("PASS  backoff reset to base after recovery")

    print("\n--- operator R / reconnect_all ---")
    ids = {c.label: id(c.recognizer) for c in pipe.channels}
    pipe.reconnect_all()
    if not wait_until(lambda: all(c.alive and id(c.recognizer) != ids[c.label]
                                  for c in pipe.channels), 45, "manual reconnect"):
        return 1
    print("PASS  reconnect_all rebuilt every session")

    pipe.stop()
    print("\nALL RECONNECT TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
