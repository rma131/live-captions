"""Wedding live captions — three channels, three fixed-language sessions, one gate.

Three SM58s on L-8 channels 1/2/3. Each channel has a FIXED source language and
is never detected. A per-channel RMS gate decides which single channel is
forwarded to Azure; the other two get silence.

Run live:    uv run python captions.py
Replay WAV:  uv run python scripts/replay.py fixtures/rehearsal.wav
"""

import asyncio
import difflib
import json
import re
import os
import queue
import sys
import threading
import time

import azure.cognitiveservices.speech as speechsdk
import numpy as np
import uvicorn
import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse

load_dotenv()

KEY = os.getenv("AZURE_SPEECH_KEY")
REGION = os.getenv("AZURE_SPEECH_REGION")
MATCH = os.getenv("AUDIO_DEVICE_MATCH", "L-8")
GATE_THRESHOLD = float(os.getenv("GATE_THRESHOLD", "0.010"))
FONT_SIZE = int(os.getenv("FONT_SIZE", "48"))
# "dark" or "light". Only the starting value — L on the page toggles it, and a
# choice made there survives a reload.
THEME = os.getenv("THEME", "dark").lower()
# Turkish puts the verb last, so a partial Turkish sentence can translate to the
# OPPOSITE of the finished one — negation arrives in the final word. Translating
# any partial sentence also forces word-order guesses that get rewritten. So by
# default only the column of the language being SPOKEN updates live; the two
# translation columns settle once, when the sentence is complete.
# Set INTERIM_TRANSLATIONS=on to show translations of partial sentences too.
INTERIM_TRANSLATIONS = os.getenv("INTERIM_TRANSLATIONS", "off").lower() == "on"
# How close a finished sentence must be to a prepared line before we show the
# human translation instead of the machine one. 0 disables the whole mechanism.
SCRIPT_MATCH = float(os.getenv("SCRIPT_MATCH", "0.78"))
RETRY_BASE_S = float(os.getenv("RETRY_BASE_S", "1.0"))
RETRY_MAX_S = float(os.getenv("RETRY_MAX_S", "20.0"))
# Every finalised line is appended to a JSONL transcript for review afterwards.
# Append-only and flushed per line, so a crash or a closed laptop keeps whatever
# was said up to that moment.
TRANSCRIPT_DIR = os.getenv("TRANSCRIPT_DIR", "transcripts")
PORT = int(os.getenv("PORT", "8000"))
# Loopback by default. Set BIND_HOST=0.0.0.0 to let guests on the venue network
# read captions on their own phones. Doing so puts this server in front of every
# guest, so everything that can CHANGE something is restricted to loopback --
# see require_local(). The operator is at this laptop; nobody else gets to mute.
BIND_HOST = os.getenv("BIND_HOST", "127.0.0.1")
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")

DEVICE_RATE = 48000
AZURE_RATE = 16000
DECIM = DEVICE_RATE // AZURE_RATE
BLOCK = 4800  # 100 ms at 48 kHz
NCHAN = 3

# Once a channel wins it keeps winning for this long after dropping below the
# threshold. Without it, natural pauses mid-sentence hand the stream to a
# different mic and chop the utterance in half.
HOLD_S = 0.6

# channel index -> (label, azure source language, the two targets)
# Order is mic 1, 2, 3 = button 1, 2, 3 = pane 1, 2, 3 on screen, left to right.
CHANNELS = [
    ("ES", os.getenv("CH1_LANG", "es-ES"), ["en", "tr"]),
    ("EN", os.getenv("CH2_LANG", "en-US"), ["es", "tr"]),
    ("TR", os.getenv("CH3_LANG", "tr-TR"), ["es", "en"]),
]

# Which USB channel each mic actually arrives on, 1-based, as shown by
# scripts/meters.py. On this L-8, USB 1-2 are the STEREO MASTER MIX and the
# individual channels start at USB 3, so console mic N is USB channel N+2.
# Verified by tapping each capsule. Do not assume this; re-check at the venue.
USB_CHANNELS = [
    int(os.getenv("CH1_USB", "3")),
    int(os.getenv("CH2_USB", "4")),
    int(os.getenv("CH3_USB", "5")),
]
MAX_USB = max(USB_CHANNELS)

