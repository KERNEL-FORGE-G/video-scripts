"""Voix : une piste MP3 par réplique + horodatage mot à mot (edge-tts)."""
import asyncio
import json
import subprocess
import sys
from pathlib import Path

import edge_tts

sys.path.insert(0, str(Path(__file__).parent))
from script_data import LINES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "audio"
OUT.mkdir(exist_ok=True)


def probe(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


async def speak(idx, line):
    mp3 = OUT / f"line_{idx:02d}.mp3"
    if mp3.exists():
        mp3.unlink()
    last = None
    for attempt in range(4):
        try:
            words = []
            # `boundary` vaut SentenceBoundary par défaut depuis edge-tts 7 : sans
            # le demander explicitement, aucun WordBoundary ne remonte et les
            # sous-titres retombent sur la répartition approximative du timeline.
            comm = edge_tts.Communicate(line["text"], line["voice"],
                                        rate=line["rate"], pitch=line["pitch"],
                                        boundary="WordBoundary")
            with open(mp3, "wb") as fh:
                async for chunk in comm.stream():
                    if chunk["type"] == "audio":
                        fh.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        words.append({
                            "t": chunk["text"],
                            "s": chunk["offset"] / 10_000_000,
                            "e": (chunk["offset"] + chunk["duration"]) / 10_000_000,
                        })
            if mp3.stat().st_size > 2000:
                return mp3, words
            last = RuntimeError(f"piste trop courte ({mp3.stat().st_size} o)")
        except Exception as exc:  # réseau instable : on réessaie
            last = exc
            await asyncio.sleep(2 + 2 * attempt)
    raise last


async def main():
    dest = OUT / "timings.json"
    # 775 répliques passent par le réseau : la piste est sauvegardée au fil de
    # l'eau, et une piste déjà écrite n'est pas relancée. Un plantage à la
    # sixième minute ne coûte donc pas les cinq cent quatre-vingt-dix autres.
    deja = {}
    if dest.exists():
        for t in json.loads(dest.read_text()):
            piste = OUT / t["file"]
            if (piste.exists() and piste.stat().st_size > 2000
                    and t["text"] == LINES[t["i"]]["text"]):
                deja[t["i"]] = t
    timings, faites = [], 0
    for i, line in enumerate(LINES):
        if i in deja:
            timings.append(deja[i])
            continue
        mp3, words = await speak(i, line)
        dur = probe(mp3)
        timings.append({"i": i, "who": line["who"], "file": mp3.name,
                        "dur": round(dur, 3), "words": words,
                        "text": line["text"]})
        faites += 1
        if faites % 10 == 0:
            dest.write_text(json.dumps(timings, ensure_ascii=False, indent=1))
            print(f"  ... {i + 1}/{len(LINES)}   "
                  f"{sum(t['dur'] for t in timings) / 60:.1f} min de voix", flush=True)
        else:
            print(f"{i:03d} {line['who']:9s} {dur:5.2f}s  {line['text'][:58]}")
    (OUT / "timings.json").write_text(json.dumps(timings, ensure_ascii=False, indent=1))
    print("TOTAL VOIX:", round(sum(t["dur"] for t in timings), 2), "s")


asyncio.run(main())
