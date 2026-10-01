# 001 — Linux migration and hardware

**Status:** done · **Completed:** 9 September 2026
**Retroactive spec.**

## Problem
The system was built on a MacBook with a Zoom LiveTrak L-8 and had to move to an
Arch Linux laptop with different interfaces, without losing anything that made it
work at the event.

## Requirements
1. Must run, pass every test, and replay recorded audio on Linux.
2. Must capture three discrete microphone channels from an interface available
   on this machine.
3. Must keep every behaviour from 000 unchanged.
4. Should turn the event's recordings into a regression test.
5. Should prototype captions on guests' own phones (reversing 000's scope).

## Acceptance — met
- [x] Repo readable again; `git fsck` clean.
- [x] All test scripts pass; `replay.py` exits 0.
- [x] MixPre-10T captures 12 channels at 48 kHz; mics measured on USB 1/2/3.
- [x] Live end to end: three SM58s → MixPre → Azure → projector and phones.
- [x] Two minutes of the real speech block replay with all prepared lines firing.
- [x] Guest phones read captions over the LAN and cannot reach any control.

## Decisions
| Decision | Chosen | Rejected | Why |
|---|---|---|---|
| macOS `._*` sidecars, mode 0755 noise | Delete sidecars, `core.fileMode=false` | chmod everything back | Nothing is executed directly; the exec bit means nothing here |
| Exit-time SIGABRT (exit 134) on Linux | Detach SDK callbacks before teardown | Ignore it; `os._exit` | Bisected to callbacks firing into a finalizing interpreter; detaching also stopped a dying recognizer marking its replacement down |
| Recordings | Moved out of the repo, pointer kept locally | Delete / commit | 9 GB of private audio is an evaluation set, not source |
| Fixture from recordings | Separate `make_fixture.py` (24-bit mono ×3 → 16-bit 3ch) | Widen `replay.py` | Keep the live path untouched |
| MixPre 2 vs 12 channels | USB configuration 2 (UAC2) | A driver | Linux picks config 1 (UAC1) first; not a driver gap |
| Capture path | PipeWire `pro-audio` node (`MixPre-10T Pro`) | Raw `hw:`, taking the card from PipeWire | PipeWire holding the stream open stops the unit detaching on record |
| Guest phones | `/guest` + `/ws/guest` read-only; controls loopback-only | Reuse the operator socket | Same process serves mute; a guest must not be able to reach it |
| Column overflow over labels | `overflow:hidden` + fade mask | Shrink font / fewer lines | The label is what a guest navigates by |

## Constitution amendments made
- Guest phones moved from out of scope to in scope.
- Hardware section rewritten for the MixPre and PipeWire.

## Measured, for later specs
Room tone 0.001–0.002 RMS; close speech 0.015–0.215; bleed 0.002–0.008;
separation 18–35 dB with SM58s. Gate 0.010 sits in the gap.