SILENCE = np.zeros(BLOCK, dtype=np.float32)

# Interpretation rounds. A speech is delivered once in its own language, then
# interpreted live into the other two by people on the other microphones, always
# in this order. The operator sets the round with 1 / 2 / 3, and 0 returns to
# free-for-all where every channel is machine-translated into the other two.
# Translators always read in the order ENGLISH -> ESPANOL -> TURKCE, skipping
# whichever language the speaker is already using. Per the running order for the
# day; five of the eight speeches are English-source, so EN is the common case.
ROUND_ORDER = {
    "ES": ["EN", "TR"],   # Spanish original -> English -> Turkish
    "TR": ["EN", "ES"],   # Turkish original -> English -> Spanish
    "EN": ["ES", "TR"],   # English original -> Spanish -> Turkish
}


class State:
    """Operator state. `muted` is the most important field in this program.

    Mute lives on the SERVER, not in the browser. The page is fullscreen on the
    projector; if the operator's focus is on the terminal, a browser keybinding
    would do nothing. Anything that can reach localhost can mute.
    """

    def __init__(self) -> None:
        self.muted = False
        self.override: int | None = None   # 0-based channel index
        self.active: int | None = None
        self.rms: list[float] = [0.0, 0.0, 0.0]
        # The language a speech is being delivered in this round, 0-based, or
        # None for free-for-all. In a round, the other two microphones carry
        # HUMAN interpreters, so what they say is never machine-translated
        # again — re-translating an interpretation back into the language it
        # came from produces round-trip nonsense on top of the original.
        self.primary: int | None = None

    def order(self) -> list[str]:
        if self.primary is None:
            return []
        return ROUND_ORDER[CHANNELS[self.primary][0]]


STATE = State()


class Broadcaster:
    """Fans messages out to connected pages. Callable from any thread."""

    def __init__(self) -> None:
        self.clients: set = set()
        self.loop: asyncio.AbstractEventLoop | None = None

    def send(self, msg: dict) -> None:
        # Mute is enforced HERE, at the single point everything passes through,
        # so no future caller can accidentally bypass it.
        if STATE.muted and msg.get("type") == "caption":
            return
        if self.loop is None or not self.clients:
            return
        self.loop.call_soon_threadsafe(asyncio.create_task, self._fanout(msg))

    async def _fanout(self, msg: dict) -> None:
        data = json.dumps(msg)
        for ws in list(self.clients):
            try:
                await ws.send_text(data)
            except Exception:
                self.clients.discard(ws)

    def status(self) -> dict:
        primary = CHANNELS[STATE.primary][0] if STATE.primary is not None else None
        return {
            "type": "status",
            "muted": STATE.muted,
            "active": CHANNELS[STATE.active][0] if STATE.active is not None else None,
            "override": CHANNELS[STATE.override][0] if STATE.override is not None else None,
            "primary": primary,
            "threshold": round(PIPELINE.gate.threshold, 5) if PIPELINE else GATE_THRESHOLD,
            "levels": {CHANNELS[i][0]: round(v, 4) for i, v in enumerate(STATE.rms)},
            "order": ([primary] + STATE.order()) if primary else [],
            "clients": len(self.clients),
        }

    def push_status(self) -> None:
        self.send(self.status())


BUS = Broadcaster()


class Transcript:
    """Append-only log of every finalised line, for reviewing afterwards.

    One JSON object per line so a half-written file is still readable, and so it
    can be diffed against the human translations later.
    """

    def __init__(self) -> None:
        os.makedirs(TRANSCRIPT_DIR, exist_ok=True)
        stamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        self.path = os.path.join(TRANSCRIPT_DIR, f"{stamp}.jsonl")
        self.lock = threading.Lock()
        self.count = 0
        self.started = time.time()

    def write(self, row: dict) -> None:
        row = {"t": round(time.time() - self.started, 2),
               "clock": time.strftime("%H:%M:%S"), **row}
        line = json.dumps(row, ensure_ascii=False)
        try:
            with self.lock:
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(line + "\n")   # flushed on close, every line
                self.count += 1
        except Exception as e:
            print(f"transcript write failed: {e}")   # never take the show down


