# 003 — Conference mode

**Status:** draft · **Created:** 2026-09-14 · **Branch:** —
**Business half:** private repository, same number.

## Problem
A bilingual (French/English) arts-and-technology forum in Montréal runs three
days of talks, panels and workshops across more than one room, and currently
uses a commercial AI captioning service. The organisers find it expensive for a
once-a-year event *and* still carry the operational work themselves. They want
captions tailored to the event as an accessibility experience.

The wedding system (000) does most of what this needs. Its routing model does
not: a panel is a moderator and several panelists switching between French and
English mid-conversation, with no microphone to pin a language to.

## Users and situation
- Attendees: several hundred per room, francophone and anglophone, reading on
  their own phones and, where available, on a room screen.
- Deaf and hard-of-hearing attendees who need **same-language** captions.
- An operator per event (not necessarily per room) who fixes names and can mute.
- The venue's AV team, who provide one program feed per room.
- 100+ speakers whose names, works and terms of art appear on screen.

## Requirements
1. Must caption a single program feed per room where the source language changes
   between French and English without operator action.
2. Must show French and English columns; same-language captions available.
3. Must run several rooms in parallel, independently — one failing does not
   affect the others.
4. Must serve guest phones over HTTPS at a stable, trustworthy URL per room.
   Audio still never leaves the venue except to the speech service.
5. Must keep mute, resilience and the guest/control split from 000/001 intact.
6. Must load a per-session glossary (speakers, works) in both languages.
7. Must hold 300 concurrent guest connections per room.
8. Should support a third language (Spanish) as an option.
9. Must keep the wedding mode working unchanged.
10. Latency: same budget as 000; language-switch recovery measured separately.

## Out of scope
Dozens of languages; attendee accounts; a CMS for the programme; recording;
diarization; anything that requires the venue to install software.

## Acceptance
- [ ] Spike: on real recordings of past bilingual panels, French↔English switch
      recovery < ~3 s and French quality acceptable to a francophone reviewer.
- [ ] Wedding fixture still replays identically.
- [ ] 300-socket load test passes on one room.
- [ ] `test_guest.py` passes against the hosted HTTPS path.
- [ ] A real pilot event, one room, with a written review.
- [ ] Rehearsal in the real rooms on the real feeds before the festival.

## Constitution check
**Conflicts with "no language detection".** That rule was earned on Turkish,
where Azure's identification failed. FR/EN with two candidates is a different,
easier problem — but unproven. Proposed amendment, *only if the spike passes*:
scope the rule to the per-microphone mode; allow continuous LID with exactly two
candidates in conference mode. Until then the rule stands.

Also conflicts with "one Python file". Accept a second routing mode, behind two
seams only: where audio comes from, and how language is decided. No provider
abstraction.

## Decisions
| Decision | Chosen | Rejected | Why |
|---|---|---|---|
| Routing | Continuous LID, candidates `fr-FR`/`en-US` | Per-language mics | Panels switch mid-conversation; there is no mic to pin |
| Proceed? | Spike first, go/no-go | Build then test | LID is the one unproven risk; retire it before building on it |
| Capture | Local, one feed per room | Browser / cloud capture | Clean feeds exist at a venue; audio stays local |
| Guest delivery | Small hosted HTTPS relay for display/guest only | LAN IP on a QR code | A raw IP looks like phishing to a festival audience |
| Scope | Two languages done well, third optional | "Dozens" | That is the incumbent's ground; quality on names and Québec French is the differentiator |

## Open questions — for the organisers
1. How many rooms in parallel, how many hours a day?
2. Which languages and directions beyond FR↔EN?
3. Phones only, or room screens too?
4. Who operates on the day; what desk and outputs per room?
5. Can the venue WiFi carry several hundred phones per room?
6. Do they want the transcripts afterwards, and for what?

## What breaks first
The language switch. A francophone moderator asks, an anglophone panelist
answers, and the first sentence of the answer is mistranslated *as if* French.
How long, and how often, decides whether this spec proceeds.
