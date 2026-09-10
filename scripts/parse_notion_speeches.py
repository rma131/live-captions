"""Turn a Notion 'export with subpages' folder into a CSV for import_speeches.py.

    uv run python scripts/parse_notion_speeches.py "glossary/<export folder>" out.csv

Handles both shapes Notion produced for this event:
  A)  **1**  **EN**  text        segments split by ---
      **ES**  text
  B)  ### Segment 1
      **ENGLISH**
      > text
"""
import csv
import os
import re
import sys

LANGS = {"EN": "en", "ES": "es", "TR": "tr",
         "ENGLISH": "en", "ESPAÑOL": "es", "TÜRKÇE": "tr"}
NAME = {"en": "EN", "es": "ES", "tr": "TR"}

# Split on sentence end followed by a capital. Deliberately not a plain "." so
# that "8.000 km" and "≈ 2:50" survive intact.
SENT = re.compile(r"(?<=[.!?…])\s+(?=[A-ZÁÉÍÓÚÑÜÖÇĞŞİ«¿¡])")


def source_lang(text: str) -> str | None:
    m = re.search(r"Main language:\s*\*\*(\w+)\*\*", text)
    if m:
        return LANGS.get(m.group(1).upper())
    head = "\n".join(text.splitlines()[:6])
    m = re.search(r"\*\*(ENGLISH|ESPAÑOL|TÜRKÇE)", head)
    return LANGS.get(m.group(1).upper()) if m else None


def clean(s: str) -> str:
    s = re.sub(r"\*\((no translation|sin traducción)\)\*", "", s, flags=re.I)
    s = re.sub(r"[*_>]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip(" ·—-")


def parse_segments(text: str) -> list[dict]:
    """Return [{'en':..,'es':..,'tr':..}] for every segment found."""
    segs = []

    # shape B: ### Segment N, then **ENGLISH** / blockquote
    if re.search(r"^###\s+Segment", text, re.M):
        blocks = re.split(r"^###\s+Segment[^\n]*$", text, flags=re.M)[1:]
        for b in blocks:
            seg, cur = {}, None
            for line in b.splitlines():
                m = re.match(r"^\s*\*\*(ENGLISH|ESPAÑOL|TÜRKÇE)\*\*\s*$", line.strip())
                if m:
                    cur = LANGS[m.group(1).upper()]
                    continue
                if cur and line.strip().startswith(">"):
                    seg[cur] = (seg.get(cur, "") + " " + clean(line)).strip()
            if seg:
                segs.append(seg)
        return segs

    # shape A: inline **EN** / **ES** / **TR**, segments split by ---
    for block in re.split(r"^---+$", text, flags=re.M):
        if not re.search(r"\*\*(EN|ES|TR)\*\*", block):
            continue
        parts = re.split(r"\*\*(EN|ES|TR)\*\*", block)
        seg = {}
        for tag, body in zip(parts[1::2], parts[2::2]):
            seg[LANGS[tag]] = clean(body)
        if seg:
            segs.append(seg)
    return segs


def rows_for(seg: dict, src: str, who: str) -> list[dict]:
    """One row per sentence when all three languages agree on the count,
    otherwise one row for the whole segment. Misaligned splitting would pair a
    sentence with the wrong translation, which is worse than a long row."""
    if not all(seg.get(l) for l in ("en", "es", "tr")):
        return []
    parts = {l: SENT.split(seg[l]) for l in ("en", "es", "tr")}
    n = len(parts[src])
    if n > 1 and all(len(v) == n for v in parts.values()):
        return [{"Speaker": who, "Lang": src, "Said": parts[src][i],
                 "ES": parts["es"][i], "EN": parts["en"][i], "TR": parts["tr"][i]}
                for i in range(n)]
    return [{"Speaker": who, "Lang": src, "Said": seg[src],
             "ES": seg["es"], "EN": seg["en"], "TR": seg["tr"]}]


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    folder, out = sys.argv[1], sys.argv[2]
    all_rows = []
    for fn in sorted(os.listdir(folder)):
        if not fn.endswith(".md"):
            continue
        path = os.path.join(folder, fn)
        text = open(path, encoding="utf-8").read()
        title = fn.split(" 3d")[0].strip()
        if "solo espa" in fn or "sadece" in fn or "only " in fn.lower():
            print(f"  skip   {title}  (reading aid, duplicates another speech)")
            continue
        if "PENDING" in text:
            print(f"  skip   {title}  (marked PENDING, no text yet)")
            continue
        src = source_lang(text)
        if not src:
            print(f"  skip   {title}  (no main language found)")
            continue
        segs = parse_segments(text)
        rows = [r for s in segs for r in rows_for(s, src, title)]
        dropped = len(segs) - len({id(s) for s in segs if rows_for(s, src, title)})
        all_rows += rows
        print(f"  {NAME[src]}     {title}: {len(segs)} segments -> {len(rows)} rows")

    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, ["Speaker", "Lang", "Said", "ES", "EN", "TR"])
        w.writeheader()
        w.writerows(all_rows)
    print(f"\nwrote {len(all_rows)} rows to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
