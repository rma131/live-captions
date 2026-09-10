# Audio setup — Zoom LiveTrak L-8 + 3× SM58

Print this. Take it to the venue.

---

## Channel assignment

| Channel | Mic | Language | Screen pane | Operator key | Tape colour |
|---|---|---|---|---|---|
| 1 | SM58 #1 | **Spanish** | left | `1` | (choose) |
| 2 | SM58 #2 | **English** | centre | `2` | (choose) |
| 3 | SM58 #3 | **Turkish** | right | `3` | (choose) |

Mic number, operator key and on-screen pane are all the same number, left to right.
**Re-tape the handles if they were labelled under the old order.**

Tape the handles. Tell the MC and every speaker which mic is theirs. Write the assignment
on a card and leave it at the desk.

If someone speaks the wrong language into the wrong mic, the operator presses the override
key. It is not a disaster.

---

## Getting the L-8 into interface mode

This is not obvious and nothing works without it.

1. **Download and install the Zoom L-8 driver** from zoomcorp.com. Required on **macOS as
   well as Windows** — only iOS is class-compliant without it. Do this before Sunday.
2. Put the L-8 in **Mixer mode**.
3. Press **function button 8, labelled Audio I/F**.
4. The computer should now see **12 inputs**. If it sees 2, you missed a step above.

## CRITICAL: individual channels are pre-fader and pre-EQ

The per-channel USB signals (inputs 1–8) are taken **directly after the preamp**, before
the channel strip and fader. Only the stereo master mix is post-fader.

Two consequences you must design around:

- **Pulling a fader down does NOT mute that channel over USB.** You can mute a mic in the
  room while Azure still hears it at full level. Bleed control is entirely the software
  energy gate. There is no hardware backup.
- **EQ, the 75 Hz highpass and compression do not reach the USB channels.** They are part
  of the channel strip. The preamp gain knob is the only per-channel control that affects
  what Azure hears. If rumble is a problem, filter it in software.

Do not fight this. It is the correct trade: separate channels are worth more than channel
strip processing, and both the gate and a highpass are a few lines of numpy.

## L-8 configuration

- **Sample rate: 48 kHz.** 96 kHz is not supported over USB at all, and disables the
  effects, EQ and overdub as well.
- **Phantom power: OFF.** SM58s are dynamic and don't need it.
- **Gain:** the only setting that matters for recognition. Set so a normal speaking voice
  peaks around −12 to −6 dBFS. Have someone talk at realistic volume, not test-one-two
  volume. People get louder when nervous and louder again when drunk. Leave headroom.
- **EQ / highpass / compression:** set these for the room if you like, but understand they
  affect only what guests hear through the PA, not what Azure receives.
- **Save a scene.** The L-8 stores up to 7 scenes. Once the soundcheck is right, save it,
  so a knock or an accidental knob turn is one button press away from recovery.

## Routing

- **Master out → the venue's Bose PA.** This is what guests hear, post-fader, with EQ.
- **USB inputs 1/2/3 → the Mac.** This is what Azure hears, pre-fader, raw.
- These are independent. Music, sound pads and DJ playback must not be on channels 1–3.
  If music runs through the L-8, put it on channels 7–8 and never read those in software.

## Microphone technique — tell every speaker

- Hold it at **chin height, 5–10 cm from the mouth.** Not at chest height. Not at
  arm's length. This is the biggest quality lever available and it costs nothing.
- Point the mic **away from the Bose speakers.** The SM58 is cardioid, so its dead spot is
  directly behind it. Rejecting the PA prevents both feedback and recognition errors.
- Don't cup the head of the mic. It wrecks the polar pattern.
- Speak in short sentences, pause about two seconds at paragraph breaks.

## Speaker placement

Position the Bose speakers so they are **behind or beside** the microphones, never in
front of them pointing back. If the PA is firing into the mics you will get both feedback
and garbage transcription.

---

## Venue checklist — Sunday

- [ ] Arrive with 90 minutes of buffer.
- [ ] Power: L-8, Mac, hotspot. Extension lead. Tape the cables down.
- [ ] Zoom driver installed; L-8 in Mixer mode with Audio I/F (function button 8) engaged.
- [ ] macOS sees 12 inputs, not 2. Check before anything else.
- [ ] Confirm channels 1/2/3 map to the mics you think they do. Tap each capsule and
      watch which meter moves. Do not assume.
- [ ] Gain staging with a real voice at real volume through the real PA.
- [ ] Walk to the furthest table and read the projector. Increase font until legible.
- [ ] Confirm the hotspot has signal *in that room*, not in the car park.
- [ ] Tune the energy-gate threshold with all three mics open and ambient room noise.
      Remember: faders do not affect what Azure hears. The gate is your only bleed control.
- [ ] Save the L-8 scene once the soundcheck is right.
- [ ] Test the mute key. Then test it again.
- [ ] Agree a hand signal with the MC for "mute the captions."
- [ ] Freeze all configuration. Change nothing after this point.

## If something goes wrong on the day

1. Bad output → hit mute. Nobody will notice or care.
2. Crash → close the laptop. The pre-translated slides and printed programs carry the day.
3. Do not debug during a speech. You are a guest at this wedding.

## Fallbacks, in order

1. Live captions (this system)
2. Pre-translated speech slides, advanced by a human
3. Printed bilingual programs
4. Bilingual guests quietly interpreting at the Turkish-only and Spanish-only tables

Number 4 works with no electricity and has never failed at any wedding in history.
Make sure those people know they're on standby.

---

## VERIFIED: USB channel order is NOT the console channel order

Measured on this L-8 with `scripts/meters.py`, by tapping each capsule:

| Console mic | Appears on USB channels |
|---|---|
| 1 (Spanish) | 1, 2, **3** |
| 2 (English) | 1, 2, **4** |
| 3 (Turkish) | 1, 2, **5** |

**USB 1 and 2 are the stereo master mix.** Every mic sums into both, which is why
every mic lights them up. The individual pre-fader channels start at **USB 3**, so:

> **console mic N = USB channel N + 2**

This is configured in `.env` as `CH1_USB=3`, `CH2_USB=4`, `CH3_USB=5`.

Why this matters: reading USB 1/2/3 gets you master-L, master-R and mic 1 — and
because the master mix sums every microphone it is always the loudest, so the energy
gate always picks it and labels the whole room as one language. The failure is silent
and looks like "only the first mic works."

**Re-verify at the venue with `uv run python scripts/meters.py`.** Tap each capsule,
confirm which number moves, and correct `.env` if it differs. Do not assume.
