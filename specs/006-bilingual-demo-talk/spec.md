# 006 — Bilingual demo talk

**Status:** accepted · **Created:** 2026-10-02 · **Branch:** `006-bilingual-demo-talk`
**Business half:** private repository, same number.

## Problem
At a small conference, one speaker demonstrates tools with their hands while
explaining. The room should be able to follow in English and French. The
speaker cannot hold a microphone or touch a keyboard, and what the room sees is
the speaker's own slides or laptop screen. Whether the speaker switches language
freely or keeps to one is not yet known.

## Why this spec, now
It is the unproven risk of 003 — continuous French/English language detection
on a single feed — at low stakes: one speaker, one room, a forgiving audience.
With the speaker's consent it produces a real bilingual recording, which is the
test set 003's go/no-go needs. It is also the first spec to go through the
spec-driven process from start to finish.

## Users and situation
- Attendees reading a caption band under the projected content, or their phones.
- A speaker with busy hands, wearing a headset.
- An operator at our laptop who can force the language, mute and flag errors.

## Requirements
1. Must caption one microphone and show English and French, whichever is spoken.
2. Must decide the source language automatically between `en-US` and `fr-FR`,
   with an operator override always available: force English, force French,
   back to automatic.
3. Must not cover the speaker's content: captions sit in a band below it.
4. Must keep mute, resilience, and the guest/control split from 000–001. Mute
   clears the band, the projector page and phones together.
5. Must let the operator mark a caption as wrong, timestamped in the log.
6. Must, when enabled and consented to, record the audio on the same clock as the
   transcript, for replay.
7. Must log per caption: detected language, whether an override was active,
   time since the previous language switch; and peak guest connections per minute.
8. Must leave the wedding mode exactly as it was.
9. Latency: as 000. Recovery after a language switch is measured, not assumed.

## Out of scope
More than two languages in this mode; installing anything on the speaker's
laptop; hosting; multiple rooms (that is 003).

## Acceptance
- [ ] Every existing `scripts/test_*.py` passes; the wedding fixture replays
      identically.
- [ ] `scripts/test_single.py` passes on a self-recorded bilingual fixture:
      finals land in the right column; override forces the column; flags are
      logged.
- [ ] `scripts/test_guest.py` proves `/band` is read-only and the override and
      flag controls refuse non-local clients.
- [ ] `scripts/test_reconnect.py` passes in single-feed mode.
- [ ] `/band` shown in OBS under a sample slide; `M` clears it with everything else.
- [ ] Rehearsal with the speaker: full talk length, network drop, swap to the
      fallback HDMI cable.
- [ ] Post-talk review with numbers: switch-detection accuracy, recovery time,
      flagged lines, latency, operator and setup hours, audience connections.

## Constitution check
Conflicts with "no language detection". This spec makes the scoped amendment:
no detection in per-microphone mode; in single-feed mode, continuous detection
with exactly two candidates is allowed, and only with the operator override
available. The Turkish reason stays on record. Also extends "one Python file"
with a second mode behind the two seams named in 003.

## Decisions
| Decision | Chosen | Rejected | Why |
|---|---|---|---|
| Gate in single-feed mode | Bypassed | Kept | With one channel the gate can only cut quiet speech |
| Language | Continuous LID + operator override `1`/`2`/`0` | LID alone; fixed only | The speaker's habits are unknown; override is the safety net and its use is data |
| Forcing a language | Rebuild the session via `Channel.restart` | Two parallel recognizers | ~1 s gap at a switch is acceptable; parallel sessions double cost and complexity |
| Captions over their screen | Their HDMI through a capture card into OBS; content scaled to ~85%, band below | Overlay window on their laptop; captions over content | Nothing installed on their machine; a hands-on demo must not be covered |
| Video-path risk | Direct HDMI fallback cable, rehearsed | — | Our laptop is now in their video path |
| Microphone | Headset; lavalier tested as alternative | Handheld | Hands are busy; a headset is closest to the mouth, away from tool noise |
| Columns | Sent by the server in the first status message | Hard-coded per page | One set of pages serves both modes |
| Testing without a speaker | Synthetic EN/fr-CA fixture via TTS (`make_tts_fixture.py`), test tool only | Wait for the self-test | Deterministic, available today; replaced by real speech in Phase 3 |
| Mute-screen artwork | Opt-in (`MUTE_LOGO`), and the page asks for it only when told | Serve whatever file exists | The wedding couple's monogram appeared on the mute screen in single mode — see Findings |
| Default languages for Montréal | `en-CA,fr-CA` in `.env.example` | `en-US,fr-FR` | Forced fr-CA kept English intelligible; fr-FR garbled it. Synthetic evidence only |

## Findings so far

**2026-10-02 — synthetic fixture, `test_single.py`** (TTS: en-US Jenny, fr-CA
Sylvie; four alternating sentences):

- **Finals: 4 of 4 in the right column**, each translated into the other
  language, with both `en-US,fr-FR` and `en-CA,fr-CA`.
- **Interims flicker at every switch.** The first half-second of French after
  English appears as English gibberish (`megna jettie`) before flipping to
  French; `ensuite` first showed as English. Finals were right; the speaker's own
  column is briefly wrong. Candidate mitigation, not built: hold interims for a
  moment after a detected switch. Decide on real speech.
- **A wrong override is costly.** English forced to `fr-FR`: "Today I am *Bing*
  to show you how to *shop and itel*". Forced to `fr-CA` the same sentence came
  through intact — the Canadian French model tolerates English, as Montréal
  speech requires. Synthetic evidence; confirm in Phase 3.
- **Vocabulary matters.** *la pierre* (the sharpening stone) came out as the
  name *Pierre*. The speaker's tool vocabulary belongs in the glossary.
- **Privacy bug found and fixed.** On the mute screen the page showed the
  wedding couple's monogram — the file was still on this machine (gitignored,
  never public) and the page loaded it whenever it existed, from browser cache
  even after the server stopped serving it. At a client's event, pressing M
  would have put their names on screen. Artwork is now opt-in and requested only
  when the server says so.

## Open questions — for the speaker
1. Do you switch between English and French, and how — by section, by sentence?
2. Which tools, brands and terms will you name? (→ glossary, both languages)
3. What do you project — slides, a camera on your hands, your laptop?
4. What connections does the venue have: projector input, cable, network?
5. May we record the audio, to evaluate and improve afterwards?
