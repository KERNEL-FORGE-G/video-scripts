#!/usr/bin/env python3
"""Briefs des treize chapitres du « Plateau UniFlow » (60 minutes).

Chaque brief porte les FAITS VÉRIFIÉS du jour — chiffres relevés sur le site en
ligne le 2026-09-23, noms réels, réserves réelles — et le modèle ne fait que les
mettre en voix. Un brief sans fait = une réplique inventée = une publicité qui
ment, donc le bloc FAITS est obligatoire et la consigne « n'ajoute aucun fait »
est répétée.

  python3 build/briefs.py --list
  python3 build/briefs.py --chapter 4 [--chapter 5 ...]
"""
import argparse
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import llm  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "work" / "script"

# ------------------------------------------------------------------ socle commun
FAITS = """FAITS VÉRIFIÉS (source : site en ligne uniflow.kernelforge.codes relevé le
23 septembre 2026 à 16:46, et journal d'état du projet) :
- UniFlow est une plateforme universitaire créée par KERNEL FORGE, une jeune équipe
  d'étudiants en informatique de l'Université de Yaoundé I, Faculté des Sciences,
  à Ngoa-Ekellé. L'équipe est passée à DIX membres. Le fondateur se nomme
  NGHOMSI FEUKOUO RAVEL et se fait appeler Archlord sur la plateforme. La mascotte
  s'appelle Uni. Rachid n'est PAS le fondateur : c'est le prénom du premier vrai
  étudiant.
- Périmètre réel : une seule université partenaire, la Faculté des Sciences, toutes
  filières, de la première année (L1) à la master 1 (M1). Douze filières.
- Ce que le site affiche en direct : 296 unités d'enseignement, 527 séances
  planifiées, 36 salles référencées, 21 comptes (19 étudiants, 4 enseignants),
  48 visites dans la journée.
- Un vrai compte d'étudiant existe depuis le 21 septembre : un étudiant de licence 3
  ICT4D, prénommé Rachid. Avant lui, tout le monde était des comptes de démonstration.
- Côté enseignants, les noms utilisés pour la démonstration sont le professeur Fouda,
  le docteur Nkolo et monsieur Essomba. Huit étudiants fictifs composent la salle de
  démonstration de licence 1 ICT4D, dont Amina Ngo Bassong et Hervé Kamdem.
- La version 1.0.0 est publiée : application Android (83,1 Mo), application Windows
  (18,8 Mo), et le site utilisable dans le navigateur, installable sans magasin
  d'applications. L'empreinte du fichier Android est publiée à côté du bouton pour
  vérifier qu'on a téléchargé le bon.
- Ce que fait la plateforme : emploi du temps, cours et supports, devoirs à rendre,
  notes et moyenne calculée, présence par code à scanner, messages entre comptes,
  forum par cours, statistiques d'assiduité, bulletins imprimables, badges de réussite,
  quatre espaces selon le rôle (étudiant, délégué, enseignant, administration).
- La page « À propos » du site le dit elle-même : « Six piliers, présents sur les
  trois applications avec les mêmes données. » Ces six piliers sont : un emploi du
  temps qui est vraiment le vôtre ; des présences sans feuille de papier ; messages,
  devoirs, notes et forum au même endroit ; la visioconférence sur le poste de
  l'enseignant ; un logiciel conçu pour les coupures ; des rôles vérifiés par la
  plateforme et pas par l'utilisateur.
- Ce que le site promet sur la page d'accueil : « 100% Gratuit & PWA », « Fonctionne
  sans réseau », « Multi-rôles sécurisé ».
- Plus bas, la page des tarifs pose quatre paliers : l'accès académique inclus,
  l'accès personnel à 100 FCFA, le pack enseignant à 500 FCFA, et « sur devis » pour
  un campus entier.
- La présence : le code présenté est lié à une séance précise, il expire, il peut être
  retiré, et le relevé ne s'écrit que si l'étudiant est bien inscrit au cours.
- Le hors réseau : les cours, l'horaire et les notes restent consultables sans
  connexion ; ce qui a été fait hors réseau est rattrapé au retour.
- Une extension existe, appelée Sentinelle : un kiosque de pré-diagnostic santé
  (température, oxygène, pouls, tension) et un module de surveillance de posture et
  de chute, qui décident sur place, sans envoyer d'image à l'extérieur.
- Contacts publics : WhatsApp +237 6 57 63 56 44, un groupe WhatsApp KERNEL FORGE,
  permanence du lundi au vendredi 8h-17h30 heure de Yaoundé.
- La phrase du fondateur, telle qu'elle est écrite sur le site : « Avant UniFlow,
  l'emploi du temps était une photo floue sur WhatsApp qui changeait trois fois
  par semaine. »
- Le forum affiche une note moyenne de 1,0 sur un seul avis, et le premier avis
  est du fondateur lui-même, écrit en vitesse et bourré de fautes.
- Le code source n'est pas publié en entier : une partie seulement est montrée,
  le reste reste fermé pour protéger la plateforme et les données des étudiants.
- Les demandes d'accès personnel sont enregistrées puis validées à la main, après
  vérification. Il n'y a pas de paiement automatique.
"""

