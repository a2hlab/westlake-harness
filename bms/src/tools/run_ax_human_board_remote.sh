#!/bin/sh
set -eu

agent_root=${1:?remote agent root is required}
lock_dir="${agent_root}/watcher.lock"
pid_file="${agent_root}/watcher.pid"
shared_output=${AX_HUMAN_BOARD_SHARED_OUTPUT:-/Users/Shared/Bridge-HUMAN_BOARD.html}
mirror_pid=

if ! mkdir "${lock_dir}" 2>/dev/null; then
    echo "remote watcher lock already held" >&2
    exit 73
fi

cleanup() {
    if [ -n "${mirror_pid}" ]; then
        kill "${mirror_pid}" 2>/dev/null || true
        wait "${mirror_pid}" 2>/dev/null || true
    fi
    rm -f "${pid_file}"
    rmdir "${lock_dir}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "$$" > "${pid_file}"

mirror_shared_output() {
    source_output="${agent_root}/output/HUMAN_BOARD.html"
    while :; do
        if [ -f "${source_output}" ]; then
            temporary_output="${shared_output}.tmp.$$"
            cp "${source_output}" "${temporary_output}"
            chmod 0644 "${temporary_output}"
            mv -f "${temporary_output}" "${shared_output}"
        fi
        sleep 5
    done
}

mirror_shared_output &
mirror_pid=$!

python3 "${agent_root}/root/tools/ax_human_board.py" \
    --bundle-snapshot "${agent_root}/inbox/snapshot.json" \
    --output "${agent_root}/output/HUMAN_BOARD.html" \
    watch --interval 20
