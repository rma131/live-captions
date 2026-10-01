# CLAUDE.md — Live captions for multilingual events

## How work is specified — read this first

This file is the **constitution**: what must always be true. Everything else is
specified in [`specs/`](specs/README.md), one numbered directory per piece of
work, versioned with the code. Read `specs/README.md` at the start of a session
to see what exists, what is in progress, and why.

1. **No code without a spec.** Every change belongs to a spec in `specs/`. If none
   fits, write one first — a `proposed` spec can be a single paragraph.
2. **Cite the number.** Branches are named `NNN-short-name`; commit subjects start
   with `[NNN]`.
3. **Plans are drafts, specs are records.** Plan mode writes to `.plans/`
   (gitignored). Once approved, promote the plan into `specs/NNN-*/plan.md` by
   hand, after checking it contains nothing private.
4. **Tick tasks as you commit.** `tasks.md` is the progress record. Update it in
   the same commit as the work.
5. **Record decisions where they are made** — chosen, rejected, why — in the
   spec's Decisions table. Never only in chat or a commit message.
6. **Amend this file only through a spec.** A spec that conflicts with a rule here
   says so in its "Constitution check" and proposes the amendment.
7. **Nothing private in this repo.** No real names from an event, no transcript
   content, no client pricing or negotiation. Business material lives in the
   private business repository under the same spec number.

## Where this project is

**The wedding happened on 6 September 2026 and the system worked.** 4.5 hours
unattended, 530 captions, nothing crashed, mute did its job through the ceremony.
A post-event review is kept locally, outside this repository, alongside the
recordings and the transcript it draws on.

It has since moved from the MacBook to an Arch Linux machine. The deadline is gone;
what replaces it is a question — whether this is worth running again, for other
people, as a service. Until that question is answered, **treat every change as
though the code still has to survive a live event with no second take.**

The old brief said "three-day lifespan". That is no longer true, but do not read
its expiry as licence to rebuild. The design decisions below were paid for with a
real event and a real audience. Change them only with a reason as good.

## What this is

Live speech translation for events where two languages meet, usually with English
in the middle. Microphones in, translated text on a projector and on guests'
phones. Three fixed columns — **Español · English · Türkçe** — so a guest finds
their language once and never looks anywhere else.

Deliberately small: one Python file, two HTML pages, no framework, no database,
no build step.

## Critical design decision: no language detection

Azure's automatic language identification fails on Turkish. Every **fixed-pair**
translation works well in both directions (EN↔TR, EN↔ES, ES↔TR).

Source language is therefore never guessed. It is known by two independent means:

1. **Per-microphone routing (primary).** Each mic is assigned a language.
2. **Operator override (secondary).** Hotkeys force the source language.

Do not add language detection. Do not "improve" this with a detection fallback.

## Hardware

- **Sound Devices MixPre-10T** over USB. 12-in/4-out, class-compliant, no driver.
  Reached through **PipeWire's `pro-audio` node**, not the raw `hw:` device —
  `AUDIO_DEVICE_MATCH=MixPre-10T Pro`. 16 channels at 48 kHz, passed 1:1, mics on
  USB 1/2/3. Verified end to end on 9 September 2026.
  - It ships **two USB configurations**. Config 1 is UAC1 and offers 2 channels;
    config 2 is UAC2 and offers up to 12. Linux picks the first audio config it
    finds and lands on config 1, so the machine sees 2 inputs, not 12. It looks
    like a driver gap and is not one. Check `bNumConfigurations`, not
    `/proc/asound/cardN/stream0` — that only describes the *active* config.
  - **Do not take the card away from PipeWire.** Holding the stream open is
    load-bearing: the MixPre detaches from USB the moment internal recording
    starts if the host is not actively streaming.
  - **A host sample-rate change reboots the unit** and destroys a take in
    progress. Run `mixpre-session lock` before an event; `mixpre-session status`
    must read 48000 Hz with allowed rates `[ 48000 ]`.
  - The udev rule, WirePlumber drop-ins and `mixpre-*` tools that set all this
    up live in a separate repository of their own. Treat that as the source of
    truth for the interface and do not re-solve it here.
  - Card indices are **not stable**: the ALSA card number moved between reboots
    and the PortAudio index moved between two runs in one session. Always match
    by name.
- **MOTU 4pre** is the fallback — hybrid FireWire/USB, 6 in, 4 preamps. Whether
  Linux gives it multichannel over USB is **untested**.
- **3× Shure SM58** (cardioid) is the standard. Omni lavaliers exist for testing
  only; they have far worse off-axis rejection and the energy gate depends on
  level separation between channels.
- Previously a **Zoom LiveTrak L-8**, which needed a macOS driver. The recordings
  and the fixture tooling still refer to it.

