#!/usr/bin/env bash

set -Eeuo pipefail

SELF="${BASH_SOURCE[0]}"
SCRIPT_DIR="$(cd "$(dirname "$SELF")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"

BOARD_61AE="61ae0be500000000000000000324012c"
BOARD_8605="5ce2dcee00000000000000000923012c"
BOARD_5EA1="5ea1719200000000000000001123012c"

HELLOWORLD="$REPO_ROOT/.agents/skills/reproduce-helloworld/scripts/reproduce.sh"
ZIGZAG="$REPO_ROOT/.agents/skills/reproduce-zigzag-apk/scripts/reproduce.sh"
CAPYBARA="$REPO_ROOT/.agents/skills/reproduce-capybara-apk/scripts/reproduce.sh"
BOAT_ATTACK="$REPO_ROOT/.agents/skills/reproduce-boat-attack-apk/scripts/reproduce.sh"

MODE="${1:-}"
BOARD="${2:-}"
DRY_RUN=0

die()
{
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

usage()
{
    printf '%s\n' \
        "usage: $SELF quick <supported-board-serial>" \
        "       $SELF restore <supported-board-serial>" \
        "       $SELF continue-zigzag <supported-board-serial>" \
        "       $SELF continue-capybara <supported-board-serial>" \
        "       $SELF dry-run-quick <supported-board-serial>" \
        "       $SELF dry-run-restore <supported-board-serial>" \
        "       $SELF dry-run-continue-zigzag <supported-board-serial>" \
        "       $SELF dry-run-continue-capybara <supported-board-serial>"
}

case "$MODE" in
    dry-run-*)
        DRY_RUN=1
        MODE="${MODE#dry-run-}"
        ;;
esac

case "$MODE" in
    quick|restore|continue-zigzag|continue-capybara) ;;
    *) usage; exit 2 ;;
esac

# boards beyond the ones listed here: knowledge/boards.json (via the repo's scripts/lab/lab_paths.py)
lab_board_label() { python3 "${REPO_ROOT:-$SCRIPT_DIR/../../../../..}/scripts/lab/lab_paths.py" board-label "$1"; }
case "$BOARD" in
    "$BOARD_61AE") BOARD_LABEL=61ae ;;
    "$BOARD_8605") BOARD_LABEL=8605 ;;
    "$BOARD_5EA1") BOARD_LABEL=5ea1 ;;
    "5ea34a4500000000000000001123012c") BOARD_LABEL=5ea ;;
    "61b0657200000000000000000324012c") BOARD_LABEL=61b ;;
    "5cd1e3dd00000000000000000923012c") BOARD_LABEL=5cd ;;
    *) BOARD_LABEL=$(lab_board_label "$BOARD") || die "unsupported or missing board serial: $BOARD" ;;
esac

for driver in "$HELLOWORLD" "$ZIGZAG" "$CAPYBARA" "$BOAT_ATTACK"; do
    [ -x "$driver" ] || die "missing executable driver: $driver"
done

run_step()
{
    local label=$1
    shift
    printf 'STEP=%s\n' "$label"
    if [ "$DRY_RUN" -eq 1 ]; then
        printf 'COMMAND='
        printf '%q ' "$@"
        printf '\n'
        return 0
    fi
    "$@"
}

case "$MODE" in
    quick)
        run_step helloworld "$HELLOWORLD" quick "$BOARD"
        run_step zigzag "$ZIGZAG" quick "$BOARD"
        ;;
    restore)
        run_step helloworld "$HELLOWORLD" restore "$BOARD"
        run_step zigzag "$ZIGZAG" quick "$BOARD"
        ;;
    continue-zigzag)
        ;;
    continue-capybara)
        ;;
esac

case "$MODE" in
    quick|restore|continue-zigzag)
        run_step capybara-restore "$CAPYBARA" restore "$BOARD"
        run_step capybara-quick "$CAPYBARA" quick "$BOARD"
        ;;
esac

run_step boatattack-restore "$BOAT_ATTACK" restore "$BOARD"
run_step boatattack-quick "$BOAT_ATTACK" quick "$BOARD"

if [ "$DRY_RUN" -eq 1 ]; then
    printf 'SUITE_DRY_RUN=PASS\n'
    exit 0
fi

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$MODE-$BOARD_LABEL"
RUN_DIR="$REPO_ROOT/var/state/reproduce-oh61-game-suite/$RUN_ID"
TMP_RECEIPT="$RUN_DIR/receipt.env.tmp.$$"
mkdir -p "$RUN_DIR"
trap 'rm -f "$TMP_RECEIPT"' EXIT
{
    printf 'suite=reproduce-oh61-game-suite\n'
    printf 'mode=%s\n' "$MODE"
    printf 'board=%s\n' "$BOARD"
    printf 'board_label=%s\n' "$BOARD_LABEL"
    printf 'last_game=BoatAttack\n'
    printf 'result=PASS\n'
} > "$TMP_RECEIPT"
mv "$TMP_RECEIPT" "$RUN_DIR/receipt.env"
trap - EXIT
printf 'REPRODUCE_OH61_GAME_SUITE=PASS\n'
printf 'RECEIPT=%s\n' "$RUN_DIR/receipt.env"
