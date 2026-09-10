"""Serve the display page and push fake captions through it.

No microphones, no Azure, no L-8. Use this to set font size from the back of the
room, check the projector, and rehearse the operator hotkeys.

    uv run python scripts/demo_captions.py
    open http://127.0.0.1:8000/
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import captions as C  # noqa: E402

SCRIPT = [
    ("EN", {"tr": "Herkese hoş geldiniz.", "es": "Bienvenidos a todos."},
     "Welcome everyone."),
    ("EN", {"tr": "Geldiğiniz için teşekkürler.", "es": "Gracias por venir."},
     "Thank you for coming."),
    ("TR", {"en": "Today we are very happy.", "es": "Hoy estamos muy felices."},
     "Bugün çok mutluyuz."),
    ("TR", {"en": "Welcome to our family.", "es": "Bienvenida a nuestra familia."},
     "Ailemize hoş geldiniz."),
    ("ES", {"en": "To the bride and groom.", "tr": "Gelin ve damada."},
     "Por los novios."),
    ("ES", {"en": "We wish you a long life together.",
            "tr": "Birlikte uzun bir ömür diliyoruz."},
     "Les deseamos una larga vida juntos."),
]


def main() -> int:
    C.serve_in_background()
    print("\npushing demo captions. ctrl-c to stop.\n")
    i = 0
    try:
        while True:
            label, tr, src = SCRIPT[i % len(SCRIPT)]
            i += 1
            # interims first, word by word, like the real thing
            words = {k: v.split() for k, v in tr.items()}
            n = max(len(w) for w in words.values())
            for step in range(1, n + 1):
                part = {k: " ".join(w[:max(1, round(step * len(w) / n))])
                        for k, w in words.items()}
                C.BUS.send({"type": "caption", "final": False, "ch": label,
                            "source": src,
                            "translations": part if C.INTERIM_TRANSLATIONS else {}})
                time.sleep(0.45)
            C.BUS.send({"type": "caption", "final": True, "ch": label,
                        "source": src, "translations": tr})
            C.STATE.active = [c[0] for c in C.CHANNELS].index(label)
            C.BUS.push_status()
            time.sleep(1.6)
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
