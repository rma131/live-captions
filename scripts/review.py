"""Read a transcript and say what to fix.

    uv run python scripts/review.py                    # newest transcript
    uv run python scripts/review.py transcripts/x.jsonl
    uv run python scripts/review.py --full             # print every line too

Reports what actually happened, then the three things that are actionable:
which correction rules fired, which never did, and which sentences ALMOST
matched a prepared line.
"""
import glob
import json
import re
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from captions import (SCRIPT_MATCH, TRANSCRIPT_DIR, _normalise,  # noqa: E402
                      load_glossary, load_speeches)
import difflib  # noqa: E402


def newest() -> str | None:
    files = sorted(glob.glob(os.path.join(TRANSCRIPT_DIR, "*.jsonl")))
    return files[-1] if files else None


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    full = "--full" in sys.argv
    path = args[0] if args else newest()
    if not path or not os.path.exists(path):
        print(f"no transcript found in {TRANSCRIPT_DIR}/")
        return 1

    every = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    # Since spec 006 the transcript also carries event rows — overrides, flags,
    # audience counts, recording start — marked with an "event" key. Captions are
    # the rows without one.
    rows = [r for r in every if "event" not in r]
    events = [r for r in every if "event" in r]
    if not rows:
        print(f"{path} is empty")
        return 1

    print(f"=== {path} — {len(rows)} finalised lines ===\n")
    if events:
        kinds = {}
        for e in events:
            kinds[e["event"]] = kinds.get(e["event"], 0) + 1
        print("events: " + ", ".join(f"{k} {n}" for k, n in sorted(kinds.items())))
        peak = max((e.get("peak_guests", 0) for e in events if e["event"] == "audience"), default=None)
        if peak is not None:
            print(f"peak guest screens connected: {peak}")
        print()

    if full:
        for r in rows:
            flag = " [prepared]" if r.get("prepared") else (
                   " [corrected]" if r.get("corrected") else "")
            mute = " [MUTED]" if r.get("muted") else ""
            print(f"{r['clock']}  {r['ch']}{flag}{mute}\n  {r['heard']}")
            for k, v in r["translations"].items():
                print(f"    {k}: {v}")
            print()

    # ---------------------------------------------------------------- summary
    by_ch = Counter(r["ch"] for r in rows)
    prepared = sum(1 for r in rows if r.get("prepared"))
    corrected = sum(1 for r in rows if r.get("corrected"))
    muted = sum(1 for r in rows if r.get("muted"))
    print("--- summary ---")
    print(f"  lines per channel : {dict(by_ch)}")
    print(f"  prepared lines hit: {prepared}")
    print(f"  corrections fired : {corrected}")
    print(f"  spoken while muted: {muted}")
    words = sum(len(r["heard"].split()) for r in rows)
    print(f"  words recognised  : {words}")

    # ------------------------------------------------- which rules earned keep
    _, rules = load_glossary()
    fired = Counter()
    for r in rows:
        raw = r.get("raw_heard", "")
        for pattern, right in rules:
            if pattern.search(raw):
                fired[f"{pattern.pattern} -> {right}"] += 1
    print("\n--- correction rules ---")
    if not rules:
        print("  none configured")
    for pattern, right in rules:
        key = f"{pattern.pattern} -> {right}"
        n = fired.get(key, 0)
        # strip \b and the Turkish-suffix group so the rule reads as written
        wrong = re.sub(r"\(\(\?:.*$", "", pattern.pattern).replace(r"\b", "")
        note = "" if n else "   (never fired — delete it if it is a risk)"
        print(f"  {n:3d}x  {wrong} -> {right}{note}")

    # ------------------------------------------- sentences that nearly matched
    lines = load_speeches()
    print("\n--- near misses against prepared lines ---")
    near = []
    for r in rows:
        if r.get("prepared"):
            continue
        key = _normalise(r["heard"])
        best, score = None, 0.0
        for entry in lines:
            if not entry["lang"].startswith(r["lang"][:2]):
                continue
            ratio = difflib.SequenceMatcher(None, key, entry["_key"]).ratio()
            if ratio > score:
                best, score = entry, ratio
        if best and 0.45 <= score < SCRIPT_MATCH:
            near.append((score, r["heard"], best["said"]))
    if not near:
        print("  none — every prepared line either matched or was not attempted")
    for score, heard, said in sorted(near, reverse=True)[:15]:
        print(f"  {score:.2f}  heard   {heard}")
        print(f"        script  {said}")
    if near:
        print(f"\n  These fell below SCRIPT_MATCH={SCRIPT_MATCH}. Either reword the")
        print("  entry in speeches.yaml to match what was really said, or lower the")
        print("  threshold — but lowering it risks matching the wrong line.")

    # ---------------------------------------------- what changed vs raw output
    print("\n--- lines where our post-processing changed the output ---")
    changed = [r for r in rows if r.get("prepared") or r.get("corrected")]
    if not changed:
        print("  none")
    for r in changed[:15]:
        print(f"  {r['clock']} {r['ch']} {'prepared' if r.get('prepared') else 'corrected'}")
        print(f"    azure : {r.get('raw_heard','')}")
        print(f"    shown : {r['heard']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
