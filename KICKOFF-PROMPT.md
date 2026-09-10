# Session 1 kickoff prompt

Run this **on the MacBook**, in an empty repo directory containing `CLAUDE.md` and
`AUDIO-SETUP.md`. Have the L-8 plugged in via USB before you start.

---

Read `CLAUDE.md` and `AUDIO-SETUP.md` in the repo root before doing anything else.
Everything below assumes you have read both.

Context: **this ships on Sunday.** Live captions for a trilingual wedding. Three SM58s on
three channels of a Zoom LiveTrak L-8, each channel assigned a fixed language. Three Azure
speech-translation sessions, no language detection. It runs once and cannot be retried.

I would rather have a small system I have rehearsed twice than a good system I have run
once. Optimise accordingly.

## Phase 0 — Answer one question. Nothing else.

**Does macOS expose the L-8 as a multichannel input device?**

Write `scripts/list_devices.py` that prints every audio input device with its name, index,
max input channels, and default sample rate. Run it with the L-8 connected.

Then report:
- Does the L-8 appear with more than 2 input channels?
- How many, and at what sample rate?
- What exact name string does it report?

If it only exposes a stereo pair, **stop and tell me immediately.** The entire design
changes and I need to know tonight, not Saturday.

Do not write any other code until I have seen this output.

## Phase 1 — Environment and API check. Report before building.

1. Actual output, not assumptions: Python version, whether `uv` is present, and whether
   `azure-cognitiveservices-speech` installs cleanly on this Apple Silicon Mac. The arm64
   wheels have historically been a friction point.
2. From the current Azure Speech SDK Python docs, tell me concretely:
   - how to drive a recognizer from a **push audio stream** rather than a device, since we
     will be splitting channels ourselves
   - how to request **two target languages** on one translation recognizer
   - how to attach a **phrase list** for proper-noun biasing
   - how to receive **interim** (`recognizing`) results, not just final ones
   - what happens on network loss and whether reconnection is automatic
3. Flag anything in `CLAUDE.md` that is wrong, impossible, or will waste my time.

Stop and wait for me.

## Phase 2 — Single channel, end to end

Smallest thing that proves the pipeline. One Python file:

- Open the L-8, read **channel 1 only**, push it to one Azure translation session with
  source English, targets Spanish and Turkish.
- Print interim and final results to the terminal with timestamps and latency from speech
  onset.
- No server, no web page, no gate, no glossary.

Success: I talk into SM58 #1 and see Spanish and Turkish in the terminal within about two
seconds. Show me the output before continuing.

## Phase 3 — Three channels and the gate

- Read channels 1, 2 and 3. Three sessions, fixed source languages per `CLAUDE.md`.
- Per-channel RMS energy gate: only the loudest channel above a configurable threshold is
  forwarded. A few lines of numpy. Do not build or import a VAD model.
- `scripts/record_fixture.py`: records all three channels to a multichannel WAV so we can
  build regression fixtures at Friday's rehearsal.
- `scripts/replay.py`: feeds a multichannel WAV through the full pipeline at real-time
  speed. After this exists, no change should require me to talk into a microphone.

## Phase 4 — The display

- FastAPI + WebSocket on 127.0.0.1.
- `web/screen.html`: fullscreen, black, two columns, large text, interim dimmer than final.
- **Wire `M` for mute first and test it before building anything else on the page.**
- Then the remaining hotkeys from `CLAUDE.md`.

## Phase 5 — Only after 1–4 work

- Phrase list from `glossary/names.yaml`.
- Network-drop resilience, tested by actually disabling the network mid-sentence.
- Corner status indicator: connection state, active channel, override status.

## Configuration and portability rules

- **Select the audio device by name substring, never by index.** Indices change between
  reboots and when a projector is plugged in. Match on "LiveTrak" or "L-8".
- Everything environment-dependent goes in `.env`: Azure key, Azure region, device name
  substring, channel→language map, gate threshold, font size. I need to retune the gate
  threshold at the venue by editing one file, not by editing code.
- `.env` is gitignored. No keys in the repo, ever.
- Use `uv` with a lockfile. No macOS-only APIs. The code should run unmodified on Linux
  even though we will not develop there.

## Rules for this project

- Commit after every increment that works. I must be able to revert on Saturday night.
- If something fails to install or the API behaves unexpectedly, **stop and tell me.**
  Do not work around it silently and do not substitute a different library.
- Do not refactor. No provider abstractions. No config frameworks. This code has a
  three-day lifespan and I may need to read it on Sunday while nervous.
- At the end of each phase, tell me the single thing most likely to break on Sunday.
