# Changelog

## v1.0.0

First complete version. Everything below has been run against the real hardware
and a real Azure resource; it has not yet run at the event itself.

### Capture
- Multichannel USB capture from a Zoom LiveTrak L-8 at 48 kHz, device selected by
  name substring rather than index.
- Per-channel RMS energy gate with a hold, so a mid-sentence breath does not hand
  the stream to another microphone. Non-winning channels are fed silence rather
  than nothing, so Azure still sees the pause that ends an utterance.
- Anti-aliased 3:1 decimation to the 16 kHz Azure expects.
- Mic-to-USB channel mapping in config: individual channels start at USB 3
  because 1–2 carry the stereo master mix.

### Translation
- Three concurrent Azure speech-translation sessions with fixed source languages.
  No language detection anywhere.
- Phrase list from a glossary, attached to all three recognizers rather than
  split by language.
- Output corrections, Turkish-suffix aware.
- Prepared human translations that override the machine when a finished sentence
  matches one, with everything unmatched falling through to live translation.

### Display
- Three fixed columns, one per language, the speaking one marked by colour only.
- Interim results in the speaker's column; translations settle once, on the final.
- Interpretation rounds: interpreters fill their own column and are never
  re-translated.
- Corner status for connection, active mic, round and per-session health.

### Operator
- Server-side mute, reachable over HTTP as well as the keyboard.
- Live energy-gate adjustment with a level readout.
- Font size, clear, reconnect, and a key-binding overlay.

### Resilience
- Per-session reconnect with exponential backoff after an uplink drop, run by a
  supervisor thread off the audio and callback paths.
- Captions stay on screen while a session reconnects.

### Review
- JSONL transcript of every finalised line, keeping both the raw Azure output and
  what was displayed.
- A review tool reporting which correction rules fired, which never did, and
  which sentences nearly matched a prepared line.

### Authoring
- Speech import from Notion or a CSV export, with per-row validation.
- A prompt for turning a speech document into importable rows.
