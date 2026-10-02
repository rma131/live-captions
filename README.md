# Live captions for multilingual events

Real-time speech translation for events where two languages meet, usually with
English in the middle. Microphones feed one laptop; a projector shows every
sentence in all three languages at once, and guests can read along on their own
phones.

Built in three days for a trilingual wedding, where it ran **4h 38m unattended,
produced 530 captions and did not crash**. What worked, what did not, and what it
cost: [docs/case-study.md](docs/case-study.md).

It is deliberately small: one Python file, two HTML pages, no framework, no
database, no build step.

```
3× SM58 → multichannel interface → USB → one Python process
                                            ↓
                    per-channel energy gate (loudest mic wins)
                                            ↓
            3 Azure speech-translation sessions, fixed source language
                                            ↓
                      FastAPI + WebSocket
                    ↓                      ↓
          fullscreen page          guests' own phones
            (projector)              (read-only)
```

Tested against a Sound Devices MixPre-10T and a Zoom LiveTrak L-8. Any interface
that presents its microphones as separate USB channels should work — but see the
channel-map warning below, because that is where the time goes.

## Why there is no language detection

Azure's automatic language identification is unreliable on Turkish. Every
**fixed-pair** translation works well in both directions, so the source language
is never guessed: each microphone is permanently assigned a language, and the
operator can override the round from the keyboard.

## The screen

Three fixed columns — **Español · English · Türkçe**, always in that order, so a
guest finds their language once and never looks anywhere else. The column of the
language being spoken is marked in gold; nothing changes size or position when
the speaker changes.

Interim results update only the speaker's own column. Translations settle once,
when the sentence finishes — Turkish puts the verb and its negation last, so a
partial Turkish sentence can translate to the opposite of the finished one.

## One speaker, two languages — `MODE=single`

For a talk or demo by one speaker who moves between English and French: one
microphone (a headset, if their hands are busy), no gate, and the source
language detected continuously between exactly two candidates. The operator can
always overrule it — `1` / `2` force a language, `0` returns to automatic — and
`W` marks the last caption as wrong in the log, which turns the transcript into
labelled data for the review.

Detection is allowed only here. The per-microphone mode keeps the original rule,
because detection failed on Turkish ([spec 006](specs/006-bilingual-demo-talk/spec.md)).

**Captions under the speaker's own screen.** `/band` is a caption strip for an
OBS browser source: their laptop goes through a capture card into OBS, their
content is scaled to ~85% of the height, and the band sits in the space below —
never over what they are demonstrating. Options: `?fs=34&lines=2&bg=black&light=1`.
Keep a direct HDMI cable ready as a fallback; our laptop is now in their video
path.

`RECORD_AUDIO=1` writes the captured feed as a WAV on the transcript's clock —
already in `replay.py`'s format — so a recorded talk is a regression fixture.
Only with the speaker's consent.

## Interpretation rounds

The event uses live human interpreters, not machine translation alone: a speech
is delivered once, then interpreted into the other two languages by people on the
other microphones.

Press `1`, `2` or `3` and that microphone becomes the speaker. The other two are
then treated as interpreters: their words fill their own column and are **never
machine-translated again**, because re-translating an interpretation back into
the language it came from produces round-trip nonsense on top of the original.
`0` returns to translating every channel.

## Operator keys

| Key | Does |
|---|---|
| `M` | mute — clears the screen instantly |
| `C` | clear captions |
| `1` `2` `3` | start a round with that mic as the speaker |
| `0` | free-for-all, translate every channel |
| `[` `]` | lower / raise the energy gate live |
| `+` `-` | font size |
| `R` | reconnect all speech sessions |
| `?` | show this list |

## Guests' phones

`BIND_HOST=0.0.0.0` also serves `/guest` to the venue network: one language at a
time, chosen on the phone and remembered, in the guest's own thumb.

The same process serves mute, so the separation is enforced on the server rather
than in the page. `/ws/guest` never reads what a client sends; `/ws` refuses
non-local clients; every control endpoint refuses anything that is not loopback.
A guest with the browser console open cannot mute the screen, change the round or
touch the gate.

Mute needed no new enforcement — `Broadcaster.send` already drops captions before
fan-out, so phones were covered the moment they became clients.

Default is `127.0.0.1`. Nothing is exposed until you say so.

Mute, rounds, gate and reconnect are also plain HTTP endpoints
(`/mute`, `/round/2`, `/gate/down`, `/reconnect`) so they work when the page does
not have keyboard focus — the display is fullscreen on a projector, and the
operator's attention is not.

## Getting it running

```bash
uv sync
cp .env.example .env                 # add Azure key + region
cp glossary/names.example.yaml    glossary/names.yaml
cp glossary/speeches.example.yaml glossary/speeches.yaml

uv run python scripts/list_devices.py   # is the interface multichannel?
uv run python scripts/meters.py         # tap each mic, confirm the channel
uv run python captions.py               # then open http://127.0.0.1:8000/
```

