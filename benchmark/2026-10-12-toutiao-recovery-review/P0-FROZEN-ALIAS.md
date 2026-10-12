# P0 exact executable aliases: offline acceptance

## Immutable evidence and results

Commit `0cc5a5bdd9f5c390a9324916189d726daa63a637` was exported directly from
Git into `.artifacts/exe-alias-0cc5a5bd/frozen/`. Its archived base payload was
also exported from that same object. The original executor package has no
delta from reviewed 9436; historical watchdog976/helper80a are unchanged.
All 18 alias-manifest rows match actual Git SHA and byte length.

Independent execution of the six frozen alias tests: **6/6, exit 0, 0.291s**.
Static source/binding check: **exit 0**, three exact path-predicate deltas.
No R1 full suite, Rust execution, device/VM/remote, build, signal, data mutation,
privacy action or signature occurred. The new Rust wrapper was read only;
the author's three Rust PASS results are not relabeled as independent reruns.

| New object | SHA256 |
| --- | --- |
| launch-common.sh | d065f354392096819c93c808b89205355d62b333ff115fbadb8b9db38cbaa507 |
| watchdog.sh | 9a54b2fc470a483e55caa93cfc952cc6e14d2530ed3ffaf6a758c21e08837ff2 |
| route-b-owner.sh | 448184d592460f94a961a6c11c5184c651a755e9acf04ae4eec2f3e1927d0cce |
| members.tsv | 2afe7c99ea3f34030902ea700b02ee71d3232a950d9c82600fb293f910caca21 |
| startup.env | 5b6263be104d95aedd77b61dd9d6e54851887701e667afacefbd9e535f1d77ef |

## Diff and role review

Each of launch-common.parent_owned, watchdog.parent_owned and helper.rb_owned
changes exactly one case predicate, adding only these two literal variants:
`/data/local/tmp/asx/appspawn-x` and
`/data/local/tmp/asx/appspawn-x (deleted)`. The deleted variant retains exact
resident executable SHA and every other ownership check; it is not a basename
or arbitrary path fallback. This extends the earlier minimal nondeleted
proposal explicitly, rather than silently assuming it.

Every other guard instruction is byte-identical: birth before/after, all UID
fields, executable SHA, physical/private run.sh inode, private mount namespace,
child expected PPID and boot. Root parent acceptance remains read-only;
root UID child is rejected by rb_owned/child_owned. Wrong SHA, UID, birth,
namespace, inode, `/system/bin/appspawn-x` and foreign paths reject. Parent
private alias acceptance must not become permission to signal the U13 parent.

Entry changes only its watchdog/helper literal pins. Startup policy changes
only members.tsv SHA; expected-policy SHA closes. Members.tsv resolves 12
entries to exact new candidate or unchanged frozen base bytes. Startup remains
PENDING/disabled. The parent's captured original SHA `c453bce0...` exactly
matches the outer posttap source for PID5153; outer live GUARD_RC=0 corroborates
this read-only parent condition, not screenshot or child acceptance.

## Admission recommendation and remaining integration work

**Accept this exact alias correction for offline integration.** The outer must
derive a new placement plan from actual current 23 preimages, bind the new
watchdog/helper/entry/launch-common/members/policy bytes at all required aliases,
sign a fresh current-boot placement ticket and approve the new durable policy.
Do not reuse old 9436 program/member/policy bindings or its old boot ticket.
Preserve historical stop, consent and data; no blind restart is recommended.

This is not board authorization, successful spawning, UI/refresh/article,
autoboot or sealing approval. Actual current child exe was not retained in the
limited historical originals examined; the synthetic child role negatives are
not promoted to a current child measurement. No further historical sweep is
needed. The outer owns all 61b reads and writes.

5cd read-only handoff has been superseded by the outer's actual
`v1-seal-execution/5cd-restore-readonly` and `5cd-host-install`: missing original
HAP, U13 READY56, then installation yielding UID20011300/version1.0.0/code2.
Those are outer measurements, not our transport124 result. Never copy this
61b UID20011206 policy into the new 5cd recovery profile.

Raw test stdout/stderr, immutable archive and static receipt remain in this
worktree's `.artifacts/exe-alias-0cc5a5bd/`; SHA records are in
`frozen-alias-review-results.json`. Formal landing contains only this narrow
review, not any t0 candidate modification.
