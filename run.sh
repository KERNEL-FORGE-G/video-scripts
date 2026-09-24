#!/usr/bin/env bash
# « Le Plateau UniFlow » — une heure de vidéo publicitaire, construite de A à Z.
#
#   bash run.sh            # construire tout ce qui manque, puis contrôler
#   bash run.sh --etat     # afficher l'avancement sans rien lancer
#   PART=60 bash run.sh    # découper plus fin (une partie = 60 s d'antenne)
#
# Le montage est rendu PARTIE par PARTIE et chaque partie achevée est marquée
# d'un fichier .ok. Une coupure de session, de réseau ou de courant ne coûte donc
# que la partie en cours : relancer la même commande reprend à la première
# partie manquante. Le son n'est posé qu'une seule fois, au montage final, pour
# qu'aucune couture de segment ne s'entende.
#
# Rien ici ne sort du dossier video/ : la plateforme UniFlow n'est que lu.
set -uo pipefail
cd "$(dirname "$0")"

# Une heure de calcul ne doit pas dépendre d'un capot refermé : la machine a
# hiberné en pleine partie 27 et a gelé le rendu avec elle. Tant que la
# construction tient, elle pose un bloqueur de veille ; sans systemd-inhibit ou
# sans droit, elle tourne quand même, juste moins protégée.
if [ "${1:-}" != "--etat" ] && [ -z "${UNIFLOW_EVEIL:-}" ] \
        && command -v systemd-inhibit >/dev/null 2>&1; then
    if UNIFLOW_EVEIL=1 systemd-inhibit --what=sleep:handle-lid-switch --mode=block \
            --why="Montage du Plateau UniFlow" --who="run.sh" bash run.sh "$@"; then
        exit 0
    fi
    echo "(veille non bloquée — un capot fermé peut encore geler le rendu)"
fi

export OMP_NUM_THREADS=1        # un seul rendu à la fois, sans se marcher dessus
export TMPDIR="$PWD/work"       # ni image ni éphémère ne dépendent de /tmp
mkdir -p out work
PART=${PART:-120}
MASTER=audio/master.wav

# ------------------------------------------------------------------ les chiffres du plan
TOTAL=$(python3 -c "import json;print(json.load(open('timeline.json'))['total'])" 2>/dev/null)
if [ -z "${TOTAL:-}" ]; then TOTAL=0; fi
NPART=$(python3 -c "import math;print(max(0, math.ceil((${TOTAL:-0}) / $PART)))")

etat() {
    local n fait=0 o
    for ((n = 0; n < NPART; n++)); do [ -f "work/part_$(printf '%03d' $n).ok" ] && fait=$((fait + 1)); done
    o=$(ls -S out/UNIFLOW_plateau_*min_*p.ok.mp4 out/UNIFLOW_plateau_*min_*p.mp4 2>/dev/null | head -1)
    printf 'voix %s/775 · plan de tournage %s · parties %s/%s' \
        "$(ls audio/line_*.mp3 2>/dev/null | wc -l)" "$([ -f timeline.json ] && echo 'prêt' || echo 'absent')" \
        "$fait" "$NPART"
    [ -s "$MASTER" ] && printf ' · master %.0f Mo' "$(du -m "$MASTER" | cut -f1)"
    [ -n "${o:-}" ] && printf '\nfichier : %s  (%.2f min, %.0f Mo)' \
        "$o" "$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$o")" \
        "$(($(stat -c %s "$o") / 1048576))"
    printf '\nlibre sur le disque : %s\n' "$(df -h . | awk 'END{print $4}')"
}

if [ "${1:-}" = "--etat" ]; then etat; exit 0; fi

# Le verrou ne se prend qu'ici : --etat doit pouvoir répondre pendant qu'une
# construction tourne, c'est justement à ce moment-là qu'on le consulte.
if command -v flock >/dev/null 2>&1; then
    exec 9>work/run.lock
    flock -n 9 || { echo "Une construction tourne déjà — work/run.log, ou bash run.sh --etat." >&2; exit 1; }
fi

echo "=== UniFlow, $(date '+%d/%m %H:%M') — $(etat | head -1) ==="

# ------------------------------------------------------------------ 1. les voix
if [ "$(ls audio/line_*.mp3 2>/dev/null | wc -l)" -lt 775 ] || [ ! -f audio/timings.json ]; then
    echo "-- génération des voix (775 répliques, plusieurs heures)"
    python3 build/gen_audio.py || { echo "VOIX EN ÉCHEC — voir plus haut." >&2; exit 1; }
fi

# ------------------------------------------------------------------ 2. le plan de tournage
if [ ! -f timeline.json ] || [ ! -s "$MASTER" ] || [ ! -f work/plan.ok ]; then
    echo "-- plan de tournage + master son"
    python3 build/timeline.py && touch work/plan.ok || { echo "PLAN EN ÉCHEC." >&2; exit 1; }
    TOTAL=$(python3 -c "import json;print(json.load(open('timeline.json'))['total'])")
    NPART=$(python3 -c "import math;print(max(0, math.ceil($TOTAL / $PART)))")
