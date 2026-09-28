#!/usr/bin/env bash
# Stable Mac -> AlexPC Windows OpenSSH -> WSL2 executor entry.
set -euo pipefail

SSH_HOST=${ALEXPC_SSH_HOST:-AlexPC}
WINDOWS_USER=${ALEXPC_WINDOWS_USER:-mobil}
WSL_DISTRO=${ALEXPC_WSL_DISTRO:-Ubuntu}
WSL_HOME=${ALEXPC_WSL_HOME:-/home/alexyang}

usage()
{
    cat <<'EOF'
Usage:
  scripts/alexpc_wsl_executor.sh probe
  scripts/alexpc_wsl_executor.sh exec COMMAND [ARG ...]
  scripts/alexpc_wsl_executor.sh shell < script.sh

Defaults bind the known-good AlexPC route:
  Windows SSH user: mobil
  WSL distribution: Ubuntu
  WSL working dir:  /home/alexyang

Override with ALEXPC_SSH_HOST, ALEXPC_WINDOWS_USER,
ALEXPC_WSL_DISTRO, or ALEXPC_WSL_HOME.
EOF
}

case "$WINDOWS_USER:$WSL_DISTRO" in
    *[!A-Za-z0-9._:-]*)
        echo "unsafe AlexPC user or WSL distro name" >&2
        exit 2
        ;;
esac
case "$WSL_HOME" in
    /*) ;;
    *) echo "ALEXPC_WSL_HOME must be absolute" >&2; exit 2 ;;
esac

ssh_wsl()
{
    ssh -T \
        -o BatchMode=yes \
        -o ConnectTimeout=10 \
        -o ServerAliveInterval=20 \
        -l "$WINDOWS_USER" "$SSH_HOST" \
        "wsl.exe -d $WSL_DISTRO -- bash -s"
}

write_prelude()
{
    printf 'set -euo pipefail\n'
    printf 'cd %q\n' "$WSL_HOME"
}

mode=${1:-}
case "$mode" in
    probe)
        {
            write_prelude
            cat <<'EOF'
printf 'ALEXPC_WSL_EXECUTOR_PASS user=%s host=%s arch=%s cwd=%s\n' \
    "$(whoami)" "$(hostname)" "$(uname -m)" "$PWD"
findmnt -T "$PWD" -n -o FSTYPE,SOURCE,TARGET
df -h "$PWD" | tail -1
EOF
        } | ssh_wsl
        ;;
    exec)
        shift
        [ "$#" -gt 0 ] || { usage >&2; exit 2; }
        {
            write_prelude
            printf 'exec'
            printf ' %q' "$@"
            printf '\n'
        } | ssh_wsl
        ;;
    shell)
        shift
        [ "$#" -eq 0 ] || { usage >&2; exit 2; }
        {
            write_prelude
            cat
        } | ssh_wsl
        ;;
    *)
        usage >&2
        exit 2
        ;;
esac