RESERVES = """RÉSERVES HONNÊTES (à dire, pas à cacher) :
- Les horaires de la deuxième et de la troisième année d'ICT4D sont provisoires :
  ils ont été écrits par l'équipe en attendant les horaires officiels de la faculté.
  Un vrai étudiant de licence 3 les voit donc comme s'ils étaient vrais. Cela ne
  touche qu'ICT4D, de la première à la troisième année.
- Les alertes n'arrivent que si l'application est ouverte ou récente : fermée,
  elle ne sonne pas.
- Le fichier Android du 1.0.0 est mal signé : le prochain demandera de désinstaller
  celui-ci avant d'installer.
- Le hors réseau, la visioconférence de bureau et l'assistant Uni n'ont jamais été
  essayés à deux machines depuis le changement d'hébergement : c'est écrit et testé
  dans le code, mais pas encore éprouvé dans la vraie vie.
- Le site est lent à l'ouverture sur certains téléphones ; une vague de vitesse est
  en cours.
- Le tableau de bord n'a été vérifié sérieusement qu'en atelier, pas encore partout.
- La page d'accueil dit « 100% Gratuit » et la page des tarifs affiche des paliers à
  100 et 500 FCFA : les deux sont vrais, l'accès étudiant d'une université partenaire
  est gratuit, l'accès personnel hors convention est payant. Si le sujet arrive,
  dire ça, ne pas laisser le spectateur deviner.
- La page « Notre équipe » montre le fondateur en photo, et deux cartes encore
  occupées par des noms de remplissage. On ne montre pas cette page en gros plan.
"""

RULES = """RÈGLES D'ÉCRITURE :
- N'utilise QUE les faits ci-dessus. N'invente aucun chiffre, aucun nom, aucun délai.
- Français uniquement. Pas de mot technique : pas de « base de données », « serveur »,
  « API », « clé », « cloud », « PWA », « APK », « algorithme », « chiffrement »,
  « hébergement ». On dit « ce qui est rangé », « ce qui répond », « le fichier »,
  « sans connexion », « décide sur place ».
- Le rythme : une réplique sur cinq peut être très courte, deux ou trois mots pour
  couper (« Vrai de vrai. », « Chrono ! »). Toutes les autres font entre quinze et
  trente mots, soit douze secondes dites au maximum.
- UNI est vif, second degré, il coupe. ARCHLORD est posé, il rit de lui-même.
- Une ligne par réplique, commencée par « UNI: » ou « ARCHLORD: ».
- Pas de liste, pas de titre, pas de commentaire, pas d'astérisque.
- SEUL LE WEB EST FILMÉ dans cette vidéo : le site, et l'application ouverte dans
  un navigateur, y compris à la largeur d'un téléphone. Ne dis jamais « regarde ce
  que fait l'application Android » ni « voilà le logiciel de bureau » : on annonce
  qu'ils existent et qu'on les télécharge, sans prétendre les montrer.
"""


def brief(num, cible, sujet, broll, extra=""):
    # 21 mots par réplique à 2,4 mots/seconde = 8,7 s, plus la respiration entre
    # les lignes : c'est comme ça que les treize chapitres tombent sur l'heure.
    mots = cible * 21
    return (f"CHAPITRE {num} — {sujet}\n"
            f"Écris exactement {cible} répliques, soit environ {mots} mots au total. "
            f"Si tu rends moins de {int(mots * 0.85)} mots, le chapitre sera trop "
            f"court à l'écran : développe chaque idée au lieu d'ajouter des lignes.\n\n"
            f"{FAITS}\n{RESERVES}\n{RULES}\n"
            f"Écrans montrés pendant ce chapitre (cite-les au bon moment, sans les "
            f"nommer techniquement) : {broll}\n{extra}")


