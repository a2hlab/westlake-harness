#!/bin/bash
# hdc for tools running inside the OrbStack VM a2hlab. The board is USB-attached to the Mac and OrbStack has no
# USB passthrough, so every call is forwarded to the Mac's hdc through OrbStack's `mac` (which preserves argv
# exactly). `file send` names its file relative to cwd, so the Mac-side hdc starts in the Mac view of this
# directory: VM paths appear under ~/OrbStack/a2hlab on the Mac, except /Users/* (the Mac share itself) and the
# source-closure bind mount, which OrbStack does not export and is mapped back to the directory behind it.
#
# The ~/OrbStack view is an NFS mount that is not always there (2026-09-28: absent while OrbStack ran, which
# made every call from a VM cwd fail at `cd`). When a translated path does not exist on the Mac, fall back to
# a Mac-visible staging dir under /Users: local operands of `file send`/`install` are copied there first, and
# `file recv` lands there and is copied back to the VM destination afterwards.
MAC_HDC=${MAC_HDC:-/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc}
BIND=/home/dspfac/a2hlab/source-closure/verify
# The VM user's home ($HOME here) and the Mac user's home need not share a user name. The VM always sees
# ~/OrbStack/<machine>, the Mac only while the NFS view is mounted -- so ask the Mac, once, for both its home
# and whether the view is there (override the home with MAC_HOME).
MAC_VIEW=0
if [ -n "${MAC_HOME:-}" ]; then
  mac test -d "$MAC_HOME/OrbStack/a2hlab/home" 2>/dev/null && MAC_VIEW=1
else
  # the mac bridge occasionally answers empty right after OrbStack restarts (2026-09-30 U4 sweep stopped twice):
  # retry, then fall back to the /Users/<name> prefix of this script's own path (the VM sees the Mac's /Users)
  for _try in 1 2 3; do
    read -r MAC_HOME MAC_VIEW < <(mac sh -c 'v=0; test -d "$HOME/OrbStack/a2hlab/home" && v=1; printf "%s %s\n" "$HOME" "$v"' 2>/dev/null)
    case "${MAC_HOME:-}" in /Users/?*) break ;; esac; sleep 1
  done
  if [ -z "${MAC_HOME:-}" ]; then
    _self=$(cd "$(dirname "$0")" && pwd -P)
    case "$_self" in /Users/*/*) MAC_HOME=/Users/$(printf '%s' "$_self" | cut -d/ -f3)
      mac test -d "$MAC_HOME/OrbStack/a2hlab/home" 2>/dev/null && MAC_VIEW=1 ;; esac
  fi
fi
case "${MAC_HOME:-}" in /Users/?*) ;; *) echo "hdc_mac: cannot read the Mac home via OrbStack's mac (set MAC_HOME)" >&2; exit 1 ;; esac

to_mac() {
  case "$1" in
    /Users/*) printf '%s' "$1" ;;
    /mnt/mac/*) printf '%s' "${1#/mnt/mac}" ;;
    "$BIND"|"$BIND"/*) printf '%s/OrbStack/a2hlab%s/a2hlab/ws%s' "$MAC_HOME" "$HOME" "${1#"$BIND"}" ;;
    /*) printf '%s/OrbStack/a2hlab%s' "$MAC_HOME" "$1" ;;
    *) printf '%s' "$1" ;;
  esac
}
visible() {  # visible <mac-path>: will the Mac-side hdc find it?
  case "$1" in
    "$MAC_HOME"/OrbStack/*) [ "$MAC_VIEW" = 1 ] ;;
    /Users/*) [ -e "$1" ] ;;
    *) return 1 ;;
  esac
}

STAGE=""
stage_dir() { [ -n "$STAGE" ] || STAGE=$(mktemp -d "$MAC_HOME/.cache/hdc_mac.XXXXXX"); }
mkdir -p "$MAC_HOME/.cache"
# stage_local <vm-path>: set STAGED to a Mac-visible path holding the same content (no subshell, so the
# staging dir is created -- and later removed -- by this process)
stage_local() {
  local p=$1 m
  [[ "$p" == /* ]] || p="$(pwd -P)/$p"
  m=$(to_mac "$p")
  if visible "$m"; then STAGED=$m; return; fi
  stage_dir
  cp -a "$p" "$STAGE/" || { echo "hdc_mac: cannot stage $p" >&2; rm -rf "$STAGE"; exit 1; }
  STAGED="$STAGE/$(basename "$p")"
}

args=("$@")
recv_back=""   # "<staged-path>\t<vm-destination>" for a recv whose destination the Mac cannot see
for i in "${!args[@]}"; do
  prev=""; [ "$i" -gt 0 ] && prev=${args[$((i - 1))]}
  if { [ "${args[$i]}" = send ] && [ "$prev" = file ]; } || [ "${args[$i]}" = install ]; then
    j=$((i + 1))
    while [[ "${args[$j]}" == -* ]]; do j=$((j + 1)); done
    if [ -n "${args[$j]:-}" ]; then stage_local "${args[$j]}"; args[$j]=$STAGED; fi
    break
  fi
  if [ "${args[$i]}" = recv ] && [ "$prev" = file ]; then
    j=$((i + 1))
    while [[ "${args[$j]}" == -* ]]; do j=$((j + 1)); done
    k=$((j + 1))                                   # local destination follows the remote operand
    if [ -n "${args[$k]:-}" ]; then
      d=${args[$k]}; [[ "$d" == /* ]] || d="$(pwd -P)/$d"
      m=$(to_mac "$d")
      if ! visible "$(dirname "$m")"; then
        stage_dir
        args[$k]="$STAGE/recv"
        recv_back="$STAGE/recv	$d	$(basename "${args[$j]}")"
      else
        args[$k]=$m
      fi
    fi
    break
  fi
done

cwd=$(to_mac "$(pwd -P)")
if ! visible "$cwd"; then stage_dir; cwd=$STAGE; fi

# `mac` rewrites every argument that starts with "/" into its Mac view -- including board-side paths such as
# the remote operand of `file send`. Ship cwd + argv as one NUL-separated base64 blob (it always begins with
# "L", the encoding of "/") and unpack it on the Mac, so no argument is ever seen, or rewritten, by `mac`.
payload=$(printf '%s\0' "$cwd" "$MAC_HDC" "${args[@]}" | base64 -w0)
mac bash -c 'a=(); while IFS= read -r -d "" x; do a+=("$x"); done < <(printf %s "$1" | base64 -D)
cd "${a[0]}" || exit 1; exec "${a[@]:1}"' bash "$payload"
rc=$?
if [ -n "$recv_back" ] && [ $rc -eq 0 ]; then
  IFS='	' read -r src dst rname <<< "$recv_back"
  if [ -d "$src" ]; then mkdir -p "$dst" && cp -a "$src"/. "$dst"/
  elif [ -d "$dst" ]; then cp -a "$src" "$dst/$rname"     # hdc keeps the remote name inside a directory
  else cp -a "$src" "$dst"; fi || rc=1
fi
[ -n "$STAGE" ] && rm -rf "$STAGE"
exit $rc
