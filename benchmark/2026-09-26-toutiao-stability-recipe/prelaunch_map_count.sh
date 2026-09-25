#!/system/bin/sh
# Run by the privileged launcher BEFORE source_app_namespace changes identity.
# --check is used inside run.sh. --file is only for an offline regular-file test.
set -eu
check=0
file=/proc/sys/vm/max_map_count
while [ "$#" -gt 0 ]; do
    case "$1" in
        --check) check=1; shift ;;
        --file) [ "$#" -ge 2 ] || exit 2; file=$2; shift 2 ;;
        --) shift; break ;;
        *) echo "unexpected option: $1" >&2; exit 2 ;;
    esac
done
before=$(cat "$file")
case "$before" in ''|*[!0-9]*) echo 'invalid max_map_count' >&2; exit 1 ;; esac
if [ "$before" -lt 1048576 ]; then
    if [ "$check" = 1 ]; then
        echo "STABILITY46_MAP_COUNT_FAIL value=$before required=1048576; use privileged run-with-fixes.sh" >&2
        exit 1
    fi
    printf '%s\n' 1048576 > "$file"
fi
after=$(cat "$file")
case "$after" in ''|*[!0-9]*) exit 1 ;; esac
[ "$after" -ge 1048576 ] || exit 1
echo "STABILITY46_MAP_COUNT_PASS before=$before after=$after minimum=1048576" >&2
if [ "$#" -gt 0 ]; then exec "$@"; fi
