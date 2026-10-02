# 006 — Plan

**Spec:** [spec.md](spec.md) · **Status:** accepted

## Approach
Two seams in `captions.py`, as named in 003, and no others:

- **Source:** interface channels (wedding) · single feed (`MODE=single`).
- **Language:** fixed per channel (wedding) · continuous LID over `LANGS`
  (default `en-US,fr-FR`), with an operator override.

In single-feed mode there is one `Channel`. Its recognizer gets an
`AutoDetectSourceLanguageConfig` and `SpeechServiceConnection_LanguageIdMode =
Continuous`; targets are the two-letter codes of both languages. Each result's
detected language selects its column. The override rebuilds the session with a
fixed source through `Channel.restart`. `Pipeline` feeds the single channel
directly, without `Gate`.

The server sends the column list in the first status message, and the pages
build their columns from it. The wedding config sends ES/EN/TR.

A new `/band` page is the caption strip for an OBS browser source: transparent
background, both languages side by side, mute-aware, connected through the
read-only guest socket.

## Signal path at the venue
```
speaker laptop ─HDMI─▶ USB capture card ─▶ OBS on our laptop ─HDMI─▶ projector
                                              ├ their screen, scaled to ~85% height
                                              └ /band browser source below
```
Fallback: a direct HDMI cable, plugged in and ready to swap.

## Files touched
- `captions.py` — mode and languages config; LID path in `Channel.build`;
  detected language per result; gate bypass; override `1`/`2`/`0` and flag `W`
  over the operator socket and loopback-only HTTP; opt-in WAV tee in the capture
  callback; new JSONL fields; per-minute peak-connections log line; `/band`.
- `web/screen.html`, `web/guest.html` — columns from status.
- `web/band.html` — new.
- `scripts/replay.py` — 1-channel fixtures in single-feed mode.
- `scripts/test_single.py` — new.
- `scripts/test_guest.py` — `/band`, override and flag controls.
- `CLAUDE.md` — scoped amendment.

## Risks
1. A switch detected late: the first sentence after it is translated as the old
   language. Override and `W` exist for this; frequency is the measurement.
2. Our laptop in the speaker's video path. Fallback cable, rehearsed.
3. Tool noise on the mic. Headset; test the lavalier at rehearsal.
4. The detection add-on changes cost per hour slightly; recorded in the review.

## Verification
As in the spec's acceptance list. Wedding regression first, then single-feed
fixture, guest isolation, reconnect, a visual check in OBS, and the rehearsal.