# Les visuels listés ici existent sous video/assets/captures/, avec ce nom exact.
# Tous relevés dans un navigateur : le site, l'application ouverte dans le site,
# ou la même page à la largeur d'un téléphone. Rien d'autre n'est montrable.
CHAPITRES = {
    1: dict(cible=34, sujet="Ouverture du plateau : les deux arrivent, se présentent, "
            "et posent la règle de l'émission — on montre tout, y compris ce qui ne marche pas.",
            broll="aucun écran, juste le plateau",
            extra="Finis sur une annonce : « soixante minutes, sans coupe »."),
    2: dict(cible=40, sujet="Avant. La faculté en papier : la feuille collée au mur, la "
            "photo floue sur WhatsApp, l'annonce lue trois fois et ratée quand même, le "
            "bulletin recopié à la main.",
            broll="live_site_pourquoi.png, live_site_vie_fac.png, live_site_hero.png, "
                  "desktop_accueil.png"),
    3: dict(cible=40, sujet="L'atelier. Qui sont ces dix étudiants de la Faculté des "
            "Sciences de Yaoundé, pourquoi ça s'appelle Kernel Forge, et comment un devoir "
            "de groupe est devenu une plateforme.",
            broll="live_site_kernel_forge.png, live_site_chiffres.png, desktop_a_propos.png"),
    4: dict(cible=62, sujet="La journée d'un étudiant, écran par écran : ce qu'il voit le "
            "matin, son horaire de la semaine, ses cours et supports, ses devoirs à rendre, "
            "ses notes et la moyenne qui se calcule seule.",
            broll="live_app_tableau_de_bord.png, live_app_emploi_du_temps.png, "
                  "live_app_cours.png, live_app_devoirs.png",
            extra="Chapitre discipliné : tu montres la journée de l'étudiant, point. "
                  "Les réserves honnêtes (alertes, signature, site lent, hors réseau "
                  "jamais éprouvé à deux, code fermé) ont leur chapitre plus loin : "
                  "n'en dis pas un mot ici, même pour t'en excuser. Une seule exception : "
                  "la mention des horaires provisoires d'ICT4D, parce qu'ils s'affichent "
                  "à l'écran pendant qu'on parle."),
    5: dict(cible=50, sujet="L'heure juste : la présence. Comment le code qui expire "
            "empêche de pointer pour son copain, ce que voit le délégué, ce que garde "
            "l'administration, et la feuille de présence qui sort toute prête.",
            broll="live_app_delegue.png, live_app_notifications.png, "
                  "live_app_tableau_de_bord.png"),
    6: dict(cible=52, sujet="En face : l'enseignant et l'administration. Poser un devoir, "
            "saisir les notes, créer les comptes des étudiants et des enseignants, voir "
            "l'assiduité de la promotion. Et le fait que personne ne s'inscrit "
            "administration tout seul.",
            broll="live_app_cours.png, live_app_parametres.png, desktop_connexion.png"),
    7: dict(cible=44, sujet="Sans réseau. Le cours à Ngoa-Ekellé quand la connexion tombe : "
            "l'horaire est toujours là, la note enregistrée hors réseau est rattrapée après, "
            "et ce que ça change pour quelqu'un qui paie son data.",
            broll="live_site_piliers.png, live_site_telecharger.png, desktop_telecharger.png"),
    8: dict(cible=46, sujet="Le site qui prend la forme de l'écran qu'on lui donne : "
            "l'ordinateur de la maison, la salle informatique, le téléphone dans la poche. "
            "Archlord précise une fois pour toutes ce qu'on filme ici et ce qu'on ne filme "
            "pas : tout ce qui apparaît à l'écran vient du navigateur. Les versions à "
            "installer existent, elles sont annoncées sur la page de téléchargement avec "
            "leur poids et leur empreinte, mais personne ne les montre dans cette vidéo.",
            broll="desktop_a_propos.png, mobile_a_propos.png, mobile_accueil.png, "
                  "mobile_telecharger.png, desktop_presentation.png"),
    9: dict(cible=44, sujet="La Sentinelle. Le kiosque de pré-diagnostic et l'œil qui "
            "surveille la posture et les chutes, qui décident sur place sans envoyer "
            "d'image. Archlord explique pourquoi c'est le chapitre qui fait douter tout le "
            "monde, et pourquoi ça reste.",
            broll="desktop_sentinelle.png, mobile_sentinelle.png"),
    10: dict(cible=56, sujet="Ce qui n'est PAS prêt. Les horaires provisoires d'ICT4D de la "
            "première à la troisième année, l'alerte qui ne sonne pas application fermée, le "
            "fichier à désinstaller avant le prochain, le hors réseau jamais éprouvé à deux, "
            "le site lent, et le forum à un étoile avec le premier avis du fondateur plein "
            "de fautes.",
            broll="desktop_forum.png, live_site_forum_avis.png, "
                  "live_app_emploi_du_temps.png",
            extra="Ton : on ne s'excuse pas, on assume et on date. C'est le chapitre qui "
                  "rend les autres crédibles."),
    11: dict(cible=50, sujet="Ce qui vient. Les horaires officiels à remplacer, la version "
            "mieux signée, les vraies alertes, la visioconférence éprouvée à deux machines, "
            "le site accéléré, et l'ouverture du code : une partie montrée, pas la totalité, "
            "et pourquoi.",
            broll="live_site_etapes.png, live_site_videotheque.png, desktop_contact.png, "
                  "live_site_contact_equipe.png"),
    12: dict(cible=52, sujet="Pourquoi pas ce qui existe déjà. Sans nommer personne : ce que "
            "font les autres, ce qu'ils ne font pas, et le fait que la messagerie n'est PAS "
            "l'argument — une messagerie, tout le monde en a une. Les vrais atouts : le hors "
            "réseau, le code qui expire, les rôles, le matériel, et que c'est fait ici.",
            broll="live_site_piliers.png, live_app_messagerie.png, live_app_delegue.png, "
                  "live_site_fondateur.png"),
    13: dict(cible=38, sujet="Invitation finale. Aller voir, essayer un compte de "
            "démonstration, mettre un pouce, laisser un commentaire, poster une suggestion "
            "sur le forum, ou pousser la porte du groupe WhatsApp. Remercier, et rendre "
            "l'antenne.",
            broll="live_site_appel.png, desktop_forum.png, live_site_contact_equipe.png"),
}


