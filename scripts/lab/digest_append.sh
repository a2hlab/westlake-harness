#!/bin/bash
# Append one knowledge line to .octos/KNOWLEDGE-DIGEST.md and flag an unproven cause before it becomes "known".
#
#   digest_append.sh [--digest PATH] <text...>        # or the text on stdin
#
# EVO-0037/0038/0045 (2026-09-30 .. 10-01): the outer loop wrote a lane's stated hypothesis into the DIGEST as a
# proven cause (RB root cause, the ANL culprit from one bisect run, the N7 libz shell). A line that names a cause
# (导致 / 根因 / 原因 / 造成 / 因为 / 让…崩 / caused / root cause) must also carry what proves it — a single-variable
# comparison, a same-window control, or compare_runs "variables: 1" — or say it is a suspect/hypothesis.
# Without either, this prints a warning and exits 3 WITHOUT appending; --force appends anyway (use it only when
# the evidence is in the line in words this check does not know).
set -euo pipefail
DIGEST="$(cd "$(dirname "$0")/../.." && pwd)/.octos/KNOWLEDGE-DIGEST.md"
FORCE=0
while [ $# -gt 0 ]; do
  case $1 in
    --digest) DIGEST=$2; shift 2 ;;
    --force) FORCE=1; shift ;;
    *) break ;;
  esac
done
if [ $# -gt 0 ]; then TEXT="$*"; else TEXT=$(cat); fi
[ -n "${TEXT//[[:space:]]/}" ] || { echo "digest_append: empty text" >&2; exit 2; }
case $TEXT in "- "*) ;; *) TEXT="- $TEXT" ;; esac
CAUSE='导致|根因|原因是|造成|因为|让[^,,。]{0,12}(崩|挂|死|失败)|caused|root cause'
PROOF='单变量|同窗|同板|variables: ?1|compare_runs|对照|A/B|嫌疑|假设|未证|hypothesis|suspect'
if [ "$FORCE" = 0 ] && printf '%s' "$TEXT" | grep -Eq "$CAUSE" && ! printf '%s' "$TEXT" | grep -Eq "$PROOF"; then
  echo "digest_append: the line names a cause but no evidence of it (single variable / same-window control /" >&2
  echo "  compare_runs variables: 1) and does not call it a suspect or hypothesis. Not appended; add the evidence," >&2
  echo "  mark it 嫌疑/假设, or re-run with --force. (EVO-0037/0038/0045)" >&2
  exit 3
fi
printf '%s\n' "$TEXT" >> "$DIGEST"
echo "digest_append: appended to $DIGEST"
