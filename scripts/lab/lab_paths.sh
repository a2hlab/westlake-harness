# Where the lab lives, without a user-specific absolute path (gate: check_user_paths.py). Source it:
#   . "$(dirname "${BASH_SOURCE[0]}")/lab_paths.sh" || exit 1
# Sets WORKSPACES (the directory holding westlake-harness/ and westlake-inputs/) unless it is already set, by
# walking up from this file's real location to the first directory that contains westlake-inputs/ or
# westlake-harness/. This file exists both in westlake-harness/scripts/lab/ and in its live mirror
# westlake-inputs/tools/, at different depths, so a fixed number of `..` would be wrong for one of them.
# Also defines lab_vm_home (the a2hlab VM user's $HOME as the VM sees it) and lab_mac_home (the Mac user's
# $HOME, also valid inside the VM, where /Users is shared).
if [ -z "${WORKSPACES:-}" ]; then
  _lab_d=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
  while [ -n "$_lab_d" ]; do
    if [ -d "$_lab_d/westlake-inputs" ] || [ -d "$_lab_d/westlake-harness" ]; then WORKSPACES=$_lab_d; break; fi
    [ "$_lab_d" = / ] && break
    _lab_d=$(dirname "$_lab_d")
  done
  unset _lab_d
  if [ -z "${WORKSPACES:-}" ]; then
    echo "lab_paths.sh: no directory holding westlake-inputs/ or westlake-harness/ above ${BASH_SOURCE[0]}; set WORKSPACES" >&2
    return 1
  fi
fi

# lab_vm_home: inside the VM (OrbStack's `mac` exists) our own $HOME; on the Mac ask the VM -- the Mac and VM
# user names need not match. Override: A2HLAB_VM_HOME.
lab_vm_home() {
  if [ -n "${A2HLAB_VM_HOME:-}" ]; then printf '%s\n' "$A2HLAB_VM_HOME"
  elif command -v mac >/dev/null 2>&1; then printf '%s\n' "$HOME"
  else orb -m a2hlab bash -c 'printf "%s\n" "$HOME"'
  fi
}

# lab_mac_home: on the Mac our own $HOME; inside the VM ask the Mac. Override: MAC_HOME.
lab_mac_home() {
  if [ -n "${MAC_HOME:-}" ]; then printf '%s\n' "$MAC_HOME"
  elif command -v mac >/dev/null 2>&1; then mac sh -c 'printf "%s\n" "$HOME"'
  else printf '%s\n' "$HOME"
  fi
}
