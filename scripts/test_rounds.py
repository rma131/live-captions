"""Check interpretation rounds behave.

The rule being tested: while a round is running, the two microphones that are
not the speaker carry HUMAN interpreters, so what they say must never be
machine-translated again. Re-translating an interpretation back into the
language it came from puts round-trip nonsense on top of the original.

    uv run python scripts/test_rounds.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import captions as C  # noqa: E402


class FakeChannel:
    def __init__(self, idx, label):
        self.idx, self.label = idx, label
    is_interpreter = C.Channel.is_interpreter


def main() -> int:
    chans = [FakeChannel(i, lbl) for i, (lbl, _, _) in enumerate(C.CHANNELS)]
    bad = 0

    def check(desc, got, want):
        nonlocal bad
        ok = got == want
        bad += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {desc}" + ("" if ok else f"  got {got!r} want {want!r}"))

    # Looked up by label, never by index — the channel order is a config
    # decision and this test must survive changing it.
    idx = {lbl: i for i, (lbl, _, _) in enumerate(C.CHANNELS)}

    C.STATE.primary = None
    check("free-for-all: nobody is an interpreter",
          [c.is_interpreter() for c in chans], [False, False, False])

    for speaker, want_order in (("ES", ["EN", "TR"]),
                                ("TR", ["EN", "ES"]),
                                ("EN", ["ES", "TR"])):
        C.STATE.primary = idx[speaker]
        check(f"{speaker} round: only {speaker} is the speaker",
              [c.label for c in chans if not c.is_interpreter()], [speaker])
        check(f"{speaker} round order", C.STATE.order(), want_order)

    # every language must be reachable as an original, and never interpret itself
    for idx, (label, _, _) in enumerate(C.CHANNELS):
        C.STATE.primary = idx
        order = C.STATE.order()
        check(f"{label} round covers all three languages once",
              sorted([label] + order), sorted(l for l, _, _ in C.CHANNELS))
        check(f"{label} does not interpret itself", label in order, False)

    C.STATE.primary = None
    check("released back to free-for-all",
          [c.is_interpreter() for c in chans], [False, False, False])

    print("\nALL ROUND TESTS PASSED" if not bad else f"\n{bad} FAILED")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
