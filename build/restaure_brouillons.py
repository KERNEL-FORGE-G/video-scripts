"""Reconstitue work/script/chNN_draft.txt à partir de build/script_long.py.

L'assembleur (build/make_script.py) décide le plan, la pose, le duo et la fiche
de données par règles, à partir du seul (chapitre, rang, qui, texte). Les
brouillons ne portent donc que les voix et les mots : ils se reconstituent sans
perte en gardant « QUI: texte » et rien d'autre.

Le contrôle est dans le docstring de make_script.py, pas ici : ce script ne vaut
que si l'assembleur reproduit ensuite script_long.py octet pour octet. Relancer
build/briefs.py serait une autre histoire — il appelle un modèle, réécrirait les
mots, et les sept cent soixante-quinze pistes audio sont cachées sur ces mots.

    python3 build/restaure_brouillons.py
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "build"))
from script_long import PARTS  # noqa: E402

DRAFTS = ROOT / "work" / "script"

if __name__ == "__main__":
    DRAFTS.mkdir(parents=True, exist_ok=True)
    for n, part in enumerate(PARTS, 1):
        corps = "".join(f"{d['who']}: {d['text']}\n" for d in part)
        (DRAFTS / f"ch{n:02d}_draft.txt").write_text(corps, encoding="utf-8")
        print(f"ch{n:02d}  {len(part):3} répliques  {len(corps):6} octets")
    print(f"\n{sum(len(p) for p in PARTS)} répliques dans {DRAFTS.relative_to(ROOT)}")
