"""Constrit la timeline de l'émission et la piste audio complète (voix + habillage)."""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from script_data import LINES, LINK, TITLE, SUBTITLE  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
AUDIO = ROOT / "audio"
SR = 48000
# 3 236 secondes de voix sur 775 répliques : chaque dixième de respiration coûte
# soixante-quinze secondes à l'antenne. À 0,40 la seconde, l'heure est tenue sans
# couper une ligne du script.
GAP = 0.25          # respiration entre deux répliques
TAIL = 0.15         # fin de réplique avant la coupe
CHAPTER = 2.6       # carte de chapitre
TECH_HOLD = 9.0     # fiche de données à l'antenne
TITLE_DUR = 12.5
# Dix-huit secondes : le bandeau des chapitres et les quatre portes de sortie
# (pouce, commentaire, forum, WhatsApp) ne tiennent pas dans les neuf d'avant.
END_DUR = 18.0
LIT = {15: "Quinze", 30: "Trente", 45: "Quarante-cinq", 60: "Soixante",
       75: "Soixante-quinze", 90: "Quatre-vingt-dix"}

BPM = 100
BEAT = 60 / BPM
BAR = 4 * BEAT


def note(name):
    """Fréquence à partir d'une note 'A2', 'C#4'..."""
    semis = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4,
             "F#": -3, "G": -2, "G#": -1, "A": 0, "A#": 1, "B": 2}
    i = 1 if name[1] == "#" else 0
    return 440 * 2 ** ((semis[name[:i + 1]] + 12 * (int(name[i + 1:]) - 4)) / 12)


CHORDS = [["C3", "E3", "G3", "B3", "D4"], ["A2", "C3", "E3", "G3", "B3"],
          ["F2", "A2", "C3", "E3", "A3"], ["G2", "B2", "D3", "F3", "G3"]]


