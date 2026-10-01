# 000 — Wedding live captions

**Status:** done · **Built:** 3–5 September 2026 · **Ran:** 6 September 2026
**Retroactive spec.** Written after the fact from the original brief, the code
and the post-event review, so the decisions are on record.

## Problem
A trilingual wedding — Spanish, English, Turkish — where most guests understand
only one or two of the three. Speeches, toasts and a ceremony would be delivered
in one language and lost on two thirds of the room.

## Users and situation
~150 guests reading a projector from up to 15 m. Three microphones. One operator
who is also a guest and will not be at the keyboard most of the time. Human
interpreters on the other microphones during speeches. A tethered 5G uplink.
Three days to build it; it runs once.

## Requirements
1. Must show what is said in the two languages the speaker is not speaking.
2. Must let the operator clear the screen instantly, from anywhere that can reach
   the laptop, regardless of which window has focus.
3. Must survive the uplink dropping without crashing or blanking captions, and
   recover with nobody touching it.
4. Must spell the families' names correctly, including with Turkish case endings.
5. Must show a human-written translation whenever a speaker reads prepared text.
6. Must not machine-translate a human interpreter back into the language they
   are interpreting from.
7. Should be readable at 15 m: 48 px start, adjustable live.
8. Latency: first interim < 1.5 s, final < 3.5 s.

## Out of scope (at the time)
Phone clients, QR codes, guest-device fan-out, local router, TTS, local Whisper,
language detection, diarization, recording, database, auth, Docker, a test suite
beyond a replay script.

## Acceptance — met
- [x] Ran 4 h 38 m unattended, no restart, zero crashes.
- [x] 530 captions; none with an empty translation.
- [x] Mute used through the ceremony: 50 captions recognised and never shown.
- [x] 46 captions shown in a human translation.
- [x] 32 lines repaired by suffix-aware corrections.

## Decisions
| Decision | Chosen | Rejected | Why |
|---|---|---|---|
| Source language | Fixed per microphone, operator override | Automatic language ID | Azure LID failed on Turkish in testing; every fixed pair worked both ways |
| Where mute lives | Server, enforced in `Broadcaster.send` | Browser keybinding | The projector page will not have focus; one choke point means nothing can bypass it |
| Bleed control | Software energy gate, loudest above threshold wins | Faders on the desk | USB channel feeds are pre-fader; the gate is the only bleed control that exists |
| Losing channels | Fed silence | Fed nothing | Azure must hear the pause that ends an utterance or finals never arrive |
| Translations of partial sentences | Off; only the speaker's column updates live | On | Turkish is verb-final; a partial sentence can translate to the opposite of the finished one |
| Name corrections | Regex with a closed list of Turkish suffixes, suffix carried across | Whole-word rules | Turkish glues case endings onto names; whole-word rules miss exactly those mentions |
| Prepared text | Fuzzy match ≥ 0.78 on finished sentences | Exact match / none | Speakers paraphrase; human translation is the only answer to genderless Turkish pronouns |
| Interpreters | "Rounds": interpreter mics fill their own column only | Translate every mic | Re-translating an interpretation produces round-trip nonsense |
| Display | Three fixed columns, colour marks the speaker | Two rotating columns | A guest finds their language once and never looks elsewhere |
| Shape | One Python file, one HTML page | Framework, services | Three-day lifespan; smaller is more reliable |

## What went wrong — recorded for future specs
- One speech went in marked PENDING and ran on machine translation; its opening
  line mangled both families' surnames. → *No speech goes in without its text.*
- Only 46 of 108 prepared lines fired; speakers depart from scripts.
- Short names collided with common words and cost more than they returned.

See [`docs/case-study.md`](../../docs/case-study.md) for the full account.
