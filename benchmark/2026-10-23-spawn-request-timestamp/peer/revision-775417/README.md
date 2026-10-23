# T90 revised candidate peer replay

Candidate `7754176b…` passes the unchanged24-case replay (rc0), including read-only and closed stderr, missing/empty/directory uptime, client nonzero statuses, binary stdin, exact argv/stdout, and process hierarchy across `/bin/sh`, `/bin/bash`, `/bin/dash`.

The prior `d82af823…` result remains untouched in `../check.stdout.json` (22 pass,2 fail). This revision adds a builtin newline within a `/dev/null` stdout group; the formerly observed stdout marker spill does not recur in these tests. Frozen candidate/baseline snapshots accompany this result.

This is local offline semantic acceptance only, not deployment, target-shell validation or a latency repair. The revision phase is recorded separately from the original card.

The actual tested snapshot is7754176b; intermediate cb718f changed before the copy and has no independent test claim.
