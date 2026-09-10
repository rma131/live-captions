# One wedding, three languages, four and a half hours

A case study of the only time this system has run for real: a trilingual wedding
in September 2026, in Spanish, English and Turkish, with about 150 guests and one
operator who was also a guest.

Names, speeches and recordings are not published. The numbers are taken from the
event's own transcript log.

## What was asked for

Three people would speak three languages into three microphones, sometimes in
turn and sometimes interpreting one another. Everyone in the room should be able
to follow, in their own language, without wearing anything or installing
anything. It had to run once, unattended, and it could not fail loudly.

Built in three days.

## What happened

| Time | Phase | Captions | Words |
|---|---|---|---|
| 12:27–13:34 | Ceremony — **screen muted** | 50 | 698 |
| 13:34–16:11 | Reception and dinner | 99 | 1,177 |
| 16:11–17:05 | **Speech block** | 381 | 5,933 |

**4h 38m without a restart. 530 captions. Zero crashes. Not one caption came out
with an empty translation.**

Endurance was the one thing never tested beforehand, and it was the thing most
likely to fail.

## The three decisions that mattered

### 1. Never detect the language

The obvious design lets anyone pick up any microphone and works out what language
they are speaking. Testing showed automatic language identification was
unreliable on Turkish, while every **fixed pair** translated well in both
directions.

So the source language is never guessed. Each microphone is permanently assigned
one, and the operator can override it. This removed an entire category of failure
before it could happen — at the cost of a rule the room had to follow.

### 2. Mute lives on the server

The single most important feature is a key that clears every screen instantly.

It is enforced at the one point every message passes through, not in the browser.
The display is fullscreen on a projector; the operator's attention is not. Anything
that can reach the machine can mute it, and no future code path can accidentally
bypass it.

**During the ceremony, 50 captions were recognised and deliberately never shown.**
They were still written to the log, which is how we know. The screen stayed clean
through the part of the day that mattered most.

### 3. A human translation always beats the machine

Speeches were collected and translated by the families beforehand. When a
finished sentence closely matches a prepared line, the room sees the human
translation instead of the live one.

**46 captions were shown in a translation a person wrote and checked** — including
every line of the vows.

This is also the only real answer to a genuine linguistic problem: Turkish has no
grammatical gender, so a live translation into English or Spanish has to guess
"he" or "she". A prepared line never guesses.

## The part that went wrong

One speech was submitted without its prepared text. It ran entirely on live
machine translation, and the opening sentence of the father of the groom's toast
mangled both families' surnames in front of everyone.

Re-running that audio afterwards against the text — since written — **15 captions
would have been shown in the human translation instead.**

The lesson is not subtle, and it is a process lesson rather than a technical one:
*no speech goes in without its text.* The most emotional speech of the day was the
one that had none.

Two smaller failures worth recording. Only 46 of 108 prepared lines fired at all —
speakers depart from their scripts, which is what people do. And short names
collided with common words: one three-letter name was heard as "came" three times,
another consistently as a near-homophone. Some names cost more than they return
and are better left out.

## What was harder than expected

**The microphone-to-channel map fails silently.** The mixer's USB channels 1–2
carried the stereo master mix, not microphones 1 and 2. A master mix sums every
microphone, so it always wins the channel-selection gate — meaning the entire room
gets attributed to one language, with captions that look completely plausible.
Nothing errors. You just get confident nonsense.

**Pulling a fader down does not mute a channel over USB.** The per-channel feeds
are pre-fader, so a microphone can be silent in the room and fully audible to the
recogniser. There is no hardware fix; a software energy gate is the only bleed
control that exists.

**Turkish glues case endings onto names.** A correction rule for a name never
fires on `<name>'yı` or `<name>'ın` — which are exactly the mentions that matter.
Handling suffixes properly repaired 32 lines that whole-word rules would have
missed entirely.

## What it cost

About **$34** in speech-translation fees for the whole afternoon — three
recognisers running continuously for four and a half hours.

## Shape of the thing

One Python file. Two HTML pages. No framework, no database, no build step, no
test suite beyond a handful of scripts and a replay tool.

The replay tool matters more than it sounds: it feeds recorded multichannel audio
through the entire live pipeline at real-time speed, so after the first rehearsal
no change ever required anyone to talk into a microphone again.

## What I would do differently

1. Collect every speech text before anything else. It is the highest-value input
   and the one thing that cannot be fixed on the day.
2. Verify the channel map at the venue, every time, by tapping each capsule.
3. Decide deliberately whether to lock the interpretation round or change it per
   speech. Both work; not knowing which you are doing is the problem.
4. Leave short, common-sounding names out of the phrase list.
