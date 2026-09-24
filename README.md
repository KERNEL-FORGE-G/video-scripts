# Le Plateau UniFlow — chaîne de production vidéo

Dépôt **`KERNEL-FORGE-G/video-scripts`** : tout ce qui fabrique la vidéo
publicitaire « Le Plateau UniFlow », de la réplique écrite jusqu'au MP4 contrôlé.
La racine de ce dépôt est l'ancien dossier `video/` du projet KERNEL FORGE ;
tous les chemins ci-dessous partent d'elle.

**Ce que produit la chaîne**

| | |
|---|---|
| Format | 1280×720 à 25 i/s (cadre dessiné en 1920×1080 puis réduit), H.264 + AAC 48 kHz |
| Maître | 60:11 — 3611,766 s, 775 répliques, 790 plans, 90 294 images, 13 chapitres |
| Coupe courte | 15:00 — 900,000 s, 22 500 images, assemblée sans ré-encodage |
| plateau | deux personnages (Archlord, Uni) sur 13 décors composés en Kenney CC0 |
| Langue | français, registre pub télé, **zéro vocabulaire technique à l'antenne** |
| Captures d'écran | **aucune** — le plateau et ses deux voix suffisent |

Rien ici ne touche la plateforme UniFlow : elle n'est que citée. Le dépôt est
autonome — **sans aucune clé API, il rend déjà l'heure complète** (les décors sont
composés localement, les voix viennent des MP3 livrés).

Tu es un agent chargé de reprendre ce chantier sans lire les 200 lignes
précédentes ? **[`AI_STUDIO.md`](AI_STUDIO.md)** : diagnostic, ordre de
récupération, génération des visuels manquants, critères d'acceptation chiffrés.

---

## 1. Arborescence

```
run.sh                 pilote la construction complète, reprenable
blender.sh             contour local : le snap blender est bloqué par NoNewPrivs
build/
  script_long.py       les 13 chapitres, 775 répliques (source du texte)
  script_part1..3.py   l'ancienne coupe de 15 min, 11 segments
  script_data.py       pont texte → moteur ; COUPE = env UNIFLOW_COUPE (ligne 19)
  make_script.py       régénère script_long.py à partir des briefs
  check_script.py      contrôle le texte (registre, longueurs, aucune capture)
  gen_audio.py         voix edge-tts : un MP3 par réplique + audio/timings.json
  gen_audio_gemini.py  même travail par Gemini TTS (clé nécessaire)
  gen_audio_heygen.py  même travail par HeyGen (OAuth, via MCP)
  decoupe_audio.py     découpe une longue piste fournie en répliques
  timeline.py          plan de tournage + master.wav   (--json : plan seul)
  build_decors.py      compose les 13 plaques 2048×1152 depuis les packs Kenney
  cut_planches.py      découpe les planches de sprites en poses isolées
  planche_grille.py    géométrie de découpe (lignes/colonnes réelles des planches)
  render.py            image par image : caméra, mascottes, habillage, encodage
  generer_image.py     appels image : --prompt/--out, ou --planches un JSON de jobs
  llm.py               passerelle texte (Gemini, Groq, OpenRouter)
  qa.sh                contrôle du livrable (noir, image gelée, loudness, contact)
  coupe15.sh           assemble la coupe de 15 min à partir des parties de l'heure
  plateau_25d.py       essai 2.5D Blender (planches Kenney filmées à la caméra)
  briefs.py            consignes de texte nourries dans make_script.py
assets/
  kenney/              packs CC0 d'origine (background, platformer, UI, emotes…)
  planches/            planches de sprites à découper (Archlord, Uni, garçon, robot)
  sprites/             102 poses découpées + manifeste.json
  *.png                avatars, logos UniFlow / Kernel Forge
planches/ planche2/    dépôts du propriétaire : nouvelles planches à intégrer
keyframes/             plaques de décor produites + decors.json (lignes de sol)
audio/                 775 MP3 de voix + timings.json   (master.wav exclu du dépôt)
zip/                   archives Kenney téléchargées (ré-tractables)
timeline.json          le plan de tournage complet, image près (617 Ko)
plateau_25d.blend      scène Blender de l'essai 2.5D
```