fi
echo "-- heure diffusée : $(python3 -c "print(f'{$TOTAL/60:.2f}')") min · $NPART parties de ${PART}s"

# ------------------------------------------------------------------ 3. les parties
# Une partie n'est validée qu'à trois conditions : le code 0 de l'encodeur, le
# fichier .ok, et une durée conforme à la sonde. Sans la sonde, une partie coupée
# par un arrêt brutal passerait pour bonne et l'heure sortirait amputée.
duree_attendue() {
    python3 -c "print(f'{min($PART, max(0.0, $TOTAL - $1 * $PART)):.3f}')"
}

n=0
while [ "$n" -lt "$NPART" ]; do
    tag=$(printf 'part_%03d' $n)
    if [ -f "work/$tag.ok" ]; then n=$((n + 1)); continue; fi
    ok=0
    for essai in 1 2 3; do
        echo "-- $tag ($((n * PART))s → $(((n + 1) * PART))s), tentative $essai$(etat | head -1 | sed 's/^/ · /')"
        python3 build/render.py --720p --debut $((n * PART)) --fin $(((n + 1) * PART)) \
            --out "work/$tag.mp4" 2>&1 | sed -u "s/^/  /"
        got=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "work/$tag.mp4" 2>/dev/null)
        want=$(duree_attendue $n)
        if [ -n "$got" ] && python3 -c "import sys;sys.exit(0 if abs(float('$got') - float('$want')) < 0.15 else 1)"; then
            touch "work/$tag.ok"; ok=1; break
        fi
        echo "   $tag rejetée : ${got:-aucune} s au lieu de $want s"
    done
    [ "$ok" = 1 ] || { echo "$tag n'a pas passé trois tentatives — relancer bash run.sh." >&2; exit 1; }
    n=$((n + 1))
done

# ------------------------------------------------------------------ 4. le montage final
FIN=$(ls out/UNIFLOW_plateau_*min_*p.ok.mp4 2>/dev/null | head -1)
if [ -z "$FIN" ]; then
    MIN=$(python3 -c "print(max(1, round($TOTAL / 60)))")
    VISER="out/UNIFLOW_plateau_${MIN}min_720p.mp4"
    echo "-- montage final : $NPART parties + le master, sans ré-encodage"
    : > work/parties.txt
    for ((n = 0; n < NPART; n++)); do
        printf "file '%s/work/part_%03d.mp4'\n" "$PWD" "$n" >> work/parties.txt
    done
    # Copie vidéo pure : les parties partagent le même encodeur, le même cadre et
    # une image clé à leur première frame. Le son, lui, arrive entier, avec le
    # gain de normalisation mesuré (-21 LUFS visés -> -16.5, crête à -2 dBFS).
    ffmpeg -v error -y -f concat -safe 0 -i work/parties.txt -i "$MASTER" \
        -map 0:v:0 -map 1:a:0 -c:v copy -af volume=4.5dB -c:a aac -b:a 192k \
        -ar 48000 -shortest -movflags +faststart "$VISER" || { echo "MONTAGE EN ÉCHEC." >&2; exit 1; }

    D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$VISER" 2>/dev/null)
    if [ -z "$D" ] || ! python3 -c "import sys;sys.exit(0 if abs(float('$D') - $TOTAL) < 2.0 else 1)"; then
        echo "MONTAGE REJETÉ : ${D:-illisible} s au lieu de $(python3 -c "print(f'{$TOTAL:.1f}')") s." >&2
        exit 1
    fi
    mv "$VISER" "$VISER.ok.mp4"
    FIN="$VISER.ok.mp4"
    echo "-- $FIN : $(awk -v d="$D" 'BEGIN{printf "%.2f", d/60}') min, $(($(stat -c %s "$FIN") / 1048576)) Mo"
fi

# ------------------------------------------------------------------ 5. le contrôle
echo "-- contrôle automatique (noir, image figée, niveau audio, plan contact)"
bash build/qa.sh "$FIN" 2>&1 | sed -u "s/^/  /"
echo "   plan contact : work/qa_final.png"

# ------------------------------------------------------------------ 6. le ménage
# Les parties ne pèsent plus rien d'utile une fois l'heure validée ; le disque
# est la seule ressource rare ici. Elles sont rendues inutiles, pas effacées à
# l'aveugle : on ne touche qu'aux fichiers que ce script a lui-même créés.
if [ -f "$FIN" ]; then
    echo "-- suppression des $(ls work/part_*.mp4 2>/dev/null | wc -l) parties intermédiaires"
    rm -f work/part_*.mp4 work/part_*.ok work/parties.txt work/test_*.mp4 work/test_list.txt
fi

echo "=== terminé, $(date '+%d/%m %H:%M') — $FIN ==="
etat
