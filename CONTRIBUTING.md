# Contributing

## The one rule

**Never attach a transcript, a recording, or a filled-in glossary to an issue or
a pull request.**

Those files contain everything that was said at somebody's wedding, along with
their family's names. They are gitignored for that reason, and no bug is worth
publishing them. Paste the few lines that show the problem, with names replaced.

The same goes for `.env`. It holds an API key.

## What this project is trying to be

Small. One Python file, two HTML pages, no framework, no database, no build step.
It has run in front of 150 people exactly once and it did not fail, and the way
it stays that way is by not growing.

Some consequences worth knowing before you open a PR:

- **No automatic language detection.** Not an oversight. Detection proved
  unreliable on Turkish, while fixed language pairs work well in both directions,
  so the source language is always known rather than guessed. A detection
  fallback is not a welcome addition.
- **Speech recognition and translation stay in one call.** Splitting them doubles
  the latency budget and loses the joint model's context.
- **Mute is enforced on the server**, at the single point every message passes
  through. Keep it there. If you add a way to send something to the screen, it
  must pass that point too.
- **No refactors for their own sake**, and no provider abstractions.

Out of scope on purpose: QR-code onboarding, a local router, text-to-speech,
diarization, authentication, Docker, a database.

## Before opening a PR

There is no CI. Run this:

```bash
for t in mute rounds corrections script_match reconnect guest single; do
  uv run python scripts/test_$t.py || echo "FAILED: $t"
done
MODE=single uv run python scripts/test_reconnect.py
uv run python scripts/replay.py fixtures/gate_test.wav
```

`test_reconnect.py` and `replay.py` talk to the real speech API, so they need
credentials in `.env` and they cost a few cents to run.

If you changed anything about audio, verify with `scripts/replay.py` against a
recorded fixture rather than by talking into a microphone. That is what it is for.

If you changed anything that reaches the screen, check that `M` still clears it —
including on a guest phone.

## Reporting something sensitive

If you find a way for a guest on the venue network to reach the operator's
controls, that is a real problem: it means anyone in the room can mute the screen
or change the language. Report it privately through GitHub's security advisories
rather than opening an issue.