**Non livrés** (régénérables, volumineux) : `out/`, `work/`, `audio15/`,
`_remplaces/`, `.env`, `audio/master.wav`.

---

## 2. Prérequis

Mesuré sur le poste de référence (Ubuntu 24.04.5 LTS, x86-64) :

```
python 3.14.7   Pillow 12.3.0   numpy 2.5.3   edge-tts (dernier)   ffmpeg 6.1.1
```

```bash
python3 -m pip install pillow numpy edge-tts
# voix off alternative (facultatif) : google-genai
```

`bpy` n'est requis que pour l'essai `plateau_25d.py`, hors chaîne nominale.

**Clés (facultatif)** — `cp .env.example .env` puis remplir. Le fichier `.env`
est ignoré par git ; il n'est lu que par `build/gen_images.py`, `build/llm.py`,
`build/gen_audio_gemini.py` et `build/generer_image.py`. Sans lui, la chaîne
complète tourne quand même. **Ne jamais commiter une clé.**

---

## 3. Compiler, dans l'ordre

```bash
# 1. le texte (seulement si les répliques changent)
python3 build/make_script.py && python3 build/check_script.py
python3 build/script_data.py            # compte les répliques, liste les chapitres

# 2. les voix -> audio/line_NN.mp3 + audio/timings.json   (~2 h, réseau)
UNIFLOW_COUPE=60 python3 build/gen_audio.py

# 3. le plan de tournage + le master son -> timeline.json + audio/master.wav
python3 build/timeline.py               # recharge les 775 MP3, mixe ~1 Go d'onde
python3 build/timeline.py --json        # re-partitionne les PLANS seuls, master intact

# 4. les décors -> keyframes/plate_*.webp   (~40 s, 100 % local)
python3 build/build_decors.py

# 5. le rendu de l'heure -> work/part_NNN.mp4 puis out/…ok.mp4   (4 h 30 en 1 worker)
bash run.sh                             # reprend à la première partie manquante
bash run.sh --etat                      # où on en est, sans rien lancer

# 6. la coupe de 15 minutes, si l'heure est déjà en cours
bash build/coupe15.sh                   # -> out/UNIFLOW_plateau_15min_720p.mp4

# 7. le contrôle
bash build/qa.sh out/UNIFLOW_plateau_15min_720p.mp4
```

`UNIFLOW_COUPE` vaut `60` (défaut, 13 chapitres) ou `15` (11 segments). Il
conditionne le texte, donc les voix, donc le master : **changer la coupe impose
de relancer `gen_audio.py` puis `timeline.py`**.

### Rendu à la main

```bash
python3 build/render.py --720p --debut 0 --fin 120 --out work/part_000.mp4
python3 build/render.py --seconds 20          # amorçage rapide, un seul plan
python3 build/render.py --stills 4 78 200     # images fixes dans work/still_*.png
python3 build/render.py --mux work/part_003.mp4   # reposer le son, sans re-rendre
```

Une partie = 120 s d'antenne (`PART=60 bash run.sh` pour 60 s). La partie *n*
couvre `[n×PART, n×PART+PART[`.

### Reprise après coupure

Chaque partie achevée porte un marqueur `work/part_NNN.ok` **vide** : c'est son
existence, pas sa taille, qui valide la partie. Le montage final n'est retenu
que si sa durée collationne avec le plan (`±2 s`). Relancer la même commande
suffit ; rien n'est refait deux fois.

---

## 4. Budget machine (mesuré, pas deviné)

| Constat | Valeur |
|---|---|
| Débit, 1 travailleur | ≈ 5,6 images/s → l'heure en ≈ 4 h 30 |
| Débit, 2 travailleurs | ≈ 7,7 images/s cumulés |
| Débit, 3 travailleurs | **1,7 images/s** : la table d'échange sature, ça s'effondre |
| Poids d'une partie de 120 s | ≈ 27 Mo |
| Garde-fous de `render.py` | refuse sous ≈ 1,2 Go + 0,65 Mo par image libres |
| `master.wav` de l'heure | 661 Mio — **au-dessus de la limite GitHub de 100 Mo**, donc exclu |