LOG = Transcript()
PIPELINE = None      # set once the pipeline exists, so /reconnect can reach it


def set_mute(value: bool) -> dict:
    STATE.muted = value
    if value:
        BUS.send({"type": "clear"})
    BUS.push_status()
    print(f"*** MUTE {'ON — screen cleared' if value else 'OFF'} ***")
    return BUS.status()


def nudge_gate(factor: float) -> dict:
    """Raise or lower the energy gate live, for a speaker who stands off-mic.

    Multiplicative, because a useful threshold spans two orders of magnitude and
    fixed steps are far too coarse at one end and useless at the other.
    """
    if PIPELINE:
        g = PIPELINE.gate
        g.threshold = max(0.0005, min(0.2, g.threshold * factor))
        print(f"gate threshold -> {g.threshold:.5f}   "
              + "  ".join(f"{CHANNELS[i][0]}:{v:.4f}" for i, v in enumerate(STATE.rms)))
    BUS.push_status()
    return BUS.status()


def set_primary(idx: int | None) -> dict:
    STATE.primary = idx
    BUS.send({"type": "clear"})   # a new round starts on a clean screen
    BUS.push_status()
    if idx is None:
        print("*** round released — translating every channel again ***")
    else:
        label = CHANNELS[idx][0]
        print(f"*** round: {label} speaking, interpreted into "
              f"{' then '.join(ROUND_ORDER[label])} ***")
    return BUS.status()


def load_glossary(path: str = "glossary/names.yaml") -> tuple[list[str], list]:
    """Phrases bias what Azure HEARS. Corrections fix what it WRITES.

    Every phrase goes to every recognizer, not split by language — a Turkish
    name spoken in an English toast needs to be in the English recognizer.
    """
    if not os.path.exists(path):
        print(f"WARNING: {path} missing, running without name biasing")
        return [], []
    data = yaml.safe_load(open(path, encoding="utf-8")) or {}
    corrections = data.pop("corrections", None) or {}
    phrases = [p for section in data.values() if section for p in section]
    # whole-word, case-insensitive; longest first so "Marysol" wins over "Christi"
    rules = [
        (re.compile(rf"\b{re.escape(wrong)}({TR_SUFFIX})\b", re.IGNORECASE), right)
        for wrong, right in sorted(corrections.items(), key=lambda kv: -len(kv[0]))
    ]
    return phrases, rules


# Turkish glues case endings straight onto a name - "Marysolyi", "Kerem'i",
# "Sevginin", "Mustafaten" - so a whole-word correction rule never fires on the
# very mentions that matter most. We allow a Turkish ending after the name and
# put it back afterwards.
#
# Deliberately a list of real Turkish endings rather than "any few letters": an
# English plural must NOT match, or "Marysols" would become "Marisols".
TR_SUFFIX = (r"(?:'?(?:n?[ıiuü]n|y?[ıiuü]|n?[ae]|y[ae]|"
             r"[dt][ae]n?|yl[ae]|l[ae]r[ıi]?|l[ae]))?")


def _normalise(text: str) -> str:
    return re.sub(r"[^\w\s]", "", text.lower()).strip()


def load_speeches(path: str = "glossary/speeches.yaml") -> list[dict]:
    """Prepared, human-translated lines. Optional — an empty file means
    everything is translated live."""
    if not os.path.exists(path) or SCRIPT_MATCH <= 0:
        return []
    data = yaml.safe_load(open(path, encoding="utf-8")) or {}
    out = []
    for entry in data.get("lines") or []:
        if not entry.get("said") or not entry.get("lang"):
            continue
        out.append({**entry, "_key": _normalise(entry["said"])})
    return out


