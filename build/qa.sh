#!/usr/bin/env bash
# Contrôle final du livrable : intégrité, images noires/gelées, loudness, extraits.
#   build/qa.sh [chemin/du/mp4]   — par défaut la dernière coupe rendue.
set -u
V=${1:-}
if [ -z "$V" ]; then
  V=$(ls -t out/UNIFLOW_plateau_*min_*p.mp4 2>/dev/null | head -1)
  [ -n "$V" ] || V=out/UNIFLOW_plateau_1080p.mp4
fi
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$V")
echo "=== fichiers ==="; ls -lh "$V"
echo "=== flux ==="
ffprobe -v error -show_entries format=duration,bit_rate:stream=codec_name,width,height,r_frame_rate,pix_fmt,channels,sample_rate -of default=noprint_wrappers=1 "$V"
echo "=== images noires (>0.3s) ==="
ffmpeg -hide_banner -i "$V" -vf "blackdetect=d=0.3:pix_th=0.10" -an -f null - 2>&1 | grep blackdetect | grep -v "Parsed" | head -20
echo "=== images gelées (>2.5s) ==="
ffmpeg -hide_banner -i "$V" -vf "freezedetect=n=-60dB:d=2.5" -map 0:v -f null - 2>&1 | grep freeze | grep -v "Parsed" | head -20
echo "=== loudness ==="
ffmpeg -hide_banner -i "$V" -af ebur128=peak=true -f null - 2>&1 | grep -A9 "Summary"
mkdir -p work
rm -f work/final_*.png
# Les extraits se répartissent sur toute la durée : une heure ne se contrôle
# pas avec huit images prises dans les quinze premières minutes.
for q in 0.006 0.05 0.15 0.3 0.45 0.6 0.75 0.9 0.985 0.998; do
  t=$(python3 -c "print(f'{$DUR*$q:.2f}')")
  ffmpeg -v error -y -ss $t -i "$V" -frames:v 1 "work/final_${q}.png"
done
python3 - <<'PY'
from PIL import Image
import glob
fs = sorted(glob.glob('work/final_*.png'), key=lambda p: float(p.split('_')[1].split('.')[0]))
cw, ch, cols = 960, 540, 2
rows = (len(fs) + cols - 1) // cols
sheet = Image.new('RGB', (cols*cw, rows*ch), (12, 12, 18))
for i, f in enumerate(fs):
    sheet.paste(Image.open(f).resize((cw, ch), Image.LANCZOS), ((i % cols)*cw, (i//cols)*ch))
sheet.save('work/qa_final.png')
print('feuille de contrôle :', sheet.size, len(fs), 'extraits')
PY
rm -f work/final_*.png
echo "=== QA terminée ==="