Sur un disque tendu : faire transiter les sorties temporaires par un tmpfs
(`--out /dev/shm/…`, cf. `build/coupe15.sh`) plutôt que d'assouplir le garde-fou.
Et **compter les `render.py` vivants avant d'en ajouter un** ; ne jamais suspendre
le `run.sh` d'un autre sans qu'il le demande.

---

## 5. Ce qui se passe à l'image

`render.py` travaille dans un **espace-monde de 2048×1152** par décor. La caméra
y prélève une fenêtre (zoom `cam=(z0,z1)`) qu'elle ramène au cadre ; les
mascottes sont calées sur la ligne de sol du monde, donc l'ombre de contact, le
reflet et le halo suivent le mouvement. L'habillage d'antenne — loquet,
cartouche, sous-titre, fiche de données — se dessine après, dans l'espace du
cadre.

* Le dictionnaire `SHOTS` (`build/render.py:47`) est la table des plans :
  `plate`, `vy`, `cam`, `a`/`b` = `(qui, x du pied, y du sol, taille)`, `scrim`,
  `tech`. **Une scène vient des battements de `timeline.json`, pas du script.**
* `keyframes/decors.json` est la source de vérité des lignes de sol
  (`{sol, tech, props}` par décor). `render.py:121` recoupe chaque `SHOTS` avec
  ce sidecar et **lève une exception** si le pied dessiné ne pose pas sur le sol
  que le décor a produit : modifier un décor sans modifier le plan échoue au lieu
  de passer inaperçu.
* Répartition actuelle des 790 plans :
  `med 244 · amphi 56 · campus 51 · audience 50 · reseau 48 · demo 48 · portail 45
  · compare 43 · sentinelle 43 · avenir 43 · forum 42 · backstage 40 · wide 35`.
  Le plan `med` n'est pas une plaque : c'est `plate_wide` en léger recadrage
  (`cam=(1.300, 1.380)`), et `plate_medium.webp` ne monte pas à l'antenne.
* Les décors sont **composés, pas générés** : calques de paysage, vraies tuiles
  et vraie interface Kenney, téints par décor (les fonds CC0 arrivent quasi
  blancs, luminance 204–240). Reproductible hors ligne, sans quota.

### Chaîne audio

Le master sort à ≈ −21 LUFS intégré, crête −3,8 dBFS. Le montage applique
`volume=4.5dB` puis **`alimiter=level=disabled:limit=0.63:attack=3:release=120`**
en AAC 256 k. Le `level=disabled` n'est pas décoratif : le limiteur régle son
niveau tout seul par défaut, et la chaîne précédente écrêtait — 44 523 blocs de
trois échantillons collés au plafond mesurés sur la coupe, la voix craquait sur
chaque syllabe forte. Chaîne actuelle mesurée : **crête décodée −0,88 dBFS, rms
−16,38 dBFS, zéro échantillon hors plage.**

---

## 6. Règles du brief (non négociables)

Elles viennent du propriétaire du projet et priment sur toute optimisation :

1. Vidéo **en français**, registre publicitaire / dialogue télé.
2. **Aucun terme technique** à l'antenne — pas de « clé d'API », de « base de
   données », de « protocole ». `build/check_script.py` filtre le texte.
3. **Aucune capture d'écran**, d'aucun produit, sur aucun appareil : uniquement
   le plateau, les deux personnages et les fiches de données dessinées.
   `script_data.py:39` force `line["broll"] = None` pour l'appliquer à la source.
