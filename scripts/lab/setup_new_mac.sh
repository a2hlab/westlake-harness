#!/bin/bash
# Set up a new control Mac for this lab after unpack_airdrop.sh (env.md §4, §6, §9).
#
#   scripts/lab/setup_new_mac.sh [check|install]      default: check (report only, changes nothing)
#
# install does what can be automated, each step idempotent: Homebrew formulae and casks (OrbStack, Android
# command-line tools), the Android SDK pieces env-mac.sh uses, the mise-pinned JDK/Python, the westlake-inputs
# venv (scripts/lab/venv-requirements.txt + this repo editable), Rust + agent-spec, the a2hlab VM (create, apt,
# sync <workspaces>/_a2hlab, author-path bind mount) and the dockbuild image. Things that need a login or a
# GUI (Xcode command-line tools, Homebrew itself, DevEco Studio for hdc, model/agent CLIs, credentials) are
# only reported. Ends with the smoke checks.
set -uo pipefail
MODE=${1:-check}
case $MODE in check|install) ;; *) echo "usage: setup_new_mac.sh [check|install]"; exit 2;; esac
. "$(dirname "${BASH_SOURCE[0]}")/lab_paths.sh" || exit 1
H=$WORKSPACES/westlake-harness; IN=$WORKSPACES/westlake-inputs
SDK=$HOME/Library/Android/sdk
HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
AUTHOR=/home/dspfac/a2hlab/source-closure/verify   # original author's path: build outputs hash-match manifests
missing=0
ok()   { printf '  ok      %s\n' "$*"; }
miss() { printf '  MISSING %s\n' "$*"; missing=$((missing+1)); }
todo() { printf '  MANUAL  %s\n' "$*"; missing=$((missing+1)); }
run()  { if [ "$MODE" = install ]; then echo "  + $*"; "$@"; else return 1; fi; }
have() { command -v "$1" >/dev/null 2>&1; }

echo "== base (manual)"
xcode-select -p >/dev/null 2>&1 && ok "Xcode command-line tools" || todo "xcode-select --install"
have brew && ok "Homebrew" || todo "Homebrew: see https://brew.sh (one-line installer, needs your password)"

