# 006 — Tasks

**Spec:** [spec.md](spec.md) · **Plan:** [plan.md](plan.md)

## Phase 1 — Spec and speaker questions
- [x] Spec, plan, tasks; index updated; constitution amendment
- [ ] Send the open questions to the speaker; record answers in spec.md

## Phase 2 — Build
- [x] Columns sent by the server; pages build from them (wedding looks identical)
- [x] Single-feed mode: one channel, gate bypassed, `replay.py` takes 1-channel fixtures
- [x] Continuous LID with two candidates; detected language selects the column
- [x] Operator override `1`/`2`/`0` and flag `W`, loopback-only
- [x] `/band` caption strip
- [x] Opt-in audio recording on the transcript's clock
- [x] JSONL fields: detected language, override, time since switch; peak connections per minute
- [x] `test_single.py`; `test_guest.py` extended; all tests green

- [x] Mute-screen artwork made opt-in (privacy bug found in visual check)
- [x] Visual check: two-column projector, `/band` under a slide in an OBS-style layout, mute

## Phase 3 — Self-test
- [ ] Record a bilingual fixture on the headset, switching mid-paragraph while handling tools
- [x] First LID measurement written into spec.md (synthetic; real speech still to come)

## Phase 4 — Rehearsal
- [ ] Capture card + OBS path; full length; network drop; HDMI fallback swap

## Phase 5 — The talk
- [ ] Operate, flag, record

## Phase 6 — Review
- [ ] Numbers-first review; feeds 003's go/no-go and the case study
