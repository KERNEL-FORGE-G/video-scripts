"""Voix Gemini : une piste WAV par réplique, en remplacement d'edge-tts.

Gemini TTS ne renvoie pas d'horodatage mot à mot. Ce n'est pas un trou dans le
pipeline : `timeline.py` reconstruit les mots à partir de la durée de parole
mesurée (`speech_span` + `synth_words`) dès que `words` est vide. Ce script ne
produit donc que l'audio et ses durées.

    python3 build/gen_audio_gemini.py --voix              # voix disponibles
    python3 build/gen_audio_gemini.py --max 20            # échantillon d'écoute
    python3 build/gen_audio_gemini.py                     # les 775 répliques
    python3 build/gen_audio_gemini.py --tempo 20          # plus doux si 429
    UNIFLOW_COUPE=15 python3 build/gen_audio_gemini.py    # la courte coupe
"""
import argparse
import json
import pathlib
import subprocess
import sys
import time
import warnings

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from script_data import LINES  # noqa: E402

warnings.filterwarnings("ignore")
from google import genai  # noqa: E402
from google.genai import types  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
AUDIO = ROOT / "audio"
AUDIO.mkdir(exist_ok=True)
MODEL = "gemini-3.1-flash-tts-preview"

# Henri (grave, calme) et Vivienne (claire, rapide) sur edge-tts. Sur Gemini on
# garde l'écart par le timbre seul : la voix n'a ni débit ni hauteur réglables,
# et une consigne de style collée au texte risquerait d'être lue à l'antenne.
VOIX = {"ARCHLORD": "Charon", "UNI": "Puck"}


def env():
    d = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            if line.strip() and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                d[k.strip()] = v.strip()
    return d


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", str(path)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


class Plafond(Exception):
    """Le 429 tient encore après toutes les attentes : on sauve et on repartira."""


def speak(client, i, line, tempo, plafond=6):
    """Une réplique -> audio/line_NN.wav. Retourne (fichier, durée).

    Le palier gratuit est compté à la minute, pas à la journée : un 429 ici ne
    veut pas dire « terminé pour aujourd'hui » mais « ralentis ». On attend donc
    longuement et on réessaie, au lieu d'abandonner la campagne.
    """
    wav = AUDIO / f"line_{i:02d}.wav"
    cfg = types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(
                voice_name=VOIX[line["who"]]))))
    attente = tempo
    for tentative in range(plafond):
        try:
            r = client.models.generate_content(model=MODEL, contents=line["text"],
                                               config=cfg)
            d = r.candidates[0].content.parts[0].inline_data
            raw = AUDIO / f".tmp_{i:02d}.pcm"
            raw.write_bytes(d.data)
            rate = 24000
            for tok in (d.mime_type or "").split(";"):
                if tok.strip().startswith("rate="):
                    rate = int(tok.split("=")[1])
            # On garde les 24 kHz natifs de la voix : les monter à 48 kHz ne crée
            # aucune information et doublerait le poids sur un disque à 3 Go libres.
            # C'est `timeline.py` qui resample à la décodage.
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(rate),
                            "-ac", "1", "-i", str(raw), "-c:a", "pcm_s16le",
                            str(wav)], check=True)
            raw.unlink()
            if wav.stat().st_size > 4000:
                return wav, probe(wav)
            raise RuntimeError(f"piste trop courte ({wav.stat().st_size} o)")
        except Exception as exc:  # noqa: BLE001
            s = str(exc)
            raw = AUDIO / f".tmp_{i:02d}.pcm"
            if raw.exists():
                raw.unlink()
            if "429" in s or "RESOURCE_EXHAUSTED" in s:
                attente = min(300, 45 * (tentative + 1))
                print(f"    plafonné à {i} — pause {attente}s "
                      f"(essai {tentative + 1}/{plafond})", flush=True)
                time.sleep(attente)
                continue
            if tentative == plafond - 1:
                raise
            time.sleep(2 + 2 * tentative)
    raise Plafond(f"réplique {i} encore plafonnée après {plafond} attentes")


def list_voices(client):
    m = client.models.get(model=MODEL, config={"include": "generateContentConfig"})
    sc = m.generate_content_config.speech_config
    for v in sc.voice_config.prebuilt_voices.enum:
        print(f"  {v['name']:16s} {v.get('description','')}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=0, help="s'arrête après N répliques")
    ap.add_argument("--tempo", type=float, default=12.0,
                    help="secondes entre deux appels (le gratuit est compté à la minute)")
    ap.add_argument("--force", action="store_true", help="régénère même si la piste existe")
    ap.add_argument("--voix", action="store_true", help="liste les voix et quitte")
    a = ap.parse_args()

    client = genai.Client(api_key=env()["GEMINI_API_KEY"])
    if a.voix:
        list_voices(client)
        return

    dest = AUDIO / "timings.json"
    deja = {}
    if dest.exists() and not a.force:
        for t in json.loads(dest.read_text()):
            piste = AUDIO / t["file"]
            if (piste.exists() and piste.stat().st_size > 4000
                    and t["text"] == LINES[t["i"]]["text"]):
                deja[t["i"]] = t

    timings, faites, i = [], 0, -1
    for i, line in enumerate(LINES):
        if i in deja:
            timings.append(deja[i])
            continue
        try:
            wav, dur = speak(client, i, line, a.tempo)
        except Exception as exc:  # noqa: BLE001
            dest.write_text(json.dumps(timings, ensure_ascii=False, indent=1))
            if isinstance(exc, Plafond):
                print(f"\nPLAFOND à la réplique {i} — {len(timings)}/{len(LINES)} pistes "
                      f"sauvegardées. Relancer plus tard reprend exactement ici.")
                return 2
            print(f"\nÉCHEC réplique {i} ({line['who']}): {str(exc)[:160]}")
            return 1
        timings.append({"i": i, "who": line["who"], "file": wav.name,
                        "dur": round(dur, 3), "words": [], "text": line["text"]})
        faites += 1
        time.sleep(a.tempo)
        if faites % 10 == 0 or i == len(LINES) - 1:
            dest.write_text(json.dumps(timings, ensure_ascii=False, indent=1))
            print(f"  ... {len(timings)}/{len(LINES)}   "
                  f"{sum(t['dur'] for t in timings) / 60:.1f} min de voix", flush=True)
        else:
            print(f"{i:03d} {line['who']:9s} {dur:5.2f}s  {line['text'][:56]}")
        if a.max and faites >= a.max:
            dest.write_text(json.dumps(timings, ensure_ascii=False, indent=1))
            print(f"\n--max {a.max} atteint ({len(timings)} pistes au total).")
            return 0
    dest.write_text(json.dumps(timings, ensure_ascii=False, indent=1))
    print("TOTAL VOIX:", round(sum(t["dur"] for t in timings), 2), "s")
    return 0


sys.exit(main())
