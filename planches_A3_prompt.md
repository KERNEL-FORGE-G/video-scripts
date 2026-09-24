# Prompt pour Lovable — 3 planches A3 de toutes les scènes du « Plateau UniFlow »

**Mode d'emploi** : copier tout ce qui suit la ligne `COLLER À PARTIR D'ICI` dans Lovable.
Le fichier décrit l'inventaire complet des scènes de la vidéo publicitaire « Le Plateau UniFlow »
(60 min, 16/9, 25 i/s, en français). Les 3 planches A3 doivent tenir ce tout, sans rien inventer.

COLLER À PARTIR D'ICI

---

## Ce que tu construis

Une page web unique, en français, qui affiche **exactement 3 planches au format A3 portrait
(297 × 420 mm)**, chacune imprimable sur une seule feuille sans rien qui déborde. Chaque planche
regroupe **toutes les scènes dont la vidéo a besoin**, dans un seul des trois rôles ci-dessous.
Aucune scène n'est absente, aucune scène n'est inventée.

| Planche | Rôle | Contenu | Grille |
|---|---|---|---|
| 1/3 | **Les décors** | 8 plans d'arrière-plan 16:9 | 2 colonnes × 4 rangs |
| 2/3 | **Les personnages** | 14 poses détourées + 2 fiches d'identité | 4 colonnes × 4 rangs |
| 3/3 | **Les cartons** | 13 cartons de chapitre + 15 fiches de données + carton-titre + carton final | 5 colonnes × 6 rangs |

## Comment chaque scène se présente

Une case = une scène. Chaque case contient, dans cet ordre :

1. **la référence** en monospace, ex. `DEC-03 · plate_demo` ;
2. **le visuel** (zone illustrée au ratio indiqué, fond hachuré si le visuel n'existe pas encore) ;
3. **le format attendu** : `2048 × 1152 px`, `896 × 1152 px`, ou `1920 × 1080 px` ;
4. **l'usage à l'antenne** : le minuteur et le chapitre, ex. `00:12 → 03:51 · chap. 1 « Le plateau »` ;
5. **une légende d'une ligne**, en français, qui dit ce que la caméra montre ;
6. **le prompt de génération**, dans un bloc copiable en un clic (préfixe `copier`).

## Charte visuelle à respecter au pixel

- Bleu nuit `#1E3A8A` · encre `#070C1E` · cyan `#38D6FF` (accent UNI) · orange `#F98226`
  (accent ARCHLORD, barres et titres de fiche) · blanc `#FFFFFF` · rouge antenne `#E83E3E`.
- Fond de page : encre `#070C1E`. Cartes : bleu nuit très sombre, liseré de 1 px, coin arrondi 6 px.
- Une seule famille de caractères, sans-serif grotesque (fallback `DejaVu Sans`, `Arial`).
  Titres en gras, corps 9 à 11 pt à l'impression, aucune graisse fantaisiste.
- Pied de planche obligatoire : `Le Plateau UniFlow — planche n/3 — Université de Yaoundé I, Ngoa-Ekellé`,
  la date du jour à droite, un liseré orange de 3 mm en tête de chaque planche.
- Contraste AA partout ; les cases doivent rester lisibles à 25 cm et à 100 % d'impression.

## Les deux personnages (ils apparaissent sur 2 des 3 planches, toujours identiques)

- **ARCHLORD** : étudiant camerounais, sweat à capuche bleu, badge au cou, jean sombre, baskets
  noires. Tempérament : curieux, direct, il pose les questions que le public se pose. Accent orange.
- **UNI** : petite mascotte robot blanche et bleu marine, casquette de lauréat, cape orange, visage-écran
  qui exprime l'émotion. Tempérament : pédagogue, rassurant, jamais moqueur. Accent cyan.
- Même éclairage (key chaude à 45°, rim cyan), même épaisseur de trait, même palette sur les 14 poses.
  Fond transparent ou fond vert uni à détourer, jamais un décor.

## Planche 1/3 — les décors (8 scènes, 16:9, 2048 × 1152 px)

| Réf. | Fichier | Ce que montre la scène | Usage à l'antenne |
|---|---|---|---|
| DEC-01 | `plate_wide` | Plateau télé très large : deux personnages debout face caméra, sol sombre réfléchissant, grand écran courbe bleuté derrière, halo de projecteurs | chapitres 1, 3, 4, 6, 11, 13 et la sortie |
| DEC-02 | `plate_medium` | Même plateau, plan moyen : les personnages aux deux tiers, l'écran courbe occupe le fond | passages d'explication |
| DEC-03 | `plate_demo` | Plateau serré côté démonstration : les deux personnages plus grands, un plan de travail bas entre eux | chapitres « la journée », « la présence » |
| DEC-04 | `plate_campus` | Extérieur campus : bâtiment moderne de l'université, palmiers, panneau d'affichage vide, lumière de fin d'après-midi | chapitres « ce qui n'est pas prêt », « ce qui vient » |
| DEC-05 | `plate_compare` | Plateau à deux zones, gauche éteinte / droite allumée, pour mettre côte à côte « avant » et « après » | chapitres 2 et 12 |
| DEC-06 | `plate_audience` | Vue depuis le fond du plateau, silhouettes floues du public au premier plan, les deux personnages au lointain | chapitres « l'enseignant », « sans réseau » |
| DEC-07 | `plate_backstage` | Coulisses : câbles, caisses, un monitor éteint, ambiance de préparation | passages d'équipe et de coulisses |
| DEC-08 | `plate_outro` | Reprise de DEC-01 assombrie de 40 %, pour porter les cartons de la fin | dernières secondes |

