"""Phase 2: one channel, end to end.

Reads channel 1 of the L-8 (English), pushes it to a single Azure translation
session, prints Spanish and Turkish to the terminal with latency from speech onset.

No server, no web page, no gate, no glossary. Ctrl-C to stop.
"""

import os
import queue
import sys
import threading
import time

import azure.cognitiveservices.speech as speechsdk
import numpy as np
import sounddevice as sd
from dotenv import load_dotenv

load_dotenv()

KEY = os.getenv("AZURE_SPEECH_KEY")
REGION = os.getenv("AZURE_SPEECH_REGION")
MATCH = os.getenv("AUDIO_DEVICE_MATCH", "L-8")
SOURCE_LANG = os.getenv("CH1_LANG", "en-US")
TARGETS = ["es", "tr"]

DEVICE_RATE = 48000
AZURE_RATE = 16000
DECIM = DEVICE_RATE // AZURE_RATE  # 3
BLOCK = 4800  # 100 ms at 48 kHz

# Onset detection, only so we can print a latency number. This is NOT the Phase 3
# gate — it gates nothing, it just timestamps when you started talking.
ONSET_RMS = float(os.getenv("GATE_THRESHOLD", "0.010"))


def find_device() -> int:
    hits = [
        (i, d)
        for i, d in enumerate(sd.query_devices())
        if d["max_input_channels"] >= 3 and MATCH.lower() in d["name"].lower()
    ]
    if len(hits) != 1:
        print(f"device match {MATCH!r} found {len(hits)} candidates; need exactly 1")
        for i, d in hits:
            print(f"  [{i}] {d['name']} ({d['max_input_channels']} in)")
        sys.exit(1)
    idx, dev = hits[0]
    print(f"device [{idx}] {dev['name']} — {dev['max_input_channels']} in @ {DEVICE_RATE} Hz")
    return idx


# 3:1 decimation needs an anti-alias lowpass first, or everything between 8 and
# 24 kHz folds down into the speech band and quietly degrades recognition.
# 31-tap windowed sinc at 7.5 kHz. Filter state carries across blocks.
def make_lowpass(cutoff_hz: float, rate: int, taps: int = 31) -> np.ndarray:
    n = np.arange(taps) - (taps - 1) / 2
    h = np.sinc(2 * cutoff_hz / rate * n) * np.hamming(taps)
    return (h / h.sum()).astype(np.float32)


class Resampler:
    def __init__(self) -> None:
        self.h = make_lowpass(7500.0, DEVICE_RATE)
        self.tail = np.zeros(len(self.h) - 1, dtype=np.float32)

    def __call__(self, x: np.ndarray) -> bytes:
        padded = np.concatenate((self.tail, x))
        self.tail = padded[-(len(self.h) - 1):]
        y = np.convolve(padded, self.h, mode="valid")[::DECIM]
        return (np.clip(y, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()


def main() -> int:
    if not KEY or not REGION:
        print("AZURE_SPEECH_KEY / AZURE_SPEECH_REGION missing from .env")
        return 1

    device = find_device()

    cfg = speechsdk.translation.SpeechTranslationConfig(subscription=KEY, region=REGION)
    cfg.speech_recognition_language = SOURCE_LANG  # fixed. never detected.
    for t in TARGETS:
        cfg.add_target_language(t)

    fmt = speechsdk.audio.AudioStreamFormat(
        samples_per_second=AZURE_RATE, bits_per_sample=16, channels=1
    )
    push = speechsdk.audio.PushAudioInputStream(stream_format=fmt)
    recognizer = speechsdk.translation.TranslationRecognizer(
        translation_config=cfg, audio_config=speechsdk.audio.AudioConfig(stream=push)
    )

    onset = {"t": None, "reported": False}
    lock = threading.Lock()

    def elapsed() -> str:
        with lock:
            t0 = onset["t"]
        return f"{time.monotonic() - t0:5.2f}s" if t0 else "  -  "

    def on_recognizing(evt):
        text = evt.result.text
        if not text:
            return
        with lock:
            first = not onset["reported"]
            onset["reported"] = True
        tag = "FIRST INTERIM" if first else "interim"
        print(f"[{elapsed()}] {tag:>13}  {text}")

    def on_recognized(evt):
        if evt.result.reason != speechsdk.ResultReason.TranslatedSpeech:
            if evt.result.reason == speechsdk.ResultReason.NoMatch:
                print(f"[{elapsed()}]        no match")
            return
        if not evt.result.text.strip():
            return
        tr = evt.result.translations
        print(f"[{elapsed()}] {'FINAL en':>13}  {evt.result.text}")
        print(f"{'':21} es  {tr.get('es', '')}")
        print(f"{'':21} tr  {tr.get('tr', '')}")
        print()
        with lock:
            onset["t"] = None
            onset["reported"] = False

    def on_canceled(evt):
        print(f"CANCELED reason={evt.reason} code={evt.error_code}")
        if evt.error_details:
            print(f"  {evt.error_details}")

    recognizer.recognizing.connect(on_recognizing)
    recognizer.recognized.connect(on_recognized)
    recognizer.canceled.connect(on_canceled)
    recognizer.session_started.connect(lambda e: print("session started"))
    recognizer.session_stopped.connect(lambda e: print("session stopped"))

    resample = Resampler()
    audio_q: queue.Queue = queue.Queue()

    def callback(indata, frames, time_info, status):
        if status:
            print(f"audio status: {status}", file=sys.stderr)
        ch1 = np.ascontiguousarray(indata[:, 0])
        rms = float(np.sqrt(np.mean(ch1 * ch1)))
        now = time.monotonic()
        with lock:
            if rms >= ONSET_RMS and onset["t"] is None:
                onset["t"] = now
        audio_q.put(resample(ch1))

    recognizer.start_continuous_recognition()
    print(f"listening on channel 1, source {SOURCE_LANG} -> {TARGETS}. ctrl-c to stop.\n")

    stream = sd.InputStream(
        device=device, channels=3, samplerate=DEVICE_RATE,
        blocksize=BLOCK, dtype="float32", callback=callback,
    )
    try:
        with stream:
            while True:
                push.write(audio_q.get())
    except KeyboardInterrupt:
        print("\nstopping")
    finally:
        push.close()
        recognizer.stop_continuous_recognition()
    return 0


if __name__ == "__main__":
    sys.exit(main())
