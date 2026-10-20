# T34 remote integration review

The diverged histories do not require rebasing or manually combining the demonstration work. Git 2.55.0 merged the exact local master `371fae4081378f03fd7c1810ad994de9fa116237` and fetched origin/master `6c27dd416ce863a670772eb295a93b2b58054465` mechanically with rc0, yielding tree `3359ff2aae3eebe326d8c22e166650597b946268`. Merge base is `e87628143a2738508b56a2595ab155b8da588fb9`.

There are 2051 local-only and 21 remote-only commits. The remote range contains 10 merge commits and 11 content commits, changing 36 paths. The local changed-path set and remote changed-path set have zero overlap. The merge changes exactly those 36 paths relative to local master; each resulting remote path has exactly the remote content/mode. All other local files, including the Toutiao candidate/deployment/demo evidence, remain unchanged in the proposed tree.

Remote work covers generic contract/gap inference, activity lifecycle/recreation, popup/dialog placement, keyboard/focus, notification/alarm calibration, flow prediction and their probes/tests. No file conflict requires manual resolution. Generic calibration predictions and old build103–112 receipts remain historical, not new video proof or public API freezes. The new explicit probe input actions are not run by integration review.

Use an ordinary two-parent merge after the outer operator verifies unchanged refs and a clean index/worktree. Preserve both histories; do not rebase the 2051 local commits or force-push. If refs move, rerun merge-tree first. No broad test run is needed for this conflict report; the four changed host test files are listed in results.json if the integration gate requires targeted validation. No device command, checkout/reset, actual merge, main-tree edit or push was performed. The only shared Git write was merge-tree's unreachable tree object.

Raw argv/rc/stdout/stderr receipts are adjacent. This review stops at integration readiness; runtime behavior is not retested.

Ref refresh: while the report was being written, outer advanced master by one scheduling/documentation commit to `9e7c3a75359fb71402991b063c49d1f6b607a8f5`. A second fixed-ref merge-tree also returns rc0 with no conflicts, tree `f64c4e1c8984f8f25cecc9f30b85370ccfcccd82`. The original result and receipt remain unchanged; use the refreshed pair for integration if refs still match.