Contraintes des décors : plateau imaginaire, **aucune interface réelle, aucune capture d'écran, aucun
téléphone ni ordinateur montré comme maquette**. Les écrans du décor restent des surfaces abstraites
bleutées, floues, sans texte lisible. Campus de Yaoundé : végétation tropicale, lumière chaude,
étudiants camerounais.

## Planche 2/3 — les personnages (14 poses + 2 fiches, 896 × 1152 px, détourées)

| Réf. | Personnage | Pose | Légende à imprimer sous la case |
|---|---|---|---|
| PER-01 | UNI | `uni_wave` | salue le public |
| PER-02 | UNI | `uni_pointing` | montre l'écran du fond |
| PER-03 | UNI | `uni_thinking` | cherche la réponse |
| PER-04 | UNI | `uni_search` | fouille dans les horaires |
| PER-05 | UNI | `uni_shield` | protège les données |
| PER-06 | UNI | `uni_sorry` | annonce ce qui n'est pas prêt |
| PER-07 | UNI | `uni_celebrate` | fête une étape |
| PER-08 | UNI | `uni_graduate` | casquette de lauréat, promotion |
| PER-09 | ARCHLORD | `archlord_wave` | salue, ouvre l'émission |
| PER-10 | ARCHLORD | `archlord_pointing` | interpelle UNI |
| PER-11 | ARCHLORD | `archlord_thinking` | doute, questionne |
| PER-12 | ARCHLORD | `archlord_explain` | développe une idée |
| PER-13 | ARCHLORD | `archlord_laptop` | travaille, saisit une présence |
| PER-14 | ARCHLORD | `archlord_thumbs` | valide, rassure |

Deux cases restantes (PER-15, PER-16) : **fiches d'identité** — silhouette complète de chaque
personnage cotée (hauteur relative au cadre, pied posé au sol du décor, ombre de contact, reflet
sur le sol, halo de projecteur). Ces deux fiches servent de gabarit : tout personnage dessiné plus
tard doit s'y aligner.

## Planche 3/3 — les cartons (30 scènes, 1920 × 1080 px, texte intégral à respecter)

**Carton-titre (1)** — `TIT-00` : mire de régie, puis titre **LE PLATEAU UNIFLOW**, sous-titre
*Une émission tournée à Yaoundé — Université de Yaoundé I*, bandeau *Soixante minutes pour tout voir,
sans coupe*, adresse `uniflow.kernelforge.codes`.

**Cartons de chapitre (13)** — `CHA-01` à `CHA-13`, même gabarit : numéro `n / 13`, titre, liseré
orange. Textes exacts, dans l'ordre :

1. PREMIÈRE PARTIE — LE PLATEAU · 2. DEUXIÈME PARTIE — AVANT UNIFLOW · 3. TROISIÈME PARTIE — L'ATELIER ·
4. QUATRIÈME PARTIE — LA JOURNÉE D'UN ÉTUDIANT · 5. CINQUIÈME PARTIE — L'HEURE DE LA PRÉSENCE ·
6. SIXIÈME PARTIE — EN FACE, L'ENSEIGNANT · 7. SEPTIÈME PARTIE — MÊME SANS RÉSEAU ·
8. HUITIÈME PARTIE — TOUTES LES TAILLES D'ÉCRAN · 9. NEUVIÈME PARTIE — LA SENTINELLE ·
10. DIXIÈME PARTIE — CE QUI N'EST PAS PRÊT · 11. ONZIÈME PARTIE — CE QUI VIENT ·
12. DOUZIÈME PARTIE — FACE AUX AUTRES · 13. DERNIÈRE PARTIE — L'INVITATION

**Fiches de données (15)** — `FIC-01` à `FIC-15`, carte sombre à gauche du cadre, titre orange,
ligne de séparation, étiquette à gauche / valeur à droite. Contenu exact, ne changer aucun nombre :

