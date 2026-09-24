#!/bin/sh
# Le snap blender est inutilisable ici : snap-confine a besoin de cap_dac_override,
# retiré par NoNewPrivs du shell outillé. Le paquet est en confinement classic,
# on exécute donc le binaire empaqueté directement.
SNAP=/snap/blender/current
export SNAP SNAP_NAME=blender SNAP_ARCH=amd64
export LD_LIBRARY_PATH="$SNAP/lib:$SNAP/lib/x86_64-linux-gnu:$SNAP/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$SNAP/blender" "$@"