def tone(freq, dur, amp=0.3, partials=(1, 2, 3), shape="pad"):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    for k, p in enumerate(partials):
        a = amp / (k + 1.6)
        if shape == "pad":
            out += a * np.sin(2 * np.pi * freq * p * t + 0.3 * k)
        elif shape == "pluck":
            out += a * np.sin(2 * np.pi * freq * p * t) * np.exp(-t * (2.2 + k))
        else:  # bell
            out += a * np.sin(2 * np.pi * freq * p * 1.004 * t) * np.exp(-t * (1.1 + 0.7 * k))
    at = min(int(0.12 * SR), n // 3)
    rl = min(int(0.35 * SR), n // 3)
    env = np.ones(n, np.float32)
    env[:at] = np.linspace(0, 1, at, dtype=np.float32)
    env[-rl:] *= np.linspace(1, 0, rl, dtype=np.float32)
    return out * env


def place(buf, snd, at):
    i = int(at * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(snd))
    buf[i:j] += snd[:j - i]


def build_music(total, events, speech_env):
    """Habillage : nappe en boucle, basse légère, et accents sur les chapitres."""
    mix = np.zeros(int(total * SR) + SR, np.float32)

    for bar, t0 in enumerate(np.arange(1.0, total - 1.0, BAR)):
        chord = CHORDS[bar % len(CHORDS)]
        dur = min(BAR * 1.05, total - t0)
        if dur <= 0.2:
            continue
        for v in chord:
            place(mix, tone(note(v), dur, amp=0.052, partials=(1, 2, 3)), t0)
        place(mix, tone(note(chord[0]) / 2, BAR * .9, amp=0.075, shape="pluck",
                        partials=(1, 2)), t0)
        place(mix, tone(note(chord[0]) / 2, BAR * .9, amp=0.055, shape="pluck",
                        partials=(1, 2)), t0 + 2 * BEAT)
        rng = np.random.default_rng(bar)
        for off in (1, 3):
            h = rng.standard_normal(int(0.045 * SR)).astype(np.float32) * 0.018
            place(mix, h, t0 + off * BEAT * 1.5)

    # générique d'ouverture : montée puis accord tenu
    rise = np.linspace(0, 1, int(3.2 * SR), dtype=np.float32) ** 2.2
    sweep = np.sin(2 * np.pi * np.linspace(120, 660, len(rise)) * 0.02) * rise * 0.09
    place(mix, sweep, 0.2)
    for v in CHORDS[0]:
        place(mix, tone(note(v), 3.4, amp=0.075, shape="bell"), 3.1)

    for kind, at in events:
        if kind == "chapter":
            place(mix, tone(note("E5"), 1.3, amp=0.10, shape="bell",
                            partials=(1, 2.7, 4.9)), at)
            w = np.random.default_rng(3).standard_normal(int(0.5 * SR)).astype(np.float32)
            w *= np.hanning(len(w)) * 0.05
            place(mix, w, at - 0.22)
        elif kind == "cut":
            w = np.random.default_rng(7).standard_normal(int(0.26 * SR)).astype(np.float32)
            w *= np.hanning(len(w)) * 0.028
            place(mix, w, at - 0.1)
        elif kind == "end":
            for v in CHORDS[2] + ["C5", "E5", "G5"]:
                place(mix, tone(note(v), 4.2, amp=0.07, shape="bell"), at)

    # musique rabattue dès qu'une voix parle
    n = len(mix)
    env = speech_env[:n]
    gain = 0.30 + 0.62 * (1 - env)
    mix[:n] *= gain.astype(np.float32)
    return mix


def decode(path):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le",
                        "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).copy()


PAUSE = {",": 0.16, ";": 0.20, ":": 0.18, "?": 0.26, "!": 0.26, ".": 0.30, "…": 0.30}


def synth_words(text, off, span):
    """Horodatage mot à mot réparti sur la durée réelle de parole (plan B si edge-tts
    ne renvoie pas d'événements WordBoundary)."""
    toks = text.split()
    if not toks or span <= 0.1:
        return []
    pauses = [PAUSE.get(t[-1], 0.0) for t in toks]
    weights = [max(1.0, len(t.rstrip(",;:?!.…'\"()«»"))) + 0.9 for t in toks]
    speech = max(0.25, span - sum(pauses) - 0.05)
    tot = sum(weights)
    t = off + 0.03
    out = []
    for tok, w, pz in zip(toks, weights, pauses):
        d = speech * w / tot
        out.append({"t": tok, "s": round(t, 3), "e": round(t + d, 3)})
        t += d + pz
    return out


def speech_span(s):
    """Début et fin mesurés de la parole dans une piste normalisée."""
    hot = np.abs(s) > 0.012
    idx = np.flatnonzero(hot)
    if idx.size == 0:
        return 0.0, len(s) / SR
    h = int(0.03 * SR)
    return max(0.0, idx[0] / SR - 0.06), min(len(s) / SR, idx[-1] / SR + h / SR)


def main():
    timings = json.loads((AUDIO / "timings.json").read_text())
    assert len(timings) == len(LINES), f"{len(timings)} audio / {len(LINES)} script"

    beats = [dict(kind="title", at=0.0, dur=TITLE_DUR)]
    techs = []
    t, seg, blooper = TITLE_DUR, None, False
    for i, (line, tim) in enumerate(zip(LINES, timings)):
        if line.get("seg"):
            seg = line["seg"]
            blooper = "isier" in seg or line["shot"] == "backstage"
            beats.append(dict(kind="chapter", at=round(t, 3), dur=CHAPTER,
                              seg=seg, shot=line["shot"], who=line["who"],
                              blooper=blooper, pose=line["pose"], broll=line.get("broll")))
            t += CHAPTER + 0.25
        d = tim["dur"] + TAIL
        beats.append(dict(kind="line", i=i, at=round(t, 3), dur=round(d, 3),
                          voice=tim["dur"], who=line["who"], text=line["text"],
                          shot=line["shot"], pose=line["pose"], duo=line["duo"],
                          broll=line["broll"], blooper=blooper, words=[]))
        t += d + GAP
        # La fiche de données reste posée neuf secondes, même quand la réplique
        # qui l'appelle est courte : le spectateur doit avoir le temps de lire.
        if line.get("tech"):
            titre, rows = line["tech"]
            at = round(beats[-1]["at"] + 0.6, 3)
            techs.append(dict(at=at, until=round(at + TECH_HOLD, 3),
                              titre=titre, rows=rows))
    total = t + END_DUR
    beats.append(dict(kind="end", at=round(total - END_DUR, 3), dur=END_DUR))

    # --json : la seule partition des plans, sans le mixage. Le mix ne dépend
    # que des durées, donc un master.wav déjà écrit reste valide ; les tableaux
    # d'onde (une heure à 48 kHz = 700 Mo chacun) sont ce qui fait déborder la
    # mémoire, pas les battements.
    sans_audio = "--json" in sys.argv
    speech = np.zeros(int(total * SR) + SR, np.float32) if not sans_audio else None
    marks = []
    for b in beats:
        if b["kind"] != "line":
            continue
        tim = timings[b["i"]]
        snd = decode(AUDIO / f"line_{b['i']:02d}.mp3")
        peak = float(np.max(np.abs(snd))) or 1.0
        snd = snd * (0.62 / peak)
        at = b["at"] + 0.12
        o0, o1 = speech_span(snd)
        b["clip_at"] = round(at, 3)
        b["speech_at"] = round(at + o0, 3)
        b["voice"] = round(max(0.4, o1 - o0), 3)
        b["words"] = tim["words"] or synth_words(b["text"], o0, o1 - o0)
        if speech is not None:
            place(speech, snd, at)
        marks.append((at + o0, at + o1))

    wav = AUDIO / "master.wav"
    if speech is not None:
        # enveloppe de parole : musique rabattée uniquement pendant les voix
        env = np.zeros(len(speech), np.float32)
        for a, z in marks:
            i0, i1 = int(a * SR), int(z * SR)
            env[i0:i1] = 1.0
        k = int(0.18 * SR)
        env = np.convolve(env, np.hanning(k) / np.sum(np.hanning(k)), mode="same")
        env = np.clip(env * 1.9, 0, 1)

        events = [(("chapter" if b["kind"] == "chapter" else "cut"), b["at"]) for b in beats
                  if b["kind"] == "chapter" or (b["kind"] == "line" and b["i"] % 4 == 0)]
        events.append(("end", total - END_DUR + 0.4))
        music = build_music(total, events, env)

        n = min(len(music), len(speech))
        out = music[:n] + speech[:n]
        out *= 0.92 / max(0.92, float(np.max(np.abs(out))))
        fade = int(2.0 * SR)
        out[-fade:] *= np.linspace(1, 0, fade, dtype=np.float32)

        pcm = (np.clip(out, -1, 1) * 32767).astype("<i2")
        raw = AUDIO / "raw.data"
        pcm.tofile(raw)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR),
                        "-ac", "1", "-i", str(raw), "-ac", "2", "-ar", "48000",
                        "-c:a", "pcm_s16le", str(wav)], check=True)
        raw.unlink()

    mins = round(total / 60)
    (ROOT / "timeline.json").write_text(json.dumps(
        {"total": round(total, 3), "fps": 25, "title": TITLE, "subtitle": SUBTITLE,
         "link": LINK, "beats": beats, "techs": techs,
         "segs": [b["seg"] for b in beats if b["kind"] == "chapter"],
         "duree": f"{LIT.get(mins, mins)} minutes pour tout voir, sans coupe"},
        ensure_ascii=False))
    m, s = divmod(int(total), 60)
    print(f"durée totale : {m:02d}:{s:02d}   images : {int(total*25)}   répliques : {len(LINES)}")
    if speech is not None:
        print(f"piste audio : {wav} ({wav.stat().st_size/1e6:.1f} Mo)")
    else:
        print("partition sans mixage : master.wav laissé tel quel")


if __name__ == "__main__":
    main()
