#!/usr/bin/env bash
# Prepare an isolated collector runtime. Does not start/stop watchers or harvest.
set -euo pipefail
src=${1:?usage: prepare-runtime.sh OCTOSCODE_SCRIPTS NEW_RUNTIME_DIR}
dst=${2:?usage: prepare-runtime.sh OCTOSCODE_SCRIPTS NEW_RUNTIME_DIR}
[ ! -e "$dst" ] || { echo 'refuse: runtime destination already exists' >&2; exit 1; }
export PATH="/opt/homebrew/opt/coreutils/libexec/gnubin:$PATH"
stat --version >/dev/null
command -v flock >/dev/null
python3 - "$src" "$dst" <<'PY'
import hashlib,pathlib,shutil,sys
src,dst=map(pathlib.Path,sys.argv[1:])
f=src/'olp-evo-harvest.sh'
assert hashlib.sha256(f.read_bytes()).hexdigest()=='9aa8dfda365167a0ccbdb5cd91498b812b1c7962dcddaa84072b6a3c9331cdef','upstream changed; review again'
dst.mkdir(parents=True)
for name in ['olp-watch-board.sh','olp-evo-harvest.sh','olp-evo-retro.sh','olp-evo-lib.py','olp-board-append.sh']:
 shutil.copy2(src/name,dst/name)
f=dst/'olp-evo-harvest.sh';s=f.read_text();old="local_id=${local_id%%[$'\\uff08' ]*}";assert s.count(old)==1
f.write_text(s.replace(old,'local_id=${local_id%%[!0-9]*}'))
assert hashlib.sha256(f.read_bytes()).hexdigest()=='b52e7879b37a054f8aa25a5d26e045ed0768fe567f90059e8693edded41a53c0'
PY
cat > "$dst/watch.sh" <<'WATCH'
#!/usr/bin/env bash
set -euo pipefail
repo=${1:?usage: watch.sh REPO TOKEN}; token=${2:?usage: watch.sh REPO TOKEN}
export PATH="/opt/homebrew/opt/coreutils/libexec/gnubin:$PATH"
export OLP_EVO_REVIEW_BOARD="$repo/.octos/boards/app-lighting.md"
[ ! -x "$repo/scripts/olp-evo-harvest.sh" ] || { echo 'refuse: repo-local harvester would shadow isolated fix' >&2; exit 1; }
exec /bin/bash "$(dirname "$0")/olp-watch-board.sh" "$OLP_EVO_REVIEW_BOARD" "$token" --harvest "$repo"
WATCH
chmod +x "$dst/watch.sh"
printf 'prepared %s; no watcher or harvest started\n' "$dst"