| Réf. | Titre | Lignes |
|---|---|---|
| FIC-01 | SUR LE PLATEAU | Équipe : 10 étudiants · Université : Yaoundé I · Campus : Ngoa-Ekellé |
| FIC-02 | AVANT UNIFLOW | Emploi du temps : une photo · Changements : 3 par semaine · Canal : WhatsApp |
| FIC-03 | L'ATELIER | Version publiée : 1.0.0 · Filières couvertes : 12 · Années : de L1 à M1 |
| FIC-04 | LA JOURNÉE D'UN ÉTUDIANT | Unités : 296 · Séances : 527 · Salles : 36 |
| FIC-05 | NOTES ET SUIVI | Notes : en ligne · Moyenne : calculée · Assiduité : suivie · Bulletin : imprimable |
| FIC-06 | L'HEURE DE LA PRÉSENCE | Code : par séance · Validité : limitée · Contrôle : à l'inscription |
| FIC-07 | EN FACE, L'ENSEIGNANT | Comptes : 21 · Étudiants : 19 · Enseignants : 4 |
| FIC-08 | MÊME SANS RÉSEAU | Cours : lisibles · Horaire : lisible · Notes : lisibles |
| FIC-09 | TROIS PORTES D'ENTRÉE | Navigateur : installable · Android : 83,1 Mo · Windows : 18,8 Mo |
| FIC-10 | LA SENTINELLE | Mesures : 4 · Posture : décidée sur place · Images envoyées : aucune |
| FIC-11 | CE QUI N'EST PAS PRÊT | Horaires L2-L3 : provisoires · Tableau de bord : à valider · Avis sur le forum : 1 |
| FIC-12 | CE QUI VIENT | Premier compte : 21 septembre · Visites du jour : 48 · Comptes de démo : 8 |
| FIC-13 | FACE AUX AUTRES | Code montré : en partie · Code fermé : le reste · Pourquoi : protéger |
| FIC-14 | NOUS JOINDRE | Permanence : 8h - 17h30 · Jours : lundi - vendredi · Groupe : WhatsApp |
| FIC-15 | LES TARIFS | Accès académique : inclus · Accès personnel : 100 FCFA · Pack enseignant : 500 FCFA · Campus entier : sur devis |

**Carton final (1)** — `FIN-00` : signature du Plateau UniFlow, trois accroches empilées, quatre
cartes d'appel qui montent une à une — *aimer*, *commenter*, *visiter la plateforme*, *proposer sur
le forum ou dans le groupe WhatsApp* — et l'adresse `uniflow.kernelforge.codes`.

## Les règles de fond, non négociables

- **Tout en français.** Accents corrects, apostolales typographiques, pas de mot anglais inutile.
- **C'est une publicité, pas une documentation.** Aucun terme technique : pas de clé, pas
  d'interface de programmation, pas de base de données, pas de serveur, pas de dépôt.
- **Aucune capture d'écran de l'application**, aucun mockup de téléphone ni de fenêtre d'ordinateur :
  la vidéo se joue entièrement sur le plateau et le campus.
- **Ne pas inventer un seul chiffre.** Les 15 fiches portent les seules données qui existent ; toute
  autre valeur est interdite.
- Les horaires **provisoires** ne concernent que la filière informatique de gestion des TIC en
  licence 1, 2 et 3 : le dire ainsi, sans étendre à d'autres filières.
- Le code ouvert : **une partie est montrée, l'autre reste fermée pour protéger les comptes** — ne
  jamais présenter le projet comme entièrement ouvert, ni comme caché.
- Le sujet n'est **pas la messagerie** : WhatsApp n'apparaît qu'en canal de contact et de groupe.

## Ce que la page doit savoir faire

- Un bouton **« Imprimer / PDF »** qui n'imprime que les 3 planches, une par page A3, sans les boutons.
- Un bouton **« Exporter les planches en PNG »** à 300 dpi (3508 × 4961 px par planche).
- Un bouton **« manifest.json »** qui télécharge la liste des 58 scènes :
  `{"ref", "planche", "fichier", "largeur", "hauteur", "chapitre", "depuis", "jusqu", "legende", "prompt"}`.
- Un champ de recherche qui filtre les cases par référence, personnage ou chapitre.
- Un compteur visible : `58 scènes · 8 décors · 16 personnages · 34 cartons`.

## Critères d'acceptation

1. Trois sections, trois pages A3 à l'impression, zéro débord, zéro case coupée.
2. 58 cases : 8 décors, 14 poses + 2 gabarits, 13 chapitres, 15 fiches, 1 titre, 1 fin, 2 incrustations
   d'antenne (pastille « EN DIRECT » rouge pulsée, cartouche de nom cyan/orange).
3. Chaque case a sa référence, son ratio, son minuteur d'antenne, sa légende et son prompt copiable.
4. Les 15 fiches affichent mot pour mot les valeurs du tableau ci-dessus.
5. Aucun texte technique interdit, aucune capture d'interface, aucun anglais.
6. Un seul fichier, sans service externe ni police téléchargée depuis un CDN.
