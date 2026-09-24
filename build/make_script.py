#!/usr/bin/env python3
"""Assemble les treize brouillons en un script de plateau (coupe 60 minutes).

Les brouillons de work/script/ ne portent que des voix et des mots. Il manque ce
que la caméra doit faire : sur quel plateau, avec quelle pose, et quand les deux
personages sont cadrés ensemble. Ce fichier le décide par règles — une pose par
idée, pas par caprice — et écrit build/script_long.py, que script_data.py monte.

  python3 build/make_script.py            # régénère script_long.py
  python3 build/make_script.py --stats    # sans écrire
"""
import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DRAFTS = ROOT / "work" / "script"
DEST = pathlib.Path(__file__).resolve().parent / "script_long.py"

# Titre du gendarme d'antenne + le décor où la partie se tourne. L'appariement
# n'est pas décoratif : la présence se compte dans un amphi, l'antenne muette
# stand sous l'orage, « ce qui n'est pas prêt » est littéralement l'échafaudage,
# et l'invitation se serre de près sur les deux hôtes pour finir.
CHAPITRES = {
    1: ("PREMIÈRE PARTIE — LE PLATEAU", "wide"),
    2: ("DEUXIÈME PARTIE — AVANT UNIFLOW", "compare"),
    3: ("TROISIÈME PARTIE — L'ATELIER", "backstage"),
    4: ("QUATRIÈME PARTIE — LA JOURNÉE D'UN ÉTUDIANT", "campus"),
    5: ("CINQUIÈME PARTIE — L'HEURE DE LA PRÉSENCE", "amphi"),
    6: ("SIXIÈME PARTIE — EN FACE, L'ENSEIGNANT", "forum"),
    7: ("SEPTIÈME PARTIE — MÊME SANS RÉSEAU", "reseau"),
    8: ("HUITIÈME PARTIE — TOUTES LES TAILLES D'ÉCRAN", "demo"),
    9: ("NEUVIÈME PARTIE — LA SENTINELLE", "sentinelle"),
    10: ("DIXIÈME PARTIE — CE QUI N'EST PAS PRÊT", "avenir"),
    11: ("ONZIÈME PARTIE — CE QUI VIENT", "portail"),
    12: ("DOUZIÈME PARTIE — FACE AUX AUTRES", "audience"),
    13: ("DERNIÈRE PARTIE — L'INVITATION", "med"),
}

# Une idée, une pose. L'ordre compte : la première règle gagnante s'applique.
RÈGLES = [
    (r"\b(?:sécur|protèg|confidentiel|personne ne peut|label|rôle)\b",
     "archlord_explain", "uni_shield"),
    (r"\b(?:pas prêt|provisoire|jamais|lent|étoiles?|fautes|limite|tard|manque|oubli)",
     "archlord_thinking", "uni_sorry"),
    (r"\b(?:chiffre|dix|douze|cent|deux-cent|cinq-cent|trente-six|quarante-huit|"
     r"dix-neuf|vingt|seize|milieu)\b", "archlord_explain", "uni_graduate"),
    (r"\b(?:bonjour|salut|bienvenue|rendez|antenne|c'est parti|chrono)\b",
     "archlord_wave", "uni_wave"),
    (r"\b(?:bravo|super|génial|victoire|content|fierté|encore une)\b",
     "archlord_thumbs", "uni_celebrate"),
    (r"\b(?:écrire|construire|atelier|corriger|tester|reprendre|refaire)\b",
     "archlord_laptop", "uni_search"),
    (r"\b(?:pourquoi|comment|qu'est-ce|vraiment|sérieux|donc)\b",
     "archlord_thinking", "uni_thinking"),
    (r"\b(?:regarde|voici|là|ceci|montrer|on ouvre|c'est ici)\b",
     "archlord_pointing", "uni_pointing"),
]
TOURNANT = {"ARCHLORD": ["archlord_explain", "archlord_pointing",
                         "archlord_thinking", "archlord_laptop"],
            "UNI": ["uni_pointing", "uni_thinking", "uni_wave", "uni_search"]}