**Re-derive the mic-to-USB channel map with `scripts/meters.py` at every venue.**
Never assume it. On the L-8, USB 1–2 were the stereo master and isolated channels
began at USB 3. Getting this wrong **fails silently**: a channel carrying a mix
sums every microphone, so it always wins the gate and the whole room is attributed
to one language, with captions that look entirely plausible.

## Architecture

```
mics → interface → USB multichannel → Mac/Linux
                                        ↓
                      per-channel energy gate (only loudest active
                      channel above threshold is forwarded)
                                        ↓
    3 Azure speech-translation sessions, one per channel,
    each with a FIXED source language and 2 target languages
                                        ↓
                 local FastAPI + WebSocket
                        ↓                    ↓
        projector page (operator)     guest phones (read-only)
```

## The energy gate — load-bearing, not an optimisation

**Per-channel USB signals are pre-fader.** Pulling a fader down does not mute that
channel over USB. A mic can be silent in the room and fully audible to Azure. The
software gate is the only bleed control there is.

- Short-window RMS per channel; loudest above an absolute threshold wins.
- Non-winning channels are fed **silence, not nothing** — Azure must keep
  receiving audio in real time or it never sees the pause that ends an utterance
  and the final result never arrives.
- `HOLD_S` keeps a winner through mid-sentence breaths.
- Threshold is tunable live from the keyboard, at the venue, in ten seconds.

Keep this simple. A few lines of numpy. Do not build a VAD model.

## Operator controls

- `M` — mute. Stops output and clears every screen, projector and phones alike.
  **The most important feature in the project. Make it impossible to get wrong.**
- `C` — clear · `0` — release round · `1`/`2`/`3` — set the speaking mic
- `[` / `]` — gate down / up · `+` / `-` — font size · `L` — light/dark
- `R` — reconnect all sessions · `?` — key bindings

Mute lives on the **server**, and `Broadcaster.send` enforces it at the single
point every message passes through. Keep it there. Anything that can reach
localhost can mute; nothing else can.

## Guest phones

`BIND_HOST=0.0.0.0` serves `/guest` to the venue network. This was out of scope
for the wedding and is in scope now.

Opening the server to the room puts it in front of every guest, so the split is
enforced on the server, never in the page:

- `/ws/guest` never reads what a client sends.
- `/ws` refuses non-local clients.
- Every control endpoint refuses anything that is not loopback.

`scripts/test_guest.py` proves this over a real LAN address. If you add a control,
add it behind `require_local` and extend that test.

## Accuracy — where the real value is

Machine translation is the commodity. These are not:

- `glossary/names.yaml` — phrase list biasing what Azure **hears**.
- `corrections:` — substitutions fixing what Azure **writes**, Turkish-suffix
  aware. Turkish glues case endings onto names, so whole-word rules miss exactly
  the mentions that matter most.
- `glossary/speeches.yaml` — human translations that override the machine. The
  only human-checked output in the system, and the only real answer to Turkish
  pronouns, which have no gender to translate from.

**No speech goes in as PENDING.** One missing text at the wedding cost the most
emotional speech of the day its human translation, and mangled both family
surnames in its opening line.

## Resilience — non-negotiable

The uplink will drop. When it does: do not crash, show a reconnecting indicator,
retry with backoff per session, **leave existing captions on screen**, recover
without the operator. Tested by `scripts/test_reconnect.py`.

## Linux notes

- Rebuild the venv per platform; `uv sync` handles it.
- **Detach SDK callbacks before tearing a recognizer down** (`Channel._detach`).
  Without it the process aborts at exit with "FATAL: exception not rethrown",
  exit 134, after a clean run. The SDK calls back from native threads and one
  firing against a finalizing interpreter crosses a noexcept frame.
- A copy from macOS onto a non-HFS volume writes `._*` sidecars beside every
  file, including inside `.git/objects/pack/`, which breaks every git command.

## Latency budget

| Metric | Target |
|---|---|
| First interim caption after speech onset | < 1.5 s |
| Finalized caption | < 3.5 s |

## Still out of scope

No QR-code onboarding. No local router. No TTS. No local Whisper (evaluation is
spec 005). No language detection (conference mode, spec 003, proposes a scoped
amendment). No diarization. No auth. No Docker. No database. No test suite beyond
the scripts in `scripts/`.

If you find yourself building any of the above, stop and ask.

## Working style

- Commit after every increment that works.
- If a dependency fails or the API misbehaves, **stop and tell me**. Do not
  silently work around it or substitute a library.
- Do not refactor for its own sake. No provider abstractions.
- Verify against `scripts/replay.py` and a fixture, not by talking into a mic.
- After each phase, say the single thing most likely to break.
