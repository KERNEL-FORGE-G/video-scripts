# Fiche agent — reprise et recompilation du Plateau UniFlow

**Destinataire : un agent de codage** (Google AI Studio, Gemini CLI, ou
équivalent). Ce fichier est un brief exécutable, pas une documentation
d'agrément. Le README.md explique *pourquoi* la chaîne est faite ainsi ; ici,
*quoi faire, dans quel ordre, et avec quelle preuve*.

## Mission

Récupérer ce dépôt, déterminer seul ce qui manque, **produire les visuels
absents**, relancer la compilation, et rendre un livrable vérifié. Un rendu
d'heures se surveille jusqu'au fichier final : pas de question d'étape, pas de
statut intermédiaire présenté comme fini, pas de « je reviens vers toi ».

Deux livrables seulement, par cet ordre :

1. `out/UNIFLOW_plateau_15min_720p.mp4` — 900 s, le lot de démonstration.
2. `out/UNIFLOW_plateau_60min_720p.ok.mp4` — l'heure, si et seulement si le
   budget disque et les 31 parties suivent.

Commencer par le 1. Le 2 ne se lance qu'avec le 1 en main.

## Environnement

```bash
apt-get install -y ffmpeg python3-pip fonts-dejavu-core
pip install pillow numpy edge-tts
```

Attendu : Python ≥ 3.11, `ffmpeg` ≥ 5, **une police DejaVu** (le moteur charge
`/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf` en dur — sans elle, les
cartons sortent en rectangles). Pas de GPU, pas de base de données, pas de
réseau requis pour le rendu.

```bash
git clone https://github.com/KERNEL-FORGE-G/video-scripts.git plateau && cd plateau
cp .env.example .env        # FACULTATIF : sans clé, la chaîne tourne quand même
```

## 1. Diagnostic — ne rien relancer à l'aveugle

```bash
python3 - <<'PY'
import json, pathlib as p
R, tl = p.Path("."), None
ok = lambda c, msg: print(("  OK  " if c else "  MANQUE ") + msg)
try: tl = json.load(open("timeline.json"))
except Exception as e: print("  MANQUE timeline.json :", e)
n = len(tl["beats"]) if tl else 0
ok(tl and abs(tl["total"] - 3611.766) < 0.01, f"plan de tournage : {tl and tl.get('total')} s, {n} plans")
keys = [k for k in json.load(open("keyframes/decors.json")) if k != "_revision"]
absentes = [k for k in keys if not (R / f"keyframes/plate_{k}.webp").exists()]
ok(not absentes, f"plaques de decor : {len(keys)-len(absentes)}/{len(keys)}"
                 + (f" — il manque {absentes}" if absentes else ""))
voix = sorted((R/"audio").glob("line_*.mp3"))
ok(len(voix) >= 775 and (R/"audio/timings.json").exists(),
   f"voix : {len(voix)} mp3 + timings {'présent' if (R/'audio/timings.json').exists() else 'ABSENT'}")
poses = list((R/"assets/sprites").glob("*.png"))
ok(len(poses) >= 102, f"poses decoupees : {len(poses)}/102")
ok((R/"audio/master.wav").exists(), "master.wav (toujours absent du depot, ~661 Mio)")
parts = sorted((R/"work").glob("part_*.ok"))
ok(len(parts) >= 31, f"parties validees : {len(parts)}/31")
import shutil; libre = shutil.disk_usage(".").free
ok(libre > 4*2**30, f"disque libre : {libre/2**30:.1f} Go (il en faut 4 pour l'heure)")
PY
```

Tout ce qui sort en `MANQUE` passe à l'étape 2. Ne jamais déduire un état d'un
fichier de taille nulle : les marqueurs `.ok` sont **vide par conception**,
seule leur existence compte.

## 2. Récupérer, dans cet ordre

Coûts mesurés sur le poste de référence. Chaque ligne est idempotente : relancer
ne refait pas ce qui est déjà validé.