echo "== Homebrew formulae / casks"
if have brew; then
  for f in git gh python@3.14 ffmpeg coreutils jq zstd rsync mise node; do
    brew list --formula "$f" >/dev/null 2>&1 && ok "$f" || { run brew install "$f" && ok "$f (installed)" || miss "brew install $f"; }
  done
  [ -d /Applications/OrbStack.app ] || brew list --cask orbstack >/dev/null 2>&1 && ok "orbstack" \
    || { run brew install --cask orbstack && ok "orbstack (installed)" || miss "brew install --cask orbstack"; }
  command -v sdkmanager >/dev/null || ls "$HOME"/Library/Android/sdk/cmdline-tools/*/bin/sdkmanager >/dev/null 2>&1 \
    && ok "Android sdkmanager" || { run brew install --cask android-commandlinetools && ok "android-commandlinetools (installed)" \
    || miss "brew install --cask android-commandlinetools (or Android Studio)"; }
fi

echo "== Android SDK ($SDK)"
SDKM=$(command -v sdkmanager || ls "$SDK"/cmdline-tools/latest/bin/sdkmanager 2>/dev/null | head -1)
for pkg in "platform-tools" "ndk;23.1.7779620" "build-tools;34.0.0"; do
  d="$SDK/${pkg//;//}"
  [ -d "$d" ] && ok "$pkg" || { [ -n "$SDKM" ] && run "$SDKM" --sdk_root="$SDK" "$pkg" && ok "$pkg (installed)" || miss "sdkmanager --sdk_root=$SDK '$pkg'"; }
done

echo "== DevEco Studio (hdc to the boards)"
[ -x "$HDC" ] && ok "hdc $("$HDC" -v 2>/dev/null | head -1)" || todo "install DevEco Studio (Huawei developer login) into /Applications; hdc is at $HDC"

echo "== mise-pinned JDK / Python ($IN/mise.toml)"
if have mise && [ -f "$IN/mise.toml" ]; then
  (cd "$IN" && mise where java >/dev/null 2>&1 && mise where python >/dev/null 2>&1) && ok "temurin 21 + python 3.12" \
    || { (cd "$IN" && run mise install) && ok "mise install" || miss "(cd $IN && mise install)"; }
else miss "mise and $IN/mise.toml"; fi

echo "== westlake-inputs venv"
if [ -x "$IN/venv/bin/python" ] && "$IN/venv/bin/python" -c 'import androguard, lxml, yaml' 2>/dev/null; then ok "venv"
elif [ "$MODE" = install ] && have mise; then
  PY=$(cd "$IN" && mise where python)/bin/python3
  run "$PY" -m venv "$IN/venv" && run "$IN/venv/bin/pip" install -q -r "$H/scripts/lab/venv-requirements.txt" \
    && run "$IN/venv/bin/pip" install -q -e "$H" && ok "venv (rebuilt)" || miss "venv rebuild failed"
else miss "venv: python3.12 -m venv $IN/venv && pip install -r scripts/lab/venv-requirements.txt && pip install -e ."; fi

echo "== Rust / agent-spec"
have cargo && ok "cargo" || { run brew install rust && ok "cargo (installed)" || miss "cargo (brew install rust, or rustup)"; }
have agent-spec && ok "agent-spec $(agent-spec --version 2>/dev/null)" \
  || { have cargo && run cargo install agent-spec --version 1.4.0 --locked && ok "agent-spec (installed)" || miss "cargo install agent-spec --version 1.4.0"; }

echo "== OrbStack VM a2hlab"
vm_exists() { orb list 2>/dev/null | grep '^a2hlab' >/dev/null; }  # no grep -q: with pipefail an early exit fails the pipe
if have orb; then
  vm_exists && ok "VM a2hlab exists" \
    || { run orb create --arch amd64 ubuntu:noble a2hlab && ok "VM a2hlab (created)" || miss "orb create --arch amd64 ubuntu:noble a2hlab"; }
  if vm_exists; then
    orb -m a2hlab bash -lc 'command -v ccache zstd rsync >/dev/null' && ok "VM build packages" \
      || { run orb -m a2hlab bash -lc 'sudo apt-get update -q && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q build-essential ccache git git-lfs python3 python3-yaml python3-venv rsync unzip zip xz-utils zstd xxd' \
           && ok "VM build packages (installed)" || miss "VM apt packages (env.md §6)"; }
    orb -m a2hlab bash -lc 'test -d ~/a2hlab/ws/toolchains/clang-15' && ok "VM ~/a2hlab/ws/toolchains" \
      || { [ -d "$WORKSPACES/_a2hlab/ws" ] && run orb -m a2hlab bash -lc "mkdir -p ~/a2hlab && rsync -a '$WORKSPACES/_a2hlab/' ~/a2hlab/" \
           && ok "VM ~/a2hlab (synced from _a2hlab)" || miss "sync $WORKSPACES/_a2hlab into the VM's ~/a2hlab"; }
    orb -m a2hlab bash -lc "mountpoint -q $AUTHOR" && ok "author path bind mount" \
      || { run orb -m a2hlab bash -lc "sudo mkdir -p $AUTHOR && sudo mount --bind ~/a2hlab/ws $AUTHOR" \
           && ok "author path bind mount (done; redo after every VM restart)" || miss "bind ~/a2hlab/ws at $AUTHOR in the VM"; }
  fi
else miss "OrbStack (brew install --cask orbstack), then re-run"; fi

echo "== dockbuild image"
if have docker && docker image inspect a2hlab-build:24.04 >/dev/null 2>&1; then ok "a2hlab-build:24.04"
else run bash "$H/scripts/lab/dockbuild.sh" image && ok "a2hlab-build:24.04 (built)" || miss "scripts/lab/dockbuild.sh image"; fi

echo "== agent tooling and credentials (report only)"
for t in claude codex octos octoscode herdr; do have "$t" && ok "$t" || todo "$t (env.md §4)"; done
ssh -o BatchMode=yes -o ConnectTimeout=5 hw248 true 2>/dev/null && ok "ssh hw248" || todo "ssh hw248: ~/.ssh/config + key (env.md §8)"
gh auth status >/dev/null 2>&1 && ok "gh auth" || todo "gh auth login (a2hlab org access)"

echo "== smoke checks"
python3 "$H/scripts/lab/check_user_paths.py" >/dev/null 2>&1 && ok "check_user_paths" || miss "check_user_paths.py"
(cd "$H/scripts/lab" && python3 -m unittest discover -p 'test_*.py' >/dev/null 2>&1) && ok "scripts/lab unit tests" || miss "scripts/lab unit tests"
(cd "$H/benchmark/2026-09-28-bms-route-deploy/batch" && python3 -m unittest test_bms_batch >/dev/null 2>&1) && ok "bms_batch tests" || miss "bms_batch tests"
[ -x "$HDC" ] && { n=$("$HDC" list targets 2>/dev/null | grep -c .); [ "$n" -gt 0 ] && ok "hdc sees $n board(s)" || todo "no board connected (fine until the boards move)"; }

echo; [ $missing -eq 0 ] && echo "ALL OK" || echo "$missing item(s) to do (MISSING = '$0 install' can fix; MANUAL = needs you)"