# Un geste dicté, hors règles : la question qui ouvre sur le nom du fondateur se
# ferme d'un signe vers la plateforme, pas d'une main sur le menton. Les règles
# liraient « comment » et choisiraient uni_thinking — celui-là a été décidé à la
# main une fois, et le rester l'est ici plutôt que dans script_long.py, que le
# générateur doit pouvoir réécrire sans rien perdre.
POSE_DICTEE = {"Et le fondateur, il s'appelle comment ?": "uni_wave"}
RE_PLIQUET = re.compile(r"^(UNI|ARCHLORD):\s*(.+)$")


def parse(n):
    lignes = []
    for raw in (DRAFTS / f"ch{n:02d}_draft.txt").read_text(encoding="utf-8").splitlines():
        m = RE_PLIQUET.match(raw.strip())
        if m:
            lignes.append((m.group(1), re.sub(r"\s+", " ", m.group(2)).strip()))
    return lignes


def pose(qui, texte, k, chap):
    if texte in POSE_DICTEE:
        return POSE_DICTEE[texte]
    for pat, pa, pu in RÈGLES:
        if re.search(pat, texte, re.I):
            return pa if qui == "ARCHLORD" else pu
    # Rien à illustrer : on fait tourner la gestuelle du plateau. Sans ça, deux
    # poses absorberaient les trois quarts de l'heure et le plan se figerait.
    return TOURNANT[qui][(k + chap) % len(TOURNANT[qui])]


def shot(chap, k, total, qui):
    _, base = CHAPITRES[chap]
    # La règle d'avant envoyait la première et la dernière réplique de chaque
    # chapitre, plus une sur neuf, seules sur « wide » : avec sept plaques pour
    # treize parties, cela faisait un plan large du studio perdu au milieu de
    # l'amphithéâtre. Maintenant que chaque partie a son décor, c'est lui qui
    # s'installe seul ; « wide » ne sert plus qu'à ouvrir l'émission.
    if chap == 1 and k == 0:
        return "wide"
    if base == "med":                   # l'invitation se joue déjà serrée
        return "wide" if k % 9 == 5 else "med"
    if k % 9 == 5:
        return "med"
    return base if qui == "ARCHLORD" or k % 3 else "med"


# Fiche de données posée à l'antenne pendant que le plateau parle : la consigne
# du propriétaire (23 septembre 2026) est de ne montrer aucune capture, mais de
# faire apparaître de temps en temps un bloc chiffré. Tous ces chiffres viennent
# de la base vérifiée de build/briefs.py, relevée sur le site le 23 septembre.
BLOCS = {
    1: [("SUR LE PLATEAU", [("Équipe", "10 étudiants"),
                            ("Université", "Yaoundé I"),
                            ("Campus", "Ngoa-Ekellé")])],
    2: [("AVANT UNIFLOW", [("Emploi du temps", "une photo"),
                           ("Changements", "3 par semaine"),
                           ("Canal", "WhatsApp")])],
    3: [("L'ATELIER", [("Version publiée", "1.0.0"),
                       ("Filières couvertes", "12"),
                       ("Années", "de L1 à M1")])],
    4: [("LA JOURNÉE D'UN ÉTUDIANT", [("Unités", "296"),
                                      ("Séances", "527"),
                                      ("Salles", "36")]),
        ("NOTES ET SUIVI", [("Notes", "en ligne"),
                            ("Moyenne", "calculée"),
                            ("Assiduité", "suivie"),
                            ("Bulletin", "imprimable")])],
    5: [("L'HEURE DE LA PRÉSENCE", [("Code", "par séance"),
                                    ("Validité", "limitée"),
                                    ("Contrôle", "à l'inscription")])],
    6: [("EN FACE, L'ENSEIGNANT", [("Comptes", "21"),
                                   ("Étudiants", "19"),
                                   ("Enseignants", "4")])],
    7: [("MÊME SANS RÉSEAU", [("Cours", "lisibles"),
                              ("Horaire", "lisible"),
                              ("Notes", "lisibles")])],
    8: [("TROIS PORTES D'ENTRÉE", [("Navigateur", "installable"),
                                   ("Android", "83,1 Mo"),
                                   ("Windows", "18,8 Mo")])],
    9: [("LA SENTINELLE", [("Mesures", "4"),
                           ("Posture", "décidée sur place"),
                           ("Images envoyées", "aucune")])],
    10: [("CE QUI N'EST PAS PRÊT", [("Horaires L2-L3", "provisoires"),
                                    ("Tableau de bord", "à valider"),
                                    ("Avis sur le forum", "1")])],
    11: [("CE QUI VIENT", [("Premier compte", "21 septembre"),
                           ("Visites du jour", "48"),
                           ("Comptes de démo", "8")])],
    12: [("FACE AUX AUTRES", [("Code montré", "en partie"),
                              ("Code fermé", "le reste"),
                              ("Pourquoi", "protéger")])],
    13: [("LES TARIFS", [("Accès académique", "inclus"),
                         ("Accès personnel", "100 FCFA"),
                         ("Pack enseignant", "500 FCFA"),
                         ("Campus entier", "sur devis")]),
         ("NOUS JOINDRE", [("Permanence", "8h - 17h30"),
                           ("Jours", "lundi - vendredi"),
                           ("Groupe", "WhatsApp")])],
}


