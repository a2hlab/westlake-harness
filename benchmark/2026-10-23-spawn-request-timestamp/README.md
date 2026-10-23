# T90 request-before-client timestamp — revision 2 (offline)

The original six shell cases passed, but independent peer testing found stdout marker leakage with read-only stderr in `/bin/sh` and `/bin/bash` (22/24 passed). The original delivery and failure output remain under `.private/revision-02/`; they are not reclassified as passing.

The revision temporarily directs a brace group's stdout to `/dev/null`, redirects only the marker printf to original stderr, then writes a newline to the group's `/dev/null` stdout before restoring it. A bare group and an empty printf both failed the same tests; their raw results are retained. The nonempty sink write prevents the observed buffered marker from later leaking onto client stdout. No subshell or external logging process is added. The original 207-byte entry's client command and argv remain unchanged, last in the script; no timeout, check, socket or execution hierarchy changes.

Actual revision tests: eight local `/bin/sh` baseline/candidate cases passed, including read-only stderr with and without `-e`. The exact peer checker was replayed unchanged: 24/24 passed across `/bin/sh`, `/bin/bash`, `/bin/dash`, comparing stdin/stdout/return code/argv/hierarchy/stderr. Independent peer rerun is pending. No device shell or real client was executed.

Reproduce: `python3 test_semantics.py --out .private/shell-new`. Raw commands/start/end/rc/stdout/stderr are in `.private/shell-03` and `.private/revision-02`, pinned in `raw-index.json`. Missing logging is missing evidence. This is request observation only, not deployment or white-screen repair. No guardian/reentry source was read; no commit or push.
