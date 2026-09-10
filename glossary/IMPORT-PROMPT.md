# Turning a speech document into Notion rows

Paste the prompt below into Claude or ChatGPT, fill in the two bracketed blocks,
then paste the speaker's text underneath it. You get CSV back. Import that CSV
into Notion (`/csv` → Import → CSV), or append it to the existing table.

Then: `uv run python scripts/import_speeches.py --csv <file>.csv`

Do this **once per speaker**. Mixing several speakers in one run makes the model
lose track of who "I" and "she" refer to, which is the whole point of the
context block.

---

## The prompt — copy from here

> You are preparing subtitles for a trilingual wedding. I will give you one
> speaker's written speech. Convert it into CSV rows for a live-captioning
> system.
>
> **Who is who** (use this to get every pronoun and gender right):
>
> ```
> [FILL IN, e.g.:
>  Marisol Alcázar Aranda — the bride, she/her, Ecuadorian
>  Kerem Yılmaz — the groom, he/him, Turkish
>  Javier — Marisol's father, he/him
>  Gül — Kerem's mother, she/her
>  This speaker is: Javier, the bride's father, speaking Spanish]
> ```
>
> **Family relations matter more than you expect.** Spanish and Turkish both have
> precise kinship words that English lacks, and getting them wrong is noticed by
> exactly the people being thanked. Say who is related to whom and how, and
> whether the speaker is male or female — Turkish `baldız` (wife's sister) and
> `bacanak` (wife's sister's husband) are only correct from a man's point of
> view. Also flag when one name covers several people.
>
> ```
> [FILL IN, e.g.:
>  Rosa and Pilar — Marisol's sisters, so the speaker's cuñadas
>  Emre — TWO different men, both called Emre, married to Rosa and Pilar]
> ```
>
> **Names must be spelled exactly like this** wherever they appear, in all three
> languages:
>
> ```
> [FILL IN from glossary/names.yaml, e.g.:
>  Marisol, Kerem, Yılmaz, Alcázar, Aranda, Gül, Mustafa, Javier]
> ```
>
> **Output format.** CSV, nothing else — no preamble, no explanation, no code
> fence. Exactly this header row, then one row per sentence:
>
> ```
> Speaker,Lang,Said,ES,EN,TR
> ```
>
> - `Speaker` — the speaker's name, the same on every row.
> - `Lang` — `es`, `en` or `tr`: the language this speech is delivered in.
> - `Said` — the sentence in the delivery language.
> - `ES`, `EN`, `TR` — the same sentence in Spanish, English and Turkish. The
>   column matching `Lang` repeats `Said` exactly.
>
> **Rules, in order of importance:**
>
> 1. **One sentence per row.** Never put two sentences in one row. If the
>    original has a long sentence with several clauses, split it into two rows at
>    a natural pause. Short sentences caption far better than long ones.
> 2. **`Said` must be what the person will actually say out loud**, in their own
>    words. Keep their phrasing, contractions and rhythm. Do not tidy their
>    grammar, do not make it more formal, do not summarise. A rewritten sentence
>    will not match what the microphone hears.
> 3. **Write numbers, dates and times as digits** (`25`, `2019`), because that is
>    how speech recognition writes them.
> 4. **Get the pronouns right using the context block.** Turkish has no
>    grammatical gender — `o` is he, she and it — so when a Turkish line becomes
>    English or Spanish you must decide from context whether it is Marisol or
>    Kerem, and use the right gender. This is the single most valuable thing you
>    are doing here.
> 5. **Translate naturally, not literally.** These are read aloud in the room by
>    people who love the couple. Warmth beats fidelity to word order. Keep
>    kinship terms natural to the language (`anneanne`, `abuelita`).
> 6. Keep every name in the exact spelling given above, including accents and
>    Turkish characters (ö, ü, ı, ş, ç, ğ).
> 7. Quote any field containing a comma with double quotes. Use UTF-8.
> 8. Drop stage directions, headings and anything not spoken aloud.

## Copy to here

---

## After you get the CSV

1. Check the row count roughly matches the number of sentences in the document.
2. **Have a native speaker read the Turkish and the Spanish.** This file exists
   precisely because it is human-quality; an unreviewed LLM translation in it is
   no better than the machine translation it replaces, and it is trusted more.
3. Import it, then run `scripts/import_speeches.py`, which will tell you about
   any row that is malformed or holds more than one sentence.
4. Check the pronouns specifically. That is the failure the live system cannot
   fix by itself.

## What not to bother putting in

- Anything nobody will read aloud.
- Long paragraphs — they will never match. Split or leave them out; unmatched
  speech falls through to live translation and loses nothing.
- Impromptu toasts. You cannot script those, and the system handles them fine.