# Où chaque fiche se pose : (numéro du bloc, numéro d'échange dans le chapitre).
# Ailleurs, la première arrive au quatrième échange, la seconde au milieu.
PLACES = {13: [(0, 27), (1, 15)]}


def build():
    parts, tot = [], 0
    for chap in sorted(CHAPITRES):
        lignes = parse(chap)
        if not lignes:
            sys.exit(f"chapitre {chap} vide — relancer build/briefs.py")
        titre, _ = CHAPITRES[chap]
        blocs = BLOCS[chap]
        places = {k: n for n, k in PLACES.get(chap, [(0, 3), (1, len(lignes) // 2)])
                  if n < len(blocs) and k < len(lignes)}
        out = []
        for k, (qui, texte) in enumerate(lignes):
            d = dict(who=qui, shot=shot(chap, k, len(lignes), qui),
                     pose=pose(qui, texte, k, chap), text=texte)
            if k == 0:
                d["seg"] = titre
            if k in places:
                d["tech"] = blocs[places[k]]
            # Le poing-ensemble ferme un chapitre et ponctue les accords, jamais
            # deux fois d'affilée : c'est le seul plan où les deux sont collés.
            if k == len(lignes) - 1 or (k and k % 17 == 0 and qui == "UNI"):
                d["duo"] = True
            out.append(d)
        parts.append(out)
        tot += len(out)
    return parts, tot


def ecrire(parts):
    lignes = ['"""Coupe 60 minutes : les treize chapitres du Plateau UniFlow.',
              "",
              "Généré par build/make_script.py à partir de work/script/chNN_draft.txt.",
              "Ne pas éditer ici : corriger le brouillon et relancer l'assembleur.",
              '"""', ""]
    for i, part in enumerate(parts, 1):
        lignes.append(f"CH{i:02d} = [")
        for d in part:
            champs = ([("seg", d["seg"])] if "seg" in d else []) \
                + [(k, d[k]) for k in ("who", "shot", "pose", "text")] \
                + ([("duo", True)] if d.get("duo") else []) \
                + ([("tech", d["tech"])] if d.get("tech") else [])
            lignes.append("    dict(" + ", ".join(f"{k}={v!r}" for k, v in champs) + "),")
        lignes.append("]\n")
    lignes.append("PARTS = [" + ", ".join(f"CH{i:02d}" for i in range(1, 14)) + "]")
    DEST.write_text("\n".join(lignes) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", action="store_true")
    a = ap.parse_args()
    parts, tot = build()
    mots = sum(len(d["text"].split()) for p in parts for d in p)
    duo = sum(1 for p in parts for d in p if d.get("duo"))
    print(f"{tot} répliques / {len(parts)} chapitres   {mots} mots   "
          f"~{mots / 2.4 / 60:.1f} min de voix   {duo} plans à deux")
    for i, p in enumerate(parts, 1):
        m = sum(len(d["text"].split()) for d in p)
        print(f"  ch{i:02d} {len(p):3} répliques {m:5} mots ~{m / 2.4 / 60:4.1f}min  "
              f"{CHAPITRES[i][0][:44]}")
    if not a.stats:
        ecrire(parts)
        print("écrit :", DEST.name)


if __name__ == "__main__":
    main()