Azure needs the **Standard (S0)** tier. Free F0 allows one concurrent
recognition request and this runs three.

## Hardware notes that cost time to discover

- Per-channel USB feeds are **pre-fader and pre-EQ**. Pulling a fader down does
  not mute that channel over USB, so the software energy gate is the only bleed
  control there is.
- **Re-derive the mic-to-USB channel map at every venue** with `meters.py`. On the
  L-8, USB 1–2 were the stereo master mix and individual channels started at USB
  3, so reading 1/2/3 got you master-L, master-R and mic 1. Because a master mix
  sums every microphone it always wins the gate and the whole room is attributed
  to one language. **It fails silently, with captions that look plausible.**
- The **MixPre-10T** ships two USB configurations. Config 1 is UAC1 and offers 2
  channels; config 2 is UAC2 and offers 12. Linux takes the first audio config it
  finds, lands on config 1, and shows 2 inputs instead of 12 — which looks like a
  missing driver and is not one. Fix with a write to `bConfigurationValue`, and
  confirm with `grep -c 'Channels: 12' /proc/asound/card1/stream0`.
- On Linux, **detach the SDK's event handlers before tearing a recognizer down**.
  Otherwise the process aborts at exit with "FATAL: exception not rethrown" after
  an otherwise clean run: the SDK calls back from native threads, and one firing
  against a finalizing interpreter crosses a noexcept frame inside the SDK.
- 48 kHz only; audio is low-passed and decimated 3:1 to the 16 kHz Azure wants.

## Accuracy tooling

| File | Purpose |
|---|---|
| `glossary/names.yaml` | phrase list biasing what Azure **hears** |
| `glossary/names.yaml` → `corrections:` | substitutions fixing what Azure **writes** |
| `glossary/speeches.yaml` | human translations that override the machine |
| `glossary/IMPORT-PROMPT.md` | prompt turning a speech document into importable rows |

Corrections are Turkish-suffix aware: a rule for `Kristina` also fixes
`Kristinayı` and `Kristina'nın`, keeping the ending. Turkish glues case endings
onto names, so whole-word rules miss exactly the mentions that matter most.

Prepared lines are the only human-checked output in the system, and the only real
answer to Turkish pronouns: Turkish has no grammatical gender, so live
translation must guess "he" or "she". A prepared line never guesses.

## Tools

```bash
uv run python scripts/demo_captions.py        # drive the page with no mics, no Azure
uv run python scripts/record_fixture.py f.wav # capture 3 channels at rehearsal
uv run python scripts/replay.py f.wav         # replay through the full pipeline
uv run python scripts/review.py               # what went wrong, and what to fix
uv run python scripts/import_speeches.py --csv speeches.csv
uv run python scripts/make_fixture.py SESSION out.wav --from 16:11:00 --to 17:05:00
```

`make_fixture.py` turns a multitrack recorder session — three mono 24-bit files —
into the one interleaved fixture `replay.py` wants, so a real event becomes a
regression test made of real speech.

`replay.py` exists so that after the first rehearsal, no change requires anyone
to talk into a microphone.

## Tests

```bash
for t in mute rounds corrections script_match reconnect guest single; do
  uv run python scripts/test_$t.py
done
```

`test_reconnect.py` kills live Azure sessions and proves they come back; run it
with `MODE=single` too. `test_single.py` replays a synthetic English/Québec
French fixture (`make_tts_fixture.py` builds it — a test tool, not a product
feature) and checks each sentence lands in its own column.
`test_guest.py` checks the guest split over a real LAN address, because that is
the only way `request.client.host` is anything but `127.0.0.1` — a mock would
pass while the real thing let a phone mute the room.
`test_mute.py` drives a real WebSocket against a real server — an earlier version
used a fake client and therefore did not notice that uvicorn had no WebSocket
library installed at all.

## Resilience

Azure cancels a session when the uplink drops and does not bring it back, so each
channel rebuilds its own recognizer with exponential backoff, independently. A
supervisor thread does the rebuilding, off both the audio path and the SDK
callback threads, so a hung teardown cannot wedge capture. Captions stay on
screen throughout.

## Privacy

Real names, speeches, recordings and transcripts are gitignored and never
committed. `glossary/*.example.yaml` shows the shape; fill in your own copies.

A transcript contains **everything said at the event**, and a glossary contains
the names of everyone in the room. Keep both off shared storage, and never attach
either to a bug report — see [CONTRIBUTING.md](CONTRIBUTING.md).

This repository has no history from the event it was built for. That history
exists, privately, and is deliberately not published.

## Licence

MIT.
