#!/usr/bin/env python3
"""Relit les brouillons des treize chapitres avant de les monter en script.

Ne corrige rien : il signale. Ce qu'il vérient vient d'une règle simple — dans une
publicité, une réplique qui dépasse le fait vérifié ou qui glisse vers le vocabulaire
technique coûte plus cher qu'elle ne rapporte.

  python3 build/check_script.py            # tous les chapitres
  python3 build/check_script.py 4 10       # deux chapitres
"""
import pathlib
import re
import sys

OUT = pathlib.Path(__file__).resolve().parent.parent / "work" / "script"

# Ce que la vidéo est censée dire, relevé sur le site en ligne et dans le journal
# d'état le 2026-09-23. Un nombre hors de cette liste = une invention à vérifier.
CHIFFRES = {
    "1", "2", "3", "4", "6", "8", "10", "12", "21", "36", "48", "19", "1646", "23",
    "296", "527", "1.0.0", "83,1", "18,8", "100", "500", "17", "30", "60", "1", "1,0", "0",
    "un", "une", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf",
    "dix", "onze", "douze", "quinze", "seize", "vingt", "cent", "mille",
    "dix-neuf", "vingt et un", "trente-six", "quarante-huit", "cinquante-deux",
    "soixante", "deux-cent", "cinq-cent", "quatre-vingt", "dixième",
}
NOMS = {
    "UniFlow", "KERNEL", "FORGE", "Kernel", "Forge", "Archlord", "Uni", "Rachid",
    "Nghomsi", "Feukouo", "Ravel",
    "Fouda", "Nkolo", "Essomba", "Amina", "Ngo", "Bassong", "Hervé", "Kamdem",
    "Yaoundé", "Ngoa", "Ekellé", "ICT4D", "WhatsApp", "Sentinelle", "Faculté",
    "Sciences", "Licence", "Master", "Android", "Windows", "FCFA", "Cameroun",
    "L'Équipe", "Rentrée", "Afrique", "Fleuve", "Sanaga", "Université",
    "Docteur", "Monsieur", "Professeur", "Internet", "Kernel", "Page", "Oui",
}
# Vocabulaire interdit : le public n'a pas à entendre l'envers du décor.
INTERDITS = [
    r"\bAPI\b", r"\bbase de données\b", r"\bserveur\b", r"\bcloud\b", r"\bPWA\b",
    r"\bAPK\b", r"\balgorithme\b", r"\bchiffrement\b", r"\bhéberge?ment\b",
    r"\bJSON\b", r"\bwebhook\b", r"\btoken\b", r"\bbackend\b", r"\bfrontend\b",
    r"\bclé (d'|du |de la )?\w+", r"\bsha-?256\b", r"\bendpoint\b", r"\bscript\b",
]
# Pas interdit, mais le public comprend mieux en français courant.
A_REFORMULER = [
    r"\bsynchronis\w*\b", r"\bmis en cache\b", r"\ble cache\b", r"\bcommit\b", r"\bmerge\b",
    r"\bdéploi(e|é|ment)\b", r"\bmigration\b", r"\bseed\b", r"\binterface\b",
    r"\bparamétr\w*\b", r"\bback-?up\b", r"\bmodule\b", r"\brépertoire\b",
]
# Le modèle a pris l'habitude de nommer ses propres consignes : « c'est une de nos
# réserves honnêtes » n'est pas une réplique, c'est une note de bas de page.
META = [r"réserve honnête", r"fait vérifié", r"consigne", r"chapitre \d",
        r"le brief", r"notre journal", r"on ne doit pas", r"règle de l'émission"]

CHIFFRE_RE = re.compile(r"\b\d[\d.,]*\b")
# Nombres écrits en toutes lettres qu'on attend dans l'émission. Le modèle écrit
# parfois « vingt-neuf-six » pour 296 : la liste de contrôle sert à ce que chaque
# nombre épelé soit relu, pas à deviner s'il est juste.
EPEPES = ["un", "une", "deux", "trois", "quatre", "cinq", "six", "sept", "huit",
          "dix", "onze", "douze", "quinze", "seize", "dix-huit", "dix-neuf",
          "vingt", "vingt-et-un", "trente-six", "quarante-huit", "cent", "mille",
          "deux-cent", "quatre-vingt-seize", "cinq-cent", "vingt-sept",
          "quatre-vingt-trois", "soixante", "cinquante-deux", "quatorze"]
