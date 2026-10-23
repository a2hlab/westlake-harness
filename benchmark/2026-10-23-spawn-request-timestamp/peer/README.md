# T90 independent semantic review: reject current candidate

The timestamp is not always confined to stderr. With stderr supplied as a read-only fd, candidate line4 appends `[WL-SPAWN-REQUEST] uptime_s=1234.56` plus newline to **stdout** after client output under local `/bin/sh` and `/bin/bash`. Baseline stdout has no marker. This violates the logging-failure preservation requirement; target-shell behavior has not been tested.

Independent fake-client replay:24 cases across3 real shells;22 pass,2 fail; checker rc1. All cases preserve argv, binary stdin, client exit status and observed process hierarchy. Missing/empty/directory uptime and closed stderr continue executing the client. `/bin/dash` passes the read-only-fd case.

See `check.stdout.json` for exact baseline/candidate bytes, `review.json` for source SHA and command, and `check_semantics.py` for reproduction. Candidate unchanged, no device calls and no real client/socket execution. Author should resolve the stdout regression before acceptance; this review supplies no deployment or runtime-fix claim.