4. Fondateur cité : **Nghomsi Feukouo Ravel** (pseudo à l'antenne : Archlord).
   Rachid est le premier étudiant réel, pas le fondateur.
5. Timetables tardives ou provisoires : exclusivement ICT4D L1→L3.
6. « Open source » = **une partie seulement** du code est montrée.
7. Appel à l'action final : liker, commenter, visiter la plateforme, puis
   proposer sur le forum ou par groupe WhatsApp.
8. Une seule adresse canonique par livrable, datée à la compilation.

---

## 7. Améliorations

En cours ou identifiées, par ordre d'intérêt :

* **Finir l'heure.** 16 parties sur 31 validées. Avant de relancer : remplacer
  `work/part_000.mp4` et `part_001.mp4` (anciens plans à 7 décors) par les
  versions valides de `work/coupe15/`, re-toucher les `.ok`, et supprimer
  `work/part_007.mp4` tronquée (sans `.ok`).
* **Retoucher quatre décors** (`build/build_decors.py`) : `amphi` se lit comme un
  mur de briques, `avenir` a un panneau beige flottant et un échafaudage non
  raccord, `compare` laisse un grand vide au milieu, `reseau` mérite ses câbles.
  Supprimer `keyframes/plate_medium.webp`, qui ne sert pas.
* **Couche d'accessoires animés** — un `draw_props()` entre le décor et les
  personnages (écrans qui s'allument, foule qui respire, drapeaux). Le champ
  `props` existe déjà dans `decors.json`, il n'est pas consommé.
* **Brancher les 102 poses** de `assets/sprites/manifeste.json` sur `mascot()`
  (`build/render.py:161`), avec un repli `POSES.get(...)` sur les silhouettes
  actuelles pour ne rien casser pendant la transition.
* **Payer le débit** : le fond et le grade sont recalculés à chaque image. Un
  cache par fenêtre de caméra (les 13 plans tournent en boucle) est la seule
  vraie économie restante, devant l'ajout de travailleurs.
* **Ranger `run.sh`** : appeler `build_decors.py` quand une plaque manque, ne
  plus coder « 775 » en dur (le lire depuis `script_data.py`), exporter
  `UNIFLOW_COUPE` au lieu de le supposer.
* **Recette 15 minutes transversale** : les 900 premières secondes de l'heure ne
  traversent que 5 des 13 décors. Une coupe qui échantillonne les 13 chapitres
  les montrerait tous, pour un tiers du calcul.

Pour itérer vite sur un décor sans relancer l'heure :
`python3 build/build_decors.py amphi && python3 build/render.py --720p --seconds 30`.

---

## 8. Vérifier un livrable

```bash
ffprobe -v error -show_entries stream=codec_type,width,height,r_frame_rate,duration,nb_frames \
        -of default=noprint_wrappers=1 out/UNIFLOW_plateau_15min_720p.mp4
# les deux flux doivent annoncer la même durée au microsecondes près

ffmpeg -v error -i FICHIER -af astats=metadata=1:reset=0,ametadata=print:key=lavfi.astats.Overall.Peak_level -f null - 2>&1 | tail -2
ffmpeg -hide_banner -i FICHIER -vf "blackdetect=d=0.3:pix_th=0.10" -an -f null - 2>&1 | grep blackdetect
ffmpeg -hide_banner -i FICHIER -vf "freezedetect=n=-60dB:d=2.5" -f null - 2>&1 | grep freeze
```

Un livrable n'est « fini » que avec ses chiffres : durée vidéo = durée audio,
image finale présente, aucun écran noir > 0,3 s, aucune image gelée > 2,5 s,
crête sous 0 dBFS. `bash build/qa.sh` les réclame et produit un plan contact
`work/qa_final.png`.

---

## 9. Licence des contenus

* Visuels de décor : packs **Kenney.nl**, licence CC0 — ré-téléchargeables, et
  les archives sources sont dans `zip/`.
* Logos UniFlow / Kernel Forge et planches de sprites : propriété du projet,
  fournis pour la seule reproduction de cette vidéo.
* Voix : synthèse edge-tts (voix publiques Microsoft `fr-FR-HenriNeural`,
  `fr-FR-VivienneMultilingualNeural`).
* Code de ce dépôt : libre pour l'usage interne KERNEL FORGE.
