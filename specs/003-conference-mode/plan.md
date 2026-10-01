# 003 — Plan

**Spec:** [spec.md](spec.md) · **Status:** draft — not accepted until the spike passes

## Approach
Keep `captions.py` as the single process, now one per room. Add two seams and
no more:

- **Source:** interface channels (wedding) · single program feed (conference).
- **Language:** fixed per channel (wedding) · continuous LID with two candidates
  (conference).

A single-feed room needs no energy gate. The gate stays for the wedding mode.
Display gains a two-column layout and a same-language option. Guest and display
pages are served through a small HTTPS relay; capture and Azure calls stay on the
venue laptop.

## Phases
| Phase | When | Hours | Exit |
|---|---|---|---|
| 0 Discovery | Sep–Oct | ~20 | Answers to the open questions |
| 1 LID spike | Oct–Nov | ~40 | **Go/no-go** on measured switch recovery and French quality |
| 2 Build | Dec–Mar | ~160 | Tests, load test, wedding regression all green |
| 3 Pilot | Apr–Jun | ~40 | One real event, written review |
| 4 Readiness | Jul–Aug | ~50 | Rehearsal in real rooms, failover sheet |
| 5 Festival | late Aug | ~50 | Operated live |
| 6 Review | Sep | ~10 | Numbers-first review |

## Files touched
- `captions.py` — `Channel.build()` gains an `AutoDetectSourceLanguageConfig`
  path; `Pipeline` gains a single-feed source that bypasses `Gate`; per-room
  config via env. Reuse `Channel.feed`, `Resampler`, `Broadcaster`,
  `require_local`, the reconnect supervisor unchanged.
- `web/screen.html`, `web/guest.html` — two-column layout, same-language option.
- `scripts/eval_lid.py` (new) — replay a recorded panel, report switch recovery
  and per-language output. Built on `make_fixture.py` / `replay.py`.
- `scripts/test_guest.py` — extended to the hosted path.
- `scripts/load_test.py` (new) — 300 WebSocket clients.

## Risks
1. LID quality on Québec French and on switches. → the spike.
2. One operator for several rooms. → independent processes, failover sheet.
3. Venue WiFi. → the organisers' responsibility, in writing.
4. No clean feed in a room. → confirm desk outputs in discovery.

## Verification
Spike against real recordings; wedding fixture replays identically; all
`scripts/test_*.py` pass; load test; pilot review.
