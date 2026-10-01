# 005 — Local model evaluation

**Status:** proposed · **Created:** 2026-09-09

## Problem
Every event depends on an uplink to a cloud speech service. Cost is not the
issue (about $34 for a 4.5-hour event); the uplink is the largest operational
risk the system has. A local model would remove it.

## Known constraints
- Whisper translates **into English only**. It covers 2 of the 6 directions the
  wedding needed; the rest would require a separate translation stage.
- Meta's SeamlessStreaming does direct speech→text translation into 76 languages
  (Spanish, French, Turkish included), streaming, ~2 s latency, single stage.
  It is the architecture-compatible candidate.
- The current Linux laptop (i7-8650U, no GPU) cannot run either in real time for
  three streams. Evaluation belongs on Apple Silicon.

## Proposal
Measure before switching. `scripts/eval_asr.py` replays recorded fixtures through
a candidate engine offline and scores it against the event transcript, reporting
per-language accuracy and name accuracy separately. No live-path changes.

## Constitution check
"No local Whisper" and "STT and translation in one call" are both in
`CLAUDE.md`. An *evaluation* conflicts with neither. Adopting a local engine
would require amending both, with the evaluation's numbers as the reason.
