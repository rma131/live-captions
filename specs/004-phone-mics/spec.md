# 004 — Phones as microphones

**Status:** proposed · **Created:** 2026-09-09

## Problem
The system needs a multichannel interface, three wired mics and a channel map that
fails silently when wrong. Three phones, one per language, would remove all of
it — and because each phone is already its own channel, the energy gate stops
being load-bearing.

## Known constraints
- Browsers refuse microphone access over plain `http` on a LAN IP. Mic phones need
  HTTPS and a trusted certificate (`mkcert` CA installed once on known devices).
  Guest phones are unaffected — reading needs no microphone.
- iOS suspends the mic when the tab backgrounds or the screen locks. Screen Wake
  Lock (iOS 18.4+) helps; switching apps still kills it. Mic phones must be
  dedicated, awake, on charge.
- Phone mics are omnidirectional, with no gain control.
- A guest must never be able to become a microphone: join code, server-enforced.

## Seam
`Channel.feed()` is already the single entry point for audio. A `/ws/mic/{lang}`
endpoint feeds it directly; phone-fed channels bypass the gate.

## Relation to other specs
Shares the hosted-HTTPS work with 003. The "any phone" variant needs a real
domain and belongs after 003.