| # | Ce qui manque | Commande | Coût |
|---|---|---|---|
| a | brouillons de relecture | `python3 build/restaure_brouillons.py` | secondes — **sans ça, `check_script.py` annonce `0 réplique` en sortant 0** |
| b | plaques de décor | `python3 build/build_decors.py [cle...]` | secondes, **100 % local** |
| c | poses de sprites | `python3 build/cut_planches.py` | secondes, local |
| d | voix | `UNIFLOW_COUPE=60 python3 build/gen_audio.py` | ≈ 2 h, réseau, sans clé |
| e | plan de tournage seul | `python3 build/timeline.py --json` | secondes, **ne touche pas au master** |
| f | master.wav | `python3 build/timeline.py` | ≈ 30 min, ≈ 2 Go de RAM |
| g | parties vidéo | `bash run.sh` (ou une triche, voir §4) | 4 h 30 en 1 travailleur |
| h | livrable | `bash build/coupe15.sh` puis `bash build/qa.sh <fichier>` | minutes |

**Piège connu, à ne pas répéter** : `timeline.py` sans argument recharge les 775
MP3 dans des tableaux d'onde d'une heure à 48 kHz — environ 700 Mo chacun. Sur
une machine à 8 Go de RAM disponible, le processus se fait tuer **sans message**
et le log reste à zéro octet. Si l'objectif est de modifier le découpage des
plans et non le son, et que `master.wav` existe déjà : **`--json`**, toujours.
Le mix ne dépend que des durées ; un master existant reste valide.

**Cet enchaînement a été exécuté sur un clone neuf** (215 Mo, sans `out/` ni
`work/`) : diagnostic complet, `build_decors.py amphi` après suppression
volontaire de la plaque (1,7 s, 89 Ko rendus), `cut_planches.py 5` (25 poses),
`restaure_brouillons.py` → `check_script.py` (775 répliques),
`render.py --720p --seconds 2` (50 images, 1280×720 à 25 i/s) et
`--debut 0 --fin 4 --out …` (4,000000 s). Un clone de ce dépôt compile donc sans
clé, sans réseau et sans données locales.

## 3. Générer les visuels manquants

Trois catégories, trois régimes — ne pas les confondre, c'est là que les agents
échouent.

**Décors (`keyframes/plate_*.webp`) — jamais par génération d'image.** Ils sont
*composés* dans `build/build_decors.py` à partir des packs Kenney CC0 de
`assets/kenney/` : calques de paysage teintés, vraies tuiles, vraie interface.
Reproductible, hors ligne, sans quota, et c'est une exigence du brief. Ajouter un
décor = écrire une fonction portant le **nom exact de la clé** (`def amphi():`,
`def forum():`, …) qui renvoie une image 2048×1152, et l'inscrire dans le
dictionnaire `DECORS` (ligne 999) — `plateau("wide")` couvre les trois vues du
plateau nu. Puis :

```bash
python3 build/build_decors.py <cle>
python3 build/render.py --720p --seconds 30      # verifier a l'image, pas au log
```

Le sidecar `keyframes/decors.json` consigne la ligne de sol de chaque décor et
`render.py` **lève une exception** si un plan pose un pied à une autre hauteur :
l'erreur est bruyante, corrige la géométrie au lieu d'assouplir le contrôle.

**Poses (`assets/sprites/`) — par découpe.** Le propriétaire dépose des planches
entières dans `planches/` et `planche2/` à la racine. Les inscrire dans
`PLANCHES` de `build/cut_planches.py`, découper, puis vérifier que le
`manifeste.json` couvre bien les clés demandées par le script.

