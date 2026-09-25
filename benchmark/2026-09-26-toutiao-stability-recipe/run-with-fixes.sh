#!/system/bin/sh
# Usage: sh <runtime>/stability46/run-with-fixes.sh <privileged launch command> [args...]
set -eu
[ "$#" -gt 0 ] || { echo 'launch command required' >&2; exit 2; }
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
(cd "$here/.." && sha256sum -c stability46/SHA256SUMS)
/system/bin/sh "$here/prelaunch_map_count.sh"
exec "$@"