def match_script(text: str, lang: str, lines: list[dict]) -> dict | None:
    """Closest prepared line in the same source language, if close enough.

    A speaker who goes off-script simply does not match and falls through to
    live translation.
    """
    key = _normalise(text)
    if not key:
        return None
    best, score = None, 0.0
    for entry in lines:
        if not entry["lang"].startswith(lang[:2]):
            continue
        r = difflib.SequenceMatcher(None, key, entry["_key"]).ratio()
        if r > score:
            best, score = entry, r
    return best if score >= SCRIPT_MATCH else None


def apply_corrections(text: str, rules: list) -> str:
    # The Turkish suffix is carried across, so "Marysolyi" becomes "Marisolyi"
    # rather than being missed entirely.
    for pattern, right in rules:
        text = pattern.sub(lambda m: right + m.group(1), text)
    return text


def make_lowpass(cutoff_hz: float, rate: int, taps: int = 31) -> np.ndarray:
    n = np.arange(taps) - (taps - 1) / 2
    h = np.sinc(2 * cutoff_hz / rate * n) * np.hamming(taps)
    return (h / h.sum()).astype(np.float32)


class Resampler:
    """48 kHz -> 16 kHz. Anti-alias lowpass then 3:1 decimate, state kept
    across blocks. Without the filter everything from 8-24 kHz folds into the
    speech band and quietly degrades recognition."""

    def __init__(self) -> None:
        self.h = make_lowpass(7500.0, DEVICE_RATE)
        self.tail = np.zeros(len(self.h) - 1, dtype=np.float32)

    def __call__(self, x: np.ndarray) -> bytes:
        padded = np.concatenate((self.tail, x))
        self.tail = padded[-(len(self.h) - 1):]
        y = np.convolve(padded, self.h, mode="valid")[::DECIM]
        return (np.clip(y, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()


class Channel:
    """One microphone, one fixed source language, one Azure session.

    Sessions die when the uplink drops and the SDK does not bring them back, so
    each channel rebuilds its own recognizer with backoff, independently of the
    other two. The operator will not be at the keyboard when it happens.
    """

    def __init__(self, idx: int, label: str, source: str, targets: list[str],
                 phrases: list[str], rules: list, script: list[dict]) -> None:
        self.idx, self.label, self.source, self.targets = idx, label, source, targets
        self.rules = rules
        self.script = script
        self.phrases = phrases
        self.resampler = Resampler()

        self.lock = threading.Lock()
        self.alive = False
        self.want_restart = False
        self.retry_at = 0.0
        self.backoff = RETRY_BASE_S
        self.build()

    def build(self) -> None:
        cfg = speechsdk.translation.SpeechTranslationConfig(subscription=KEY, region=REGION)
        cfg.speech_recognition_language = self.source  # fixed. never detected.
        for t in self.targets:
            cfg.add_target_language(t)

        fmt = speechsdk.audio.AudioStreamFormat(
            samples_per_second=AZURE_RATE, bits_per_sample=16, channels=1
        )
        self.push = speechsdk.audio.PushAudioInputStream(stream_format=fmt)
        self.recognizer = speechsdk.translation.TranslationRecognizer(
            translation_config=cfg,
            audio_config=speechsdk.audio.AudioConfig(stream=self.push),
        )
        if self.phrases:
            pl = speechsdk.PhraseListGrammar.from_recognizer(self.recognizer)
            for p in self.phrases:
                pl.addPhrase(p)

        self.recognizer.recognizing.connect(self._on_interim)
        self.recognizer.recognized.connect(self._on_final)
        self.recognizer.canceled.connect(self._on_canceled)
        self.recognizer.session_started.connect(self._on_session_started)

    def start(self) -> None:
        self.recognizer.start_continuous_recognition_async()
        with self.lock:
            self.alive = True

    def _detach(self, recognizer) -> None:
        """Unhook our Python callbacks from a recognizer we are done with.

        The SDK calls these back from its own native threads. If one fires while
        the interpreter is shutting down, the exception crosses a noexcept frame
        inside the SDK and glibc aborts the process with "FATAL: exception not
        rethrown" — exit 134 after a clean run, on Linux only. Detaching first
        means there is nothing left to call.

        It also stops a recognizer being replaced mid-reconnect from reporting
        its own death onto the fresh session that just took its place.
        """
        for signal in (recognizer.recognizing, recognizer.recognized,
                       recognizer.canceled, recognizer.session_started):
            try:
                signal.disconnect_all()
            except Exception:
                pass

    def stop(self) -> None:
        with self.lock:
            self.alive = False
        try:
            self._detach(self.recognizer)
            self.push.close()
            self.recognizer.stop_continuous_recognition_async()
        except Exception:
            pass

    def restart(self) -> None:
        """Tear the session down and build a fresh one. Never called from an SDK
        callback thread — the supervisor does it, so a hung stop cannot wedge
        the audio path."""
        print(f"  [{self.label}] reconnecting…")
        BUS.send({"type": "session", "ch": self.label, "state": "retrying"})
        old_push, old_rec = self.push, self.recognizer
        with self.lock:
            self.alive = False
            self.want_restart = False
        try:
            self._detach(old_rec)
            old_push.close()
            old_rec.stop_continuous_recognition_async()
        except Exception:
            pass
        try:
            self.build()
            self.start()
        except Exception as e:                       # keep trying, never crash
            print(f"  [{self.label}] reconnect failed: {e}")
            with self.lock:
                self.want_restart = True

    def mark_down(self, why: str) -> None:
        with self.lock:
            if self.want_restart:
                return
            self.alive = False
            self.want_restart = True
            self.retry_at = time.monotonic() + self.backoff
            wait = self.backoff
            self.backoff = min(self.backoff * 2, RETRY_MAX_S)
        print(f"  [{self.label}] session down ({why}); retrying in {wait:.0f}s")
        BUS.send({"type": "session", "ch": self.label, "state": "down"})

    def feed(self, mono48: np.ndarray) -> None:
        data = self.resampler(mono48)
        with self.lock:
            if not self.alive:
                return                                # dropped while reconnecting
            try:
                self.push.write(data)
            except Exception as e:
                self.alive = False
                threading.Thread(target=self.mark_down, args=(f"write: {e}",),
                                 daemon=True).start()

    def _on_session_started(self, evt) -> None:
        with self.lock:
            self.backoff = RETRY_BASE_S               # healthy again
        BUS.send({"type": "session", "ch": self.label, "state": "up"})

    def _fix(self, text: str) -> str:
        return apply_corrections(text, self.rules)

    def is_interpreter(self) -> bool:
        """True when a round is running and this mic is not the original speaker."""
        return STATE.primary is not None and self.idx != STATE.primary

    def _on_interim(self, evt) -> None:
        if not evt.result.text.strip():
            return
        text = self._fix(evt.result.text)
        print(f"  [{self.label}] ~ {text}")
        interp = self.is_interpreter()
        BUS.send({
            "type": "caption", "final": False, "ch": self.label, "source": text,
            "interpreted": interp,
            # Translation columns stay put until the sentence is finished,
            # unless INTERIM_TRANSLATIONS is on. An interpreter is never
            # machine-translated: their words fill their own column only.
            "translations": (
                {t: self._fix(evt.result.translations.get(t, "")) for t in self.targets}
                if INTERIM_TRANSLATIONS and not interp else {}
            ),
        })

    def _on_final(self, evt) -> None:
        if evt.result.reason != speechsdk.ResultReason.TranslatedSpeech:
            return
        if not evt.result.text.strip():
            return
        text = self._fix(evt.result.text)
        trans = {t: self._fix(evt.result.translations.get(t, "")) for t in self.targets}

        # A prepared line beats the machine every time — it is the only
        # human-checked output in the system.
        raw_text = evt.result.text
        raw_trans = {t: evt.result.translations.get(t, "") for t in self.targets}
        hit = match_script(text, self.source, self.script)
        if hit:
            text = hit.get(self.source[:2], text)
            trans = {t: hit.get(t, trans[t]) for t in self.targets}
            print(f"  [{self.label}] (prepared line)")

        # Logged whatever happens on screen, including while muted: the point of
        # the log is reviewing what went wrong, and muted lines are exactly the
        # ones that went wrong.
        LOG.write({
            "ch": self.label, "lang": self.source,
            "heard": text, "translations": trans,
            # what Azure produced before our corrections and prepared lines, so
            # the two can be compared afterwards
            "raw_heard": raw_text, "raw_translations": raw_trans,
            "prepared": bool(hit),
            "primary": CHANNELS[STATE.primary][0] if STATE.primary is not None else None,
            "interpreted": self.is_interpreter(),
            "corrected": raw_text != text and not hit,
            "muted": STATE.muted,
        })
        print(f"  [{self.label}] = {text}")
        for t in self.targets:
            print(f"       {t}: {trans[t]}")
        print()
        interp = self.is_interpreter()
        BUS.send({"type": "caption", "final": True, "ch": self.label,
                  "source": text, "interpreted": interp,
                  # A human interpretation replaces the machine draft in its own
                  # column and goes nowhere else.
                  "translations": {} if interp else trans})

    def _on_canceled(self, evt) -> None:
        # NoError is the normal end-of-stream at shutdown. Anything else is the
        # uplink, and the session will not come back by itself.
        if evt.error_code == speechsdk.CancellationErrorCode.NoError:
            return
        print(f"  [{self.label}] CANCELED {evt.error_code}: {evt.error_details}")
        self.mark_down(str(evt.error_code))


class Gate:
    """Loudest channel above an absolute threshold wins; the others get silence.

    Silence rather than nothing: the recognizers must keep receiving audio in
    real time or Azure never sees the pause that ends an utterance, and the
    final result never arrives.
    """

    def __init__(self, threshold: float) -> None:
        self.threshold = threshold
        self.winner: int | None = None
        self.last_active = 0.0
        self.override: int | None = None

    def pick(self, rms: np.ndarray, now: float) -> int | None:
        if self.override is not None:
            return self.override
        loudest = int(np.argmax(rms))
        if rms[loudest] >= self.threshold:
            self.winner, self.last_active = loudest, now
        elif self.winner is not None and now - self.last_active > HOLD_S:
            self.winner = None
        return self.winner


class Pipeline:
    """Drives the gate and the three channels. Fed by live audio or by replay."""

    def __init__(self) -> None:
        global PIPELINE
        PIPELINE = self
        phrases, rules = load_glossary()
        script = load_speeches()
        print(f"phrase list: {len(phrases)} entries -> all three recognizers")
        print(f"corrections: {len(rules)} rules applied to output")
        print(f"interim translations: {'on' if INTERIM_TRANSLATIONS else 'off'}")
        print(f"prepared lines: {len(script)} (match >= {SCRIPT_MATCH})")
        self.channels = [
            Channel(i, label, src, tgts, phrases, rules, script)
            for i, (label, src, tgts) in enumerate(CHANNELS)
        ]
        self.gate = Gate(GATE_THRESHOLD)
        self.last_winner = -2
        self.running = True

    def start(self) -> None:
        for c in self.channels:
            c.start()
        threading.Thread(target=self._supervise, daemon=True).start()

    def stop(self) -> None:
        self.running = False
        for c in self.channels:
            c.stop()

    def _supervise(self) -> None:
        """Rebuild dead sessions. Runs off the audio path and off the SDK
        callback threads, so a slow reconnect never blocks capture."""
        while self.running:
            now = time.monotonic()
            for c in self.channels:
                with c.lock:
                    due = c.want_restart and now >= c.retry_at
                if due:
                    c.restart()
            time.sleep(0.25)

    def reconnect_all(self) -> None:
        for c in self.channels:
            with c.lock:
                c.want_restart = True
                c.retry_at = 0.0
                c.backoff = RETRY_BASE_S

    def process(self, block: np.ndarray, now: float) -> None:
        """block: (frames, 3) float32 at 48 kHz."""
        rms = np.sqrt(np.mean(block * block, axis=0))
        STATE.rms = [float(v) for v in rms]
        self.gate.override = STATE.override
        winner = self.gate.pick(rms, now)
        STATE.active = winner
        if winner != self.last_winner:
            who = self.channels[winner].label if winner is not None else "-none-"
            lvl = " ".join(f"{c.label}:{r:.4f}" for c, r in zip(self.channels, rms))
            print(f"gate -> {who}   ({lvl})")
            self.last_winner = winner
            BUS.push_status()
        for i, ch in enumerate(self.channels):
            ch.feed(np.ascontiguousarray(block[:, i]) if i == winner else SILENCE)



# ----------------------------------------------------------------- web server

app = FastAPI()

LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def is_local(client) -> bool:
    return client is not None and client.host in LOOPBACK


def require_local(request):
    """Refuse control requests that did not come from this laptop.

    Only matters once BIND_HOST opens the server to the room. Mute is the most
    important feature in the project and a guest with the page open must not be
    able to reach it -- neither by pressing M nor by typing /mute into a phone.
    """
    if not is_local(request.client):
        return JSONResponse({"detail": "controls are local-only"}, status_code=403)
    return None


@app.get("/")
def index():
    return FileResponse(os.path.join(WEB_DIR, "screen.html"))


@app.get("/guest")
def guest():
    """Read-only caption view for a guest's phone. One language, no controls."""
    return FileResponse(os.path.join(WEB_DIR, "guest.html"))


# Mute over plain HTTP as well as over the socket, so it works from anything
# that can reach localhost even if the page is not focused or not loaded.
@app.get("/mute")
@app.post("/mute")
def http_mute(request: Request):
    return require_local(request) or JSONResponse(set_mute(True))


@app.get("/unmute")
@app.post("/unmute")
def http_unmute(request: Request):
    return require_local(request) or JSONResponse(set_mute(False))


@app.get("/gate/{direction}")
@app.post("/gate/{direction}")
def http_gate(direction: str, request: Request):
    """up = less sensitive, down = picks up quieter speakers."""
    return require_local(request) or JSONResponse(
        nudge_gate(1.25 if direction == "up" else 0.8))


@app.get("/fc-{variant}.svg")
def logo(variant: str):
    """Optional monogram for the mute screen. Absent in the public repo — the
    page falls back to the word MUTED."""
    if variant not in ("dark", "white"):
        return JSONResponse({"detail": "no logo"}, status_code=404)
    path = os.path.join(WEB_DIR, f"fc-{variant}.svg")
    if not os.path.exists(path):
        return JSONResponse({"detail": "no logo"}, status_code=404)
    return FileResponse(path, media_type="image/svg+xml")


@app.get("/round/{ch}")
@app.post("/round/{ch}")
def http_round(ch: int, request: Request):
    """0 = free-for-all, 1/2/3 = that microphone is delivering the speech."""
    return require_local(request) or JSONResponse(
        set_primary(None if not ch else ch - 1))


@app.get("/reconnect")
@app.post("/reconnect")
def http_reconnect(request: Request):
    denied = require_local(request)
    if denied:
        return denied
    if PIPELINE:
        PIPELINE.reconnect_all()
    return JSONResponse({"reconnecting": True})


@app.get("/status")
def http_status():
    return JSONResponse(BUS.status())


@app.websocket("/ws/guest")
async def ws_guest(ws: WebSocket):
    """Captions out, nothing in.

    A guest's phone is on the same server as the operator's controls, so this
    socket never reads a message. Whatever a guest sends is discarded without
    being parsed -- there is no code path from here to mute, rounds or the gate.
    Mute still covers these clients for free, because Broadcaster.send drops
    captions before fan-out rather than at the page.
    """
    await ws.accept()
    BUS.loop = asyncio.get_running_loop()
    BUS.clients.add(ws)
    await ws.send_text(json.dumps({**BUS.status(), "font_size": FONT_SIZE,
                                   "theme": THEME, "guest": True}))
    try:
        while True:
            await ws.receive_text()      # read and drop, purely to notice a close
    except WebSocketDisconnect:
        pass
    finally:
        BUS.clients.discard(ws)


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    # The operator socket. It can mute, so it does not leave this laptop.
    if not is_local(ws.client):
        await ws.close(code=1008)
        return
    await ws.accept()
    BUS.loop = asyncio.get_running_loop()
    BUS.clients.add(ws)
    await ws.send_text(json.dumps({**BUS.status(),
                                   "font_size": FONT_SIZE, "theme": THEME}))
    try:
        while True:
            msg = json.loads(await ws.receive_text())
            kind = msg.get("type")
            if kind == "mute":
                set_mute(not STATE.muted if msg.get("toggle") else bool(msg.get("on")))
            elif kind == "clear":
                BUS.send({"type": "clear"})
            elif kind == "gate":
                nudge_gate(1.25 if msg.get("up") else 0.8)
            elif kind == "primary":
                ch = msg.get("ch")  # 0 = free-for-all, 1-3 = that mic is the speaker
                set_primary(None if not ch else int(ch) - 1)
            elif kind == "reconnect":
                print("*** operator requested reconnect of all sessions ***")
                if PIPELINE:
                    PIPELINE.reconnect_all()
            BUS.push_status()
    except WebSocketDisconnect:
        pass
    finally:
        BUS.clients.discard(ws)


def lan_address() -> str | None:
    """Best guess at the address a phone on the venue network would use."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("192.0.2.1", 1))      # TEST-NET-1, routed nowhere, sends nothing
        addr = s.getsockname()[0]
        s.close()
        return addr
    except Exception:
        return None


def serve_in_background() -> None:
    cfg = uvicorn.Config(app, host=BIND_HOST, port=PORT, log_level="warning")
    threading.Thread(target=uvicorn.Server(cfg).run, daemon=True).start()
    print(f"display:  http://127.0.0.1:{PORT}/")
    print(f"mute:     http://127.0.0.1:{PORT}/mute   (unmute: /unmute)")
    if BIND_HOST not in ("127.0.0.1", "localhost"):
        host = lan_address() or BIND_HOST
        print(f"guests:   http://{host}:{PORT}/guest   (read-only, controls stay here)")


def find_device(min_channels: int = 3) -> int:
    import sounddevice as sd

    hits = [
        (i, d)
        for i, d in enumerate(sd.query_devices())
        if d["max_input_channels"] >= min_channels and MATCH.lower() in d["name"].lower()
    ]
    if len(hits) != 1:
        print(f"device match {MATCH!r} found {len(hits)} candidates, need exactly 1:")
        for i, d in hits:
            print(f"  [{i}] {d['name']} ({d['max_input_channels']} in)")
        sys.exit(1)
    idx, dev = hits[0]
    print(f"device [{idx}] {dev['name']} — {dev['max_input_channels']} in @ {DEVICE_RATE} Hz")
    return idx


def main() -> int:
    import sounddevice as sd

    if not KEY or not REGION:
        print("AZURE_SPEECH_KEY / AZURE_SPEECH_REGION missing from .env")
        return 1

    serve_in_background()
    device = find_device(MAX_USB)
    print(f"mic -> USB channel map: {list(zip([c[0] for c in CHANNELS], USB_CHANNELS))}")
    pipe = Pipeline()
    blocks: queue.Queue = queue.Queue()

    def callback(indata, frames, time_info, status):
        if status:
            print(f"audio status: {status}", file=sys.stderr)
        # Map USB channels down to the three mics before anything else sees it.
        blocks.put((indata[:, [c - 1 for c in USB_CHANNELS]].copy(), time.monotonic()))

    pipe.start()
    print(f"gate threshold {GATE_THRESHOLD}. ctrl-c to stop.\n")
    stream = sd.InputStream(
        device=device, channels=MAX_USB, samplerate=DEVICE_RATE,
        blocksize=BLOCK, dtype="float32", callback=callback,
    )
    try:
        with stream:
            while True:
                block, now = blocks.get()
                pipe.process(block, now)
    except KeyboardInterrupt:
        print("\nstopping")
    finally:
        pipe.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