EPELE_RE = re.compile(r"\b[a-zà-ü]+(?:-[a-zà-ü]+)*\b", re.I)
# Majuscule en milieu de phrase : c'est là que se cachent les noms propres à
# vérifier. Celle qui ouvre la réplique ou suit un point n'intéresse personne.
MOT_MAJ_RE = re.compile(r"\b[A-ZÀ-Ü][a-zà-ü]{2,}\b")


def mots(texte):
    return len(re.findall(r"[\w'’-]+", texte, re.UNICODE))


def check(n):
    path = OUT / f"ch{n:02d}_draft.txt"
    if not path.exists():
        print(f"ch{n:02d}  ABSENT")
        return 0, 0
    lignes = path.read_text(encoding="utf-8").splitlines()
    repliques = [(i + 1, l) for i, l in enumerate(lignes)
                 if l.startswith(("UNI:", "ARCHLORD:"))]
    problemes, entiers = [], []
    if len(repliques) != len(lignes):
        problemes.append(f"  {len(lignes) - len(repliques)} ligne(s) hors réplique")

    total_mots = 0
    for no, ligne in repliques:
        qui, _, corps = ligne.partition(":")
        corps = corps.strip()
        total_mots += mots(corps)
        for pat in INTERDITS:
            m = re.search(pat, corps)
            if m:
                problemes.append(f"  L{no} INTERDIT « {m.group(0)} »")
        for pat in A_REFORMULER:
            m = re.search(pat, corps, re.I)
            if m:
                problemes.append(f"  L{no} à dire autrement : « {m.group(0)} »")
        for pat in META:
            m = re.search(pat, corps, re.I)
            if m:
                problemes.append(f"  L{no} parle de sa propre consigne : « {m.group(0)} »")
        nm = mots(corps)
        if nm > 32:
            problemes.append(f"  L{no} {nm} mots, à dire en une respiration")
        if corps and not corps[-1] in ".!?…":
            problemes.append(f"  L{no} finit sans ponctuation : …{corps[-24:]}")
        for x in CHIFFRE_RE.findall(corps):
            if x.rstrip(".,") not in CHIFFRES:
                problemes.append(f"  L{no} chiffre à vérifier « {x} »")
        for mot in EPELE_RE.findall(corps):
            if mot.lower() in EPEPES:
                entiers.append(f"ch{n:02d} L{no:3}  {mot}")
        for m in MOT_MAJ_RE.finditer(corps):
            avant = corps[:m.start()].rstrip()
            if avant and avant[-1] in ".!?…:" or not avant:
                continue
            if m.group(0) not in NOMS:
                problemes.append(f"  L{no} nom inconnu « {m.group(0)} »")
    for i in range(2, len(repliques)):
        a, b, c = (repliques[i - 2][1].split(":")[0], repliques[i - 1][1].split(":")[0],
                   repliques[i][1].split(":")[0])
        if a == b == c:
            problemes.append(f"  L{repliques[i][0]} {a} parle trois fois de suite")

    for e in entiers:
        print("   nombre épelé, à relire :", e)
    minutes = total_mots / 2.4 / 60
    etat = "OK " if not problemes else f"{len(problemes)} signalement(s)"
    print(f"ch{n:02d}  {len(repliques):3} répliques  {total_mots:5} mots  "
          f"{minutes:4.1f} min  {etat}")
    for p in problemes:
        print(p)
    return len(repliques), total_mots


def main():
    nums = [int(x) for x in sys.argv[1:]] or list(range(1, 14))
    tot = [check(n) for n in nums]
    r, m = sum(t[0] for t in tot), sum(t[1] for t in tot)
    print(f"\nTOTAL  {r} répliques  {m} mots  ~{m / 2.4 / 60:.1f} min de voix")


if __name__ == "__main__":
    main()