MODELES = ("gemini-2.5-flash", "gemini-3-flash-preview")
# gemini-3-render-preview refuse les longs briefs d'une traite (HTTP 503 rendu en
# moins d'une seconde, alors que la même clé répond sur un prompt court) : le
# 2.5-flash, lui, sort les 22 répliques complètes. On tente dans cet ordre.


def ecrire(prompt, model=""):
    cle = llm.load_env()["GEMINI_API_KEY"]
    derniers = []
    for i, m in enumerate((model,) if model else MODELES):
        # Le quota gratuit est à la minute, pas à la journée : un 429 après six
        # chapitres d'affilée ne veut pas dire « refusé », mais « attends ».
        for attempt in range(4):
            try:
                return llm.gemini(cle, prompt, m, 12000), m
            except Exception as exc:  # noqa: BLE001
                derniers.append(f"{m} : {exc}")
                if attempt < 3:
                    time.sleep(30 + 45 * attempt + 20 * i)
    raise RuntimeError(" | ".join(derniers))


def generate(n, model="", force=False):
    OUT.mkdir(parents=True, exist_ok=True)
    spec = CHAPITRES[n]
    dest = OUT / f"ch{n:02d}_draft.txt"
    if dest.exists() and not force:
        print(f"ch{n:02d} existe déjà (--force pour réécrire)")
        return
    prompt = brief(n, spec["cible"], spec["sujet"], spec["broll"], spec.get("extra", ""))
    (OUT / f"ch{n:02d}_brief.txt").write_text(prompt, encoding="utf-8")
    text, m = ecrire(prompt, model)
    lines = [ln for ln in text.splitlines() if ln.startswith(("UNI:", "ARCHLORD:"))]
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    mots = sum(len(ln.split(":", 1)[1].split()) for ln in lines)
    print(f"ch{n:02d}  {len(lines):3} répliques / viser {spec['cible']:3}   {mots:4} mots "
          f"~{mots / 2.4 / 60:.1f}min  [{m}]  -> {dest.name}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--chapter", type=int, action="append", default=[])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--model", default="")
    a = ap.parse_args()
    if a.list:
        for n, s in CHAPITRES.items():
            print(f"ch{n:02d}  {s['cible']:3} répliques  {s['sujet'][:88]}")
        return
    todo = sorted(a.chapter or (range(1, 14) if a.all else []))
    for n in todo:
        try:
            generate(n, a.model, a.force)
        except Exception as exc:  # noqa: BLE001
            print(f"ch{n:02d} ÉCHEC : {exc}", flush=True)


if __name__ == "__main__":
    main()