**Images nouvelles (visuels d'ambiance, illustrations ponctuelles) — par API, en
dernier recours.** `python3 build/generer_image.py --prompt "…" --out …` avec
`GEMINI_API_KEY` dans `.env`. Avant d'y aller : **tester le quota sur une seule
image et le signaler**. Mesuré sur le poste de référence : HTTP 429 sur les six
modèles image (le texte et la synthèse vocale répondent). Un quota épuisé n'est
pas une raison pour inventer un décor — revenir au composite Kenney.

## 4. Relancer la compilation

```bash
bash run.sh --etat      # ou : ce qui reste a faire
bash run.sh             # 1 travailleur, 31 parties de 120 s, reprend aux .ok
```

Règles de débit, mesurées (et non négociables) :

* 1 travailleur ≈ **5,6 images/s** ; 2 ≈ **7,7 cumulés** ; **3 = 1,7** — la table
  d'échange sature et tout le monde s'arrête. Deux grands maximum, en surveillant
  le débit réel, pas le nombre de processus.
* `render.py` refuse une tranche s'il estime le disque trop juste
  (≈ 1,2 Go + 0,65 Mo par image). **Ne pas abaisser ce garde-fou** : passer la
  sortie par un tmpfs (`--out /dev/shm/part_042.mp4`) et vérifier que le fichier
  existe vraiment avant de le concaténer.
* Une partie validée = `.ok` présent **et** durée conforme à ±0,15 s. Une partie
  sans `.ok` est considered comme absente, même si elle pèse 4 Mo.
* Économie connue, à privilégier si des parties de l'heure existent déjà : la
  coupe de 15 min **emprunte** les parties valides (`build/coupe15.sh`, fonction
  `source_de`) et ne recalcule que les manques. Un `work/part_NNN.mp4` ne vaut
  que pour le `timeline.json` de sa date : vérifier la cohérence avant d'emprunter.

## 5. Critères d'acceptation — avec les chiffres

Ne rendre un fichier que s'il passe **les six**. Le rapport final cite des
mesures, jamais des adjectifs.

```bash
V=out/UNIFLOW_plateau_15min_720p.mp4
ffprobe -v error -show_entries stream=codec_type,width,height,r_frame_rate,duration,nb_frames \
        -of default=noprint_wrappers=1 "$V"
ffmpeg -v error -i "$V" -af "astats=metadata=1,ametadata=print:key=lavfi.astats.Overall.Peak_level" \
        -f null - 2>&1 | grep Peak_level | tail -1
ffmpeg -hide_banner -i "$V" -vf "blackdetect=d=0.3:pix_th=0.10" -an -f null - 2>&1 | grep blackdetect
ffmpeg -hide_banner -i "$V" -vf "freezedetect=n=-60dB:d=2.5" -f null - 2>&1 | grep freeze
ffmpeg -v error -i "$V" -vf "select=eq(n\,0)"  -frames:v 1 work/first.png
ffmpeg -v error -sseof -0.1 -i "$V" -frames:v 1 work/last.png
```

1. vidéo **et** audio annoncent la même durée (coupe 15 min : `900,000000 s`,
   `22 500 images`) — un conteneur qui annonce 900 s pendant que le flux vidéo en
   fait 840 est un **échec de montage**, pas un arrondi ;
2. crête audio **sous 0 dBFS** et zéro échantillon collé au plafond : la chaîne
   est `volume=4.5dB,alimiter=level=disabled:limit=0.63:attack=3:release=120`,
   AAC 256 k — le `level=disabled` est ce qui empêche le limiteur d'automonter la
   crête et de faire craquer la voix (44 523 blocs écrêtés mesurés avant correction) ;
3. aucun écran noir > 0,3 s, aucune image gelée > 2,5 s ;
4. première image = carton d'intro, dernière image complète et non tronquée ;
5. synchro labellisée : corrélation de l'enveloppe 10 ms entre la piste du
   conteneur et `audio/master.wav`, maximum attendu à ±1 frame de 0 s
   (mesuré : 0,910 à +0,00 s). Ne pas utiliser la corrélation d'onde brute, elle
   noie le résultat sous les respirations ;
6. contrôle visuel par plans contact, **une image toutes les ~5 s** et une bande
   autour de chaque couture (`240/360/480/600 s`) :
   `ffmpeg -i "$V" -vf "scale=480:-2,select='not(mod(n\,125))',tile=6x5" -frames:v 1 work/contact.png`
   (≈ 8 s de décodage, ≈ 5 Mo — sans le `scale`, la vignette pleine résolution
   pèse 32 Mo et devient illisible). Regarder les bandes : un plan sombre n'est
   pas un bug (le grade filmique global descend la luminance moyenne à ≈ 41 sur
   255) ; une couture qui décale le sol de trois centimètres, si.

Format de compte-rendu attendu :

```
fichier : <chemin> · <octets> · built <date>
video   : <codec> <lxh> <fps> — <duree> s / <nb_frames> images
audio   : <codec> <rate> <canaux> — <duree> s · crete <dBFS> · rms <dBFS>
synchro : <score> a <derive> s
coutures : <liste> — conforme / décalé de …
libre disque : <Go>   workers restants : <n>
anomalies assumées : <liste, vide n'est pas une réponse par défaut>
```

## 6. Interdits

* **Ne rien modifier hors de ce dépôt.** La plateforme UniFlow (le reste du
  monorepo KERNEL FORGE) est hors champ : lecture seule, et encore — ce dont la
  vidéo a besoin est déjà ici.
* **Aucune clé dans git.** `.env` est ignoré ; `.env.example` ne contient que des
  noms. Le dépôt distant doit rester vérifiable : `git ls-files | grep -c '^\.env$'`
  doit renvoyer `0`.
* **Aucun fichier > 100 Mo** : `audio/master.wav` (661 Mio) et les MP4 de
  `out/`/`work/` sont exclus par `.gitignore`. Pas de LFS ici.
* **Aucune capture d'écran** dans la vidéo, d'aucun produit, sur aucun appareil.
  `script_data.py:39` force `broll = None` ; ne pas retirer cette ligne pour
  « enrichir ».
* **Aucun vocabulaire technique à l'antenne** — la liste `INTERDITS` de
  `build/check_script.py:37` fait foi. Le public n'entend ni « API », ni « base
  de données », ni « serveur ».
* **Ne pas tuer ni suspendre** un `run.sh`/`descendant.sh` lancé par quelqu'un
  d'autre : compter les `render.py` vivants et ne pas s'ajouter.
* **Ne pas réécrire l'historique** de la branche `main` (sheets de
  `git filter-branch`, `push --force`) : c'est une branche partagée.
