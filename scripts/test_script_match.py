"""Check prepared-line matching: close sentences match, unrelated ones don't.

Uses its own fixture rather than glossary/speeches.yaml — that file holds the
real speeches and changes every time someone edits their toast, which is not a
reason for this test to fail.

    uv run python scripts/test_script_match.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from captions import SCRIPT_MATCH, load_speeches, match_script  # noqa: E402

FIXTURE = """
lines:
  - lang: en
    said: "Today we celebrate the marriage of Marisol and Kerem."
    en: "Today we celebrate the marriage of Marisol and Kerem."
    es: "Hoy celebramos el matrimonio de Marisol y Kerem."
    tr: "Bugun Marisol ve Kerem'in evliligini kutluyoruz."
  - lang: tr
    said: "Onu cok seviyorum ve hayatimin geri kalanini onunla gecirmek istiyorum."
    tr: "Onu cok seviyorum ve hayatimin geri kalanini onunla gecirmek istiyorum."
    en: "I love her very much and I want to spend the rest of my life with her."
    es: "La quiero muchisimo y quiero pasar el resto de mi vida con ella."
"""

CASES = [
    # (what the recogniser produced, source lang, should it match?)
    ("Today we celebrate the marriage of Marisol and Kerem.", "en-US", True),
    ("today we celebrate the marriage of marisol and kerem", "en-US", True),
    # small slips must still match — nobody says a prepared line perfectly
    ("So today we celebrate the marriage of Marisol and Kerem.", "en-US", True),
    # genuinely different sentences must NOT match
    ("Please raise your glasses to the happy couple.", "en-US", False),
    ("Thanks everyone for coming today.", "en-US", False),
    # right words, wrong language channel
    ("Today we celebrate the marriage of Marisol and Kerem.", "tr-TR", False),
    ("Onu cok seviyorum ve hayatimin geri kalanini onunla gecirmek istiyorum.",
     "tr-TR", True),
]


def main() -> int:
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False,
                                     encoding="utf-8") as fh:
        fh.write(FIXTURE)
        path = fh.name
    try:
        lines = load_speeches(path)
        print(f"{len(lines)} fixture lines, threshold {SCRIPT_MATCH}\n")
        bad = 0
        for text, lang, want in CASES:
            hit = match_script(text, lang, lines)
            ok = bool(hit) == want
            bad += not ok
            print(f"{'PASS' if ok else 'FAIL'}  [{lang}] {text[:50]!r:54} "
                  f"{'matched' if hit else 'no match'}")
        print("\nALL SCRIPT MATCH TESTS PASSED" if not bad else f"\n{bad} FAILED")
        return 1 if bad else 0
    finally:
        os.unlink(path)


if __name__ == "__main__":
    sys.exit(main())
