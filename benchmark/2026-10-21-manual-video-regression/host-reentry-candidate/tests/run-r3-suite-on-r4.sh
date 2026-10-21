#!/bin/sh
# Regression: run the UNCHANGED r3 retirement/single-reentry suite (reentry-retirement-01, 71 tests)
# against the r4 watchdog + r4 reentry-common. The original suite file is not modified: a temp copy
# only redirects its helper directory to an overlay (r2 helpers + r4 reentry-common.sh).
set -u
HERE=$(CDPATH= cd -P "$(dirname "$0")" && pwd -P)
CAND=$(CDPATH= cd -P "$HERE/.." && pwd -P)
REPO=$(CDPATH= cd -P "$CAND/../../.." && pwd -P)
ORIG="$REPO/benchmark/2026-10-21-t34-demo61b-video/reentry-retirement-01/tests/run-retirement-tests.sh"
R2P="$REPO/benchmark/2026-10-19-toutiao-icon-reentry/candidate-payload-r2/payload"
TMPW=$(mktemp -d "${TMPDIR:-/tmp}/rc-r3on4.XXXXXX") || exit 2
trap 'rm -rf "${TMPW:?}"' EXIT
mkdir "$TMPW/helpers" "$TMPW/tests"; cp "$R2P"/*.sh "$TMPW/helpers/"
cp "$CAND/src/reentry-common-r4.sh" "$TMPW/helpers/reentry-common.sh"
grep -c '^R2P="\$REPO/benchmark/2026-10-19-toutiao-icon-reentry/candidate-payload-r2/payload"$' "$ORIG" | grep -qx 1 || { echo "R2P line not unique" >&2; exit 2; }
sed "s#^R2P=.*#R2P='$TMPW/helpers'#" "$ORIG" > "$TMPW/tests/run-retirement-tests.sh"
# The copy resolves NEW/REPO from its own location; pin them back to the real tree.
sed -i.bak -e "s#^HERE=.*#HERE='$(dirname "$ORIG")'#" "$TMPW/tests/run-retirement-tests.sh"
sh256() { (sha256sum "$1" 2>/dev/null || shasum -a 256 "$1") | cut -d' ' -f1; }
C4=$(sh256 "$CAND/src/reentry-common-r4.sh")
RETIRE_UNDER_TEST="${R4_UNDER_TEST:-$CAND/src/watchdog-reentry-r4.sh}" sh "$TMPW/tests/run-retirement-tests.sh" > "$TMPW/out" 2>&1
cat "$TMPW/out"
# Exactly one failure is expected by construction: the suite pins the r3 common hash, and the
# overlay deliberately carries r4 common. Any other failure (or a different hash) is a regression.
fails=$(grep '^FAIL ' "$TMPW/out")
want="FAIL src.r2_common_unchanged : expected [43d7b073467708770c8c69724633666e410d45581f8c0099d5098c31215e78ab] got [$C4]"
if [ "$fails" = "$want" ] && grep -q '^70 passed, 1 failed$' "$TMPW/out"; then
	echo "R3_ON_R4 OK: 70 behavioural pass; only expected hash pin differs (r4 common $C4)"; exit 0
fi
echo "R3_ON_R4 REGRESSION"; exit 1
