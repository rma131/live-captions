# 72-hour plan — wedding is Sunday

Read this before the other two files. It is ordered by deadline, not by importance.

---

## THURSDAY (today) — validate, don't build

These are blocking. Nothing else matters until they're done.

**In the next hour**

- [ ] Create an Azure account and a Speech resource. Open **Speech Studio** and test
      speech translation live with your own voice: English → Turkish, English → Spanish,
      Turkish → English, Spanish → English.
- [ ] Specifically check: can you get **three target languages at once**, and does the
      **auto-detect / multilingual input mode** let you target Turkish and Spanish, or
      only English? The docs suggest the multilingual mode may be English-target only.
      **This answer determines whether the mic can be passed around freely.**
- [ ] Judge the Turkish output quality yourself, or have a Turkish speaker judge it.
      If it's bad, we change plan tonight, not Saturday.

**Before shops close**

- [ ] Buy a USB audio interface in person (Focusrite Scarlett Solo, Behringer UMC22, or
      whatever the local music shop has). Plus an XLR cable and a 3.5mm TRS cable.
- [ ] Buy or borrow a 5G hotspot, or confirm a phone you can tether with a data plan
      that will work at the venue.
- [ ] Backup path if no interface available: a 3.5mm-to-TRRS adapter for the MacBook
      headset jack.

**Messages to send today**

- [ ] Venue / DJ: "Do you have a spare line-out, aux send, or headphone out on the
      mixer? Is it XLR or 3.5mm? Can we plug a laptop in for 20 minutes before guests
      arrive on Sunday?"
- [ ] Every speaker: "Send me your speech text, or even just bullet points, by Friday
      lunchtime. It will be shown translated on a screen so guests can follow." Expect
      half of them not to reply. Chase the important ones by phone.

**Tonight, if the Speech Studio test passed**

- [ ] Claude Code session 1 (see `KICKOFF-PROMPT.md`). Target: laptop mic in, two
      languages rendering on a fullscreen browser page. Nothing else.

---

## FRIDAY — build and harden

- [ ] Finish the vertical slice: three languages, operator keyboard controls, projector
      page.
- [ ] Test with the **real audio interface**, not the laptop mic. This will surface
      device-selection and sample-rate bugs. Budget two hours for this alone.
- [ ] Write `glossary/names.yaml`. 40–60 entries: the couple, both families, hometowns,
      kinship terms in Turkish and Spanish, any inside references. Wire it into the
      recognition phrase list.
- [ ] Pre-translate every speech text that arrived. LLM draft, then a native Turkish
      speaker and a native Spanish speaker each read theirs. Build it as a simple slide
      deck, one or two lines per slide.
- [ ] Kill test: unplug the network mid-sentence. Does the app crash or reconnect?
      Fix it so it reconnects.
- [ ] **Hard decision point, Friday night.** If the cloud path is not working end to end
      with the real interface by now, stop adding features. Do not start the Whisper
      path. Spend Saturday on the pre-translated deck and printed programs instead.

---

## SATURDAY — rehearse and pack

- [ ] Full dress rehearsal at home. Interface plugged in, laptop connected to a TV or
      monitor via HDMI, someone giving a five-minute mock toast in each language while
      you sit at the operator keyboard. Do it twice.
- [ ] Practise the mute key until it's muscle memory. You will need it.
- [ ] Print bilingual programs with the ceremony order and the vows. This is the
      fallback that works with zero electricity and it is the one that will never let
      you down.
- [ ] Pack a physical kit and check it against this list:
      laptop, charger, audio interface, USB cable, XLR cable, 3.5mm cable, TRRS adapter,
      HDMI cable + adapters, extension lead, gaffer tape, hotspot + its charger,
      printed programs, a printed copy of this plan.
- [ ] Only if everything above is done and you're bored: look at local Whisper.
      Not before.

---

## SUNDAY — event day

- [ ] Arrive with at least 90 minutes of setup buffer. Not 30.
- [ ] Soundcheck with the actual mic the speakers will use, through the actual PA.
      Have someone talk at normal speech volume while you watch the captions.
- [ ] Check the projector from the back of the room. If you can't read it from the
      furthest table, increase the font size until you can.
- [ ] Agree a hand signal with the MC for "mute the captions."
- [ ] During the ceremony: consider screen off entirely, printed programs only.
      Captions from the reception onward.

---

## Rules for the operator on the day

1. If it produces something embarrassing, hit mute. Nobody will notice or care.
2. If it crashes, close the laptop and move on. The pre-translated deck and the printed
   programs carry the day. Do not debug during a speech.
3. Do not change any configuration after the soundcheck. Not one setting.
4. You are attending a wedding. Set a limit on how much of it you spend at the laptop.
