#!/bin/bash
# run_gz05_container_build.sh — adapter container build on GZ05
# Container: oh-build:22.04 (GZ02 ubuntu-22.04 config).
# User: SAME as host owner of /data/adapter (non-root) — simplifies permissions (patches+outputs write cleanly).
# snap-docker cannot bind-mount /data -> /home bind mounts. Source pre-patched on host -> --no-apply.
# Output: /data/adapter/out (local; GZ02 NFS /opt is full). GZ05 = 16 vCPU / 60 GB.
set -e
ARCH="${1:-arm32}"; JOBS="${2:-14}"
BIND=/home/AlexYang/_build; IMG=oh-build:22.04
UG="$(stat -c %u:%g /data/adapter)"   # match host owner (AlexYang=1001 on GZ05)
mkdir -p $BIND/{adapter,oh,aosp} /data/adapter/out
for d in adapter oh aosp; do if [ "$d" = oh ]; then SRC=/home/HanBingChen/oh; else SRC=/data/$d; fi; mountpoint -q $BIND/$d || sudo mount --bind $SRC $BIND/$d; done
LOG=/data/adapter/out/build_${ARCH}_$(date +%Y%m%d_%H%M%S).log
echo "[run] ARCH=$ARCH JOBS=$JOBS USER=$UG LOG=$LOG"
case "$ARCH" in
  arm32) CMD="bash build/build_aosp_lib.sh --no-apply -j$JOBS" ;;
  *) echo "unsupported ARCH=$ARCH"; exit 2 ;;
esac
sudo docker run --rm --user $UG --name adapter_build_$ARCH \
  -v $BIND/adapter:/adapter -v $BIND/oh:/oh:ro -v $BIND/aosp:/aosp \
  -e OH_ROOT=/oh -e AOSP_ROOT=/aosp -e HOME=/tmp -e CCACHE_DIR=/adapter/out/.ccache \
  --memory=56g --cpus=16 -w /adapter $IMG \
  bash -c "$CMD 2>&1 | tee /adapter/out/$(basename $LOG)"
echo "[run] exit=${PIPESTATUS[0]}"
