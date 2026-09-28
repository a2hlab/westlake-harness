#!/bin/bash
# hdc for tools running inside the OrbStack VM a2hlab. The board is USB-attached to the Mac and OrbStack has no
# USB passthrough, so every call is forwarded to the Mac's hdc through OrbStack's `mac` (which preserves argv
# exactly). `file send` names its file relative to cwd, so the Mac-side hdc starts in the Mac view of this
# directory: VM paths appear under ~/OrbStack/a2hlab on the Mac, except /Users/* (the Mac share itself) and the
# source-closure bind mount, which OrbStack does not export and is mapped back to the directory behind it.
MAC_HDC=${MAC_HDC:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}
BIND=/home/dspfac/a2hlab/source-closure/verify

to_mac() {
  case "$1" in
    /Users/*) printf '%s' "$1" ;;
    /mnt/mac/*) printf '%s' "${1#/mnt/mac}" ;;
    "$BIND"|"$BIND"/*) printf '/Users/zhaoyue/OrbStack/a2hlab/home/zhaoyue/a2hlab/ws%s' "${1#"$BIND"}" ;;
    /*) printf '/Users/zhaoyue/OrbStack/a2hlab%s' "$1" ;;
    *) printf '%s' "$1" ;;
  esac
}

args=("$@")
# An absolute local operand of `file send` needs the same translation as the cwd.
for i in "${!args[@]}"; do
  if [ "${args[$i]}" = send ] && [ "$i" -gt 0 ] && [ "${args[$((i - 1))]}" = file ]; then
    j=$((i + 1))
    while [[ "${args[$j]}" == -* ]]; do j=$((j + 1)); done
    [[ "${args[$j]}" == /* ]] && args[$j]=$(to_mac "${args[$j]}")
    break
  fi
done
# `mac` rewrites every argument that starts with "/" into its Mac view -- including board-side paths such as
# the remote operand of `file send`. Ship cwd + argv as one NUL-separated base64 blob (it always begins with
# "L", the encoding of "/") and unpack it on the Mac, so no argument is ever seen, or rewritten, by `mac`.
payload=$(printf '%s\0' "$(to_mac "$(pwd -P)")" "$MAC_HDC" "${args[@]}" | base64 -w0)
exec mac bash -c 'a=(); while IFS= read -r -d "" x; do a+=("$x"); done < <(printf %s "$1" | base64 -D)
cd "${a[0]}" || exit 1; exec "${a[@]:1}"' bash "$payload"
