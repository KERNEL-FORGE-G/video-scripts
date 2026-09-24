"""Script complet de l'émission « Le Plateau UniFlow », sous deux coupes.

Registre publicitaire et dialogue télé. Vocabulaire grand public :
aucun terme technique n'apparaît à l'antenne.

  UNIFLOW_COUPE=60  treize chapitres, ~60 min   (défaut)
  UNIFLOW_COUPE=15  l'ancienne bande, onze segments
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from script_part1 import PART1  # noqa: E402
from script_part2 import PART2  # noqa: E402
from script_part3 import PART3  # noqa: E402
from script_long import PARTS as PARTS60  # noqa: E402

COUPE = os.environ.get("UNIFLOW_COUPE", "60")
LINK = "uniflow.kernelforge.codes"
TITLE = "LE PLATEAU UNIFLOW"
SUBTITLE = "Une émission tournée à Yaoundé — Université de Yaoundé I"

# Henri pour le fondateur, Vivienne pour l'assistant : deux timbres très distincts.
VOICES = {
    "ARCHLORD": dict(voice="fr-FR-HenriNeural", rate="+3%", pitch="-2Hz"),
    "UNI": dict(voice="fr-FR-VivienneMultilingualNeural", rate="+8%", pitch="+18Hz"),
}

LINES = []
for part in (PARTS60 if COUPE == "60" else (PART1, PART2, PART3)):
    for line in part:
        line = dict(line)
        line.update(VOICES[line["who"]])
        line.setdefault("duo", False)
        # Consigne du propriétaire du 2026-09-23 : « refais la vidéo, mais ne mets
        # aucune capture ». Les captures restent dans les fichiers de script, elles
        # ne montent plus à l'antenne — le plateau et ses deux voix suffisent.
        line["broll"] = None
        LINES.append(line)

if __name__ == "__main__":
    words = sum(len(l["text"].split()) for l in LINES)
    print(f"répliques : {len(LINES)}   mots : {words}")
    print(f"durée parlée estimée : {words / 2.75 / 60:.1f} min (+ silences et génériques)")
    segs = [l for l in LINES if l.get("seg")]
    for s in segs:
        print("  ·", s["seg"])
