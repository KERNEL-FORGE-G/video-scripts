"""Récupère l'horodatage mot à mot (boundary="WordBoundary") sans toucher aux pistes déjà validées."""
import asyncio
import json
import sys
from pathlib import Path

import edge_tts

sys.path.insert(0, str(Path(__file__).parent))
from script_data import LINES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "audio"
SEMAPHORE = asyncio.Semaphore(4)


async def fetch(idx, line):
    async with SEMAPHORE:
        for attempt in range(5):
            try:
                words = []
                comm = edge_tts.Communicate(line["text"], line["voice"], rate=line["rate"],
                                            pitch=line["pitch"], boundary="WordBoundary")
                async for chunk in comm.stream():
                    if chunk["type"] == "WordBoundary":
                        words.append({"t": chunk["text"],
                                      "s": round(chunk["offset"] / 10_000_000, 3),
                                      "e": round((chunk["offset"] + chunk["duration"]) / 10_000_000, 3)})
                if len(words) >= 2:
                    return idx, words
            except Exception:
                await asyncio.sleep(2 + 3 * attempt)
        return idx, []


async def main():
    timings = json.loads((OUT / "timings.json").read_text())
    done, failed = 0, []
    for fut in asyncio.as_completed([fetch(i, l) for i, l in enumerate(LINES)]):
        i, words = await fut
        timings[i]["words"] = words
        if not words:
            failed.append(i)
        done += 1
        if done % 10 == 0:
            print(f"{done}/138", flush=True)
    (OUT / "timings.json").write_text(json.dumps(timings, ensure_ascii=False))
    print("sans mots :", failed)
    print("mots totaux :", sum(len(t["words"]) for t in timings))


asyncio.run(main())
