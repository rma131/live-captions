"""Check that output corrections behave.

Uses its own fixture, not glossary/names.yaml — that file holds the real family
names, is gitignored, and changes whenever someone spots a new mishearing.

    uv run python scripts/test_corrections.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from captions import apply_corrections, load_glossary  # noqa: E402

FIXTURE = """
couple:
  - Marisol
  - Kerem
corrections:
  Marysol: Marisol
  Kerim: Kerem
  Alcazar: Alcázar
"""

CASES = [
    # plain substitutions
    ("Kerim y Marysol se casan hoy.", "Kerem y Marisol se casan hoy."),
    ("MARYSOL", "Marisol"),
    ("Marisol Alcazar", "Marisol Alcázar"),
    # Turkish glues case endings onto names, so a whole-word rule would miss
    # exactly the mentions that matter most. The ending must be carried across.
    ("Marysolu çok seviyorum.", "Marisolu çok seviyorum."),
    ("Marysol'u gördüm.", "Marisol'u gördüm."),
    ("Marysol'un ailesi", "Marisol'un ailesi"),
    ("Marysoldan bahsediyorum", "Marisoldan bahsediyorum"),
    ("Kerimle konuştum", "Keremle konuştum"),
    ("Kerimi gördüm", "Keremi gördüm"),
    # an English plural is NOT a Turkish ending and must not match
    ("Marysols", "Marysols"),
    # already correct text is left alone
    ("Marisol and Kerem.", "Marisol and Kerem."),
]


def main() -> int:
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False,
                                     encoding="utf-8") as fh:
        fh.write(FIXTURE)
        path = fh.name
    try:
        phrases, rules = load_glossary(path)
        print(f"{len(phrases)} phrases, {len(rules)} correction rules\n")
        bad = 0
        for src, want in CASES:
            got = apply_corrections(src, rules)
            bad += got != want
            print(f"{'PASS' if got == want else 'FAIL'}  {src!r} -> {got!r}"
                  + ("" if got == want else f"   want {want!r}"))
        print("\nALL CORRECTION TESTS PASSED" if not bad else f"\n{bad} FAILED")
        return 1 if bad else 0
    finally:
        os.unlink(path)


if __name__ == "__main__":
    sys.exit(main())
