#!/usr/bin/env bash
# La coupe de quinze minutes : les 900 premières secondes du plateau, au plan à
# treize décors.
#
# Elle ne re-calcule pas ce qui est déjà tourné. Les parties 002 à 006 sont
# sorties du moteur APRÈS le 15:22 qui a redistribué les décors, dans le même état
# des plaques (14:36) : image pour image, ce que cette coupe produirait elle-même.
# Les parties 000 et 001 sont d'avant — sept décors — donc le premier quart
# d'heure est refait, et la dernière minute aussi plutôt que de tronquer une
# partie à un keyframe.
#
# Le disque est à 1 % : render.py réclame 1,2 Go d'avance avant d'écrire, même
# pour soixante secondes. La tranche que personne d'autre ne rend vit donc dans
# /dev/shm, et l'assemblage se fait en une seule passe ffmpeg — la copie vidéo
# croque le concat, plus d'intermédiaire de 370 Mo sur le volume plein.
set -uo pipefail
cd "$(dirname "$0")/.."

FIN=900                 # 15:00, et 899,5 s tombe à la fin d'une réplique
SCRATCH=/dev/shm/coupe15
LOG=work/coupe15.log
CIBLE=out/UNIFLOW_plateau_15min_720p.mp4
mkdir -p "$SCRATCH" out work

# une partie du chantier n'est recevable que validée et complète en images.
# les marqueurs .ok sont touchés à vide : c'est une existence qui compte, pas une
# taille. le compte d'images se lit dans le conteneur, pas en décodant trois
# mille images sous trois chantiers à la fois.
complete() {                        # $1 = n° de partie, $2 = images attendues
    local tag; tag=$(printf 'part_%03d' "$1")
    [ -f "work/$tag.ok" ] || return 1
    [ "$(ffprobe -v error -select_streams v:0 -show_entries stream=nb_frames \
            -of csv=p=0 "work/$tag.mp4" 2>/dev/null)" = "$2" ]
}

# la source de [debut,fin[ : celle du chantier si elle est bonne, sinon on la
# calcule. l'attente a une fin : si le chantier est mort, la coupe se rend seule.
source_de() {                       # $1 = n°, $2 = début, $3 = fin, $4 = empruntable
    local tag n=$1 de=$2 fi=$3 tries=0
    tag=$(printf 'part_%03d' $n)
    local want=$(( ($3 - $2) * 25 ))
    local mine=$SCRATCH/$tag.mp4
    # une tranche déjà calculée par la coupe se remplace elle-même : relancer ce
    # script ne doit pas payer deux fois la même minute d'antenne.
    [ -s work/coupe15/$tag.mp4 ] && { echo work/coupe15/$tag.mp4; return; }
    [ -s $mine ] && { echo $mine; return; }
    if [ "${4:-emprunt}" = "emprunt" ]; then
        while ! complete $n $want; do
            [ $tries -ge 60 ] && break            # 30 min d'attente, pas plus
            echo "$(date '+%H:%M') en attente de $tag ($de->$fi)" >> $LOG
            sleep 30; tries=$((tries + 1))
        done
        complete $n $want && { echo work/$tag.mp4; return; }
    fi
    echo "$(date '+%H:%M') $tag hors service ($de->$fi) : la coupe la calcule" >> $LOG
    python3 build/render.py --720p --debut $de --fin $fi --out $mine >> $LOG 2>&1
    echo $mine
}

echo "------------------------------------------------- $(date '+%d %H:%M') coupe 15 min" >> $LOG

morceaux=()
morceaux+=("$(source_de 0 0 120 nous)")            # chapitre 1, premier plan
morceaux+=("$(source_de 1 120 240 nous)")          # fin chapitre 1, chapitre 2
for n in 2 3 4 5 6; do
    morceaux+=("$(source_de $n $((n * 120)) $((n * 120 + 120)))")
done
morceaux+=("$(source_de 7 840 900 nous)")          # 840 -> 900, soixante secondes

total=0
: > work/coupe15_liste.txt
for m in "${morceaux[@]}"; do
    # le dé-muxeur concat résout les chemins relatifs depuis le dossier de la
    # liste, et la tranche du /dev/shm est déjà absolue : tout passer en absolu,
    # sinon le dernier morceau disparaît et la coupe s'arrête à 840 s.
    case $m in /*) ;; *) m=$PWD/$m ;; esac
    [ -f "$m" ] || { echo "$m introuvable" | tee -a $LOG; exit 1; }
    d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$m" 2>/dev/null)
    [ -z "$d" ] && { echo "$m illisible" | tee -a $LOG; exit 1; }
    total=$(python3 -c "print(round($total + $d, 3))")
    printf "file '%s'\n" "$m" >> work/coupe15_liste.txt
done
echo "$(date '+%H:%M') ${#morceaux[@]} morceaux, $total s assemblées" >> $LOG
if ! python3 -c "import sys; sys.exit(0 if abs($total - $FIN) <= 0.2 else 1)"; then
    echo "durée assemblée $total != $FIN — on ne monte pas là-dessus" | tee -a $LOG; exit 1
fi

# Le son vient du master de l'heure à la seconde près : la coupe commence à 0,
# donc aucune couture ne se voit ni ne s'entend. volume=4,5dB est le gain de
# normalisation du moteur (-21 LUFS mesurés -> -16,5 visés). Le limiteur doit
# être réglé SANS son niveau automatique : avec, il remonte l'entrée et la crête
# sortie dépassait 0 dBFS — 44 523 blocs d'écrêtage mesurés, la voix qui casse.
# Mais le plafond se mesure APRÈS le décodage : l'AAC rend +3 dB sur une matière
# déjà bridée, et tenir la PCM à -2 dBFS laissait encore 1 342 écrêtages. Le
# plafond descend donc à -4 dBFS et le débit à 256k : crête décodée mesurée à
# -1 dBFS. Le fondu ferme la coupe au lieu de la casser.
SON="volume=4.5dB,alimiter=level=disabled:limit=0.63:attack=3:release=120,\
afade=t=out:st=897.5:d=2.5"
ffmpeg -v error -y -f concat -safe 0 -i work/coupe15_liste.txt -t $FIN -i audio/master.wav \
    -map 0:v:0 -map 1:a:0 -c:v copy \
    -af "$SON" -c:a aac -b:a 256k -ar 48000 -movflags +faststart /dev/shm/coupe15.mp4 >> $LOG 2>&1
[ -s /dev/shm/coupe15.mp4 ] && mv /dev/shm/coupe15.mp4 "$CIBLE"

echo "$(date '+%H:%M') $CIBLE écrit" >> $LOG
# Un conteneur peut annoncer 900 s parce que l'audio les fait : c'est le flux
# vidéo qu'on engage, et une minute d'image manquante ne s'entend pas.
v=$(ffprobe -v error -select_streams v:0 -show_entries stream=duration \
        -of csv=p=0 "$CIBLE" 2>/dev/null)
if ! python3 -c "import sys; sys.exit(0 if abs($v - $FIN) <= 0.2 else 1)"; then
    echo "vidéo $v s pour $FIN s d'audio — montage incomplet, non livré" | tee -a $LOG
    exit 1
fi
ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_name \
        -of default=nw=1 "$CIBLE" | tee -a $LOG
