"""Synthesise a bilingual test fixture: English and French segments, with pauses.

A TEST TOOL, not a product feature — the constitution's "no TTS" is about what
the room hears. Real speech replaces this as soon as a bilingual recording exists
(spec 006, Phase 3); until then it lets the single-feed path be tested without
anyone talking into a microphone, and deterministically.

French uses a Québec voice, because that is who will be speaking.

    uv run python scripts/make_tts_fixture.py [out.wav]

Writes 1-channel 16-bit 48 kHz — the format replay.py reads in MODE=single —
plus a sidecar .json listing each segment's language, text and start time.
"""

import json
import os
import sys
import wave

import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

RATE = 48000
GAP_S = 1.8          # long enough for the recognizer to close an utterance

VOICES = {"en": "en-US-JennyNeural", "fr": "fr-CA-SylvieNeural"}

# A hands-on demo, switching language the way a Montréal speaker does: by
# passage, not word by word (detection cannot switch inside a sentence).
SEGMENTS = [
    ("en", "Today I am going to show you how to sharpen a chisel by hand."),
    ("fr", "Maintenant, je tiens l'outil à quarante-cinq degrés sur la pierre."),
    ("en", "Keep the pressure even and move slowly along the stone."),
    ("fr", "Ensuite, on vérifie le tranchant avec la lumière."),
]


def synth(lang: str, text: str) -> bytes:
    cfg = speechsdk.SpeechConfig(subscription=os.getenv("AZURE_SPEECH_KEY"),
                                 region=os.getenv("AZURE_SPEECH_REGION"))
    cfg.speech_synthesis_voice_name = VOICES[lang]
    cfg.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Raw48Khz16BitMonoPcm)
    synth = speechsdk.SpeechSynthesizer(speech_config=cfg, audio_config=None)
    res = synth.speak_text_async(text).get()
    if res.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        sys.exit(f"synthesis failed for {lang!r}: {res.reason} {getattr(res, 'cancellation_details', '')}")
    return res.audio_data


def main() -> int:
    out = sys.argv[1] if len(sys.argv) > 1 else "fixtures/bilingual_tts.wav"
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    gap = b"\x00\x00" * int(RATE * GAP_S)
    pcm, meta, t = bytearray(gap), [], GAP_S
    for lang, text in SEGMENTS:
        audio = synth(lang, text)
        meta.append({"lang": lang, "text": text, "start_s": round(t, 2),
                     "dur_s": round(len(audio) / 2 / RATE, 2)})
        pcm += audio + gap
        t += len(audio) / 2 / RATE + GAP_S
    with wave.open(out, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes(bytes(pcm))
    with open(out.replace(".wav", ".json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print(f"{out}: {t:.1f}s, {len(meta)} segments")
    for m in meta:
        print(f"  {m['start_s']:5.1f}s  {m['lang']}  {m['text']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
