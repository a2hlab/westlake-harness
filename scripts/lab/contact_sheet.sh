#!/usr/bin/env bash
# Tile many board screenshots into one labeled image so the outer loop reads a whole batch in one look.
#
#   contact_sheet.sh <out.jpeg> [--cols N] [--width W] <img>...
#   contact_sheet.sh <out.jpeg> [--cols N] [--width W] --run <run-dir> [--shot final]
#
# --run takes a bms_batch.py run directory (<run>/<serial>/<key>/<shot>.jpeg, or <run>/<key>/<shot>.jpeg) and
# tiles <shot>.jpeg of every key in name order. Each tile is labeled with its key (or file stem) at the top;
# missing images become a grey tile labeled "missing" so a gap is visible instead of silently shifting the grid.
# Needs ffmpeg. Labels need its drawtext filter (Homebrew's default build lacks it); without drawtext the
# tiles are unlabeled and the row/column of each key is read from the order printed to stdout.
set -euo pipefail

usage() { sed -n '2,11p' "$0" >&2; exit 2; }
[[ $# -ge 2 ]] || usage
out=$1; shift
cols=7 width=200 run="" shot=final imgs=() labels=()
while [[ $# -gt 0 ]]; do
    case $1 in
        --cols) cols=$2; shift 2 ;;
        --width) width=$2; shift 2 ;;
        --run) run=$2; shift 2 ;;
        --shot) shot=$2; shift 2 ;;
        -h|--help) usage ;;
        *) imgs+=("$1"); labels+=("$(basename "${1%.*}")"); shift ;;
    esac
done
if [[ -n $run ]]; then
    base=$run
    # a run dir holds one <serial>/ subdirectory; step into it when present
    sub=$(find "$run" -mindepth 1 -maxdepth 1 -type d -name '*0000000*' | head -1)
    [[ -n $sub ]] && base=$sub
    while IFS= read -r d; do
        k=$(basename "$d")
        [[ -f $d/record.json || -f $d/$shot.jpeg ]] || continue
        imgs+=("$d/$shot.jpeg"); labels+=("$k")
    done < <(find "$base" -mindepth 1 -maxdepth 1 -type d | sort)
fi
n=${#imgs[@]}
[[ $n -gt 0 ]] || { echo "contact_sheet: no images" >&2; exit 1; }
command -v ffmpeg >/dev/null || { echo "contact_sheet: ffmpeg not found" >&2; exit 1; }

height=$((width * 8 / 5))   # boards are 1200x1920 portrait
font=$(ls /System/Library/Fonts/PingFang.ttc /System/Library/Fonts/Helvetica.ttc 2>/dev/null | head -1 || true)
fontopt=${font:+fontfile=$font:}
drawtext=0
ffmpeg -hide_banner -filters 2>/dev/null | grep -q ' drawtext ' && drawtext=1
inputs=() filters="" stack="" layout=""
for ((i = 0; i < n; i++)); do
    label=${labels[$i]//[:\']/_}
    if [[ -f ${imgs[$i]} ]]; then
        inputs+=(-i "${imgs[$i]}")
    else
        inputs+=(-f lavfi -i "color=c=gray:s=${width}x${height}")
        label="$label (missing)"
    fi
    if [[ $drawtext == 1 ]]; then
        filters+="[$i:v]scale=${width}:${height},drawbox=y=0:w=iw:h=22:color=black@0.6:t=fill,"
        filters+="drawtext=${fontopt}text='${label}':x=4:y=4:fontsize=14:fontcolor=white[v$i];"
    else
        filters+="[$i:v]scale=${width}:${height}[v$i];"
    fi
    stack+="[v$i]"
    layout+="$(( (i % cols) * width ))_$(( (i / cols) * height ))|"
    printf 'row %d col %d  %s  %s\n' $((i / cols + 1)) $((i % cols + 1)) "$label" "${imgs[$i]}"
done
if [[ $n -eq 1 ]]; then
    ffmpeg -y -loglevel error "${inputs[@]}" -filter_complex "${filters%;}" -map "[v0]" -frames:v 1 "$out"
else
    ffmpeg -y -loglevel error "${inputs[@]}" \
        -filter_complex "${filters}${stack}xstack=inputs=$n:layout=${layout%|}:fill=black[out]" \
        -map "[out]" -frames:v 1 "$out"
fi
echo "contact_sheet: $n tiles -> $out"