* Le texte cité à l'antenne : fondateur **Nghomsi Feukouo Ravel** (pseudo
  Archlord), premier étudiant Rachid. Orthographe à vérifier dans
  `render.py` et `script_long.py` si tu touches ces lignes.

## 7. Cassé connu — ne pas le rediscover

* **Quatre décors à retoucher** : `amphi` se lit comme un mur de briques,
  `avenir` a un panneau beige flottant et un échafaudage non raccord, `compare`
  laisse un vide central, `reseau` mérite ses câbles. Tâche ouverte ; le rendu de
  l'heure complet est lancé **après**, sinon c'est 4 h 30 à refaire.
* `keyframes/plate_medium.webp` n'est monté nulle part (le plan `med` est un
  recadrage de `plate_wide`) : candidate à la suppression, pas à l'ajout d'un plan.
* **Quota image Gemini épuisé** (429 sur les six modèles) sur le poste de
  référence ; texte et TTS répondent.
* Les 15 premières minutes de l'heure ne traversent que **5 des 13 décors**
  (`backstage`, `med`, `compare`, `wide`, `campus`). C'est un choix de montage,
  pas un bug — mais si l'objectif est de montrer les 13 décors dans une coupe
  courte, il faut une **coupe transversale** qui échantillonne les chapitres, pas
  un simple `-t 900`.
* Sur ce chantier, l'heure est à 16/31 parties validées et `work/` n'est pas dans
  le dépôt : un clone repart de zéro, compte 4 h 30.

## 8. Ce que tu peux décider seul · ce qu'il faut demander

Seul, sans attendre : lancer/rerelancer une tranche, corriger un script de ce
dépôt, choisir l'ordre de récupération, emprunter une partie valide, regénérer un
décor, arbitrer 720 p contre 1080 p au profit du budget disque, purger les
intermédiaires d'un job que **tu** as lancés.

À demander au propriétaire — une seule fois, groupé, et en continuant par
ailleurs : toucher au texte des répliques, changer la durée de la commande
(60 min / 15 min), publier hors de ce dépôt, supprimer un asset livré, ou toute
dérivation d'un point du §6.
