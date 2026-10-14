# JIT51 explicit UID successor (disabled)

This independent source retains the frozen5cdJIT51 directory behavior. Its only changes replace the fixed UID with required `--expected-uid N` and check that **both** installed imehost root owner and the current private `/data/data` owner match N:N before any mkdir/chown. Missing, invalid or mismatching UID refuses. It never guesses UID from the system namespace.

Proposed caller, only inside the original verified parent mount namespace:

```sh
/system/bin/sh /data/local/tmp/asx/prepare_jit51-owner.sh --expected-uid "$AUTH_UID"
```

AUTH_UID must come from the original independently observed installed-host binding. The file itself is the same full SHA on61b/5cd; only the explicitly pinned wrapper invocation parameter differs. The caller's serial/boot/parent/executable/namespace/window guards remain mandatory. The script has no default and rejects the old system/data namespace even with an otherwise valid expected UID.

Do not install this file alone. Reuse original prepare/compile to produce a new candidate JIT target, STARTUP_JIT_SHA and spawn wrapper argv/hash, then regenerate startup/members/realization. Old frozen scripts and signed proof remain historical. No runtime, deployment or board call was made in this subtask. Seven offline tests cover both existing UIDs, wrong UID, wrong namespace, missing/invalid arguments and frozen base byte equality. Full directory logic remains covered by the separate nine-test5cdcandidate; these new tests execute the real added shell gate only, not device mutation.
