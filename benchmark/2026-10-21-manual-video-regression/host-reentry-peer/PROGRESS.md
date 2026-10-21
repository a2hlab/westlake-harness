# T37 progress / first slice

2026-10-21 16:48 CST. Independent lane at analysis/t37-host-peer-20261021; base 47bdf7c706.

26 production-function observations reproduced: r3 12 (3 counterexamples), T36 snapshot 14 (7 adverse observations). Candidate watchdog b6593237d03eb2173b9f238167df1977b5029990ad69ed6b22b9a58595f081ff; common b806eb6c1bb390be357f2ac689024bf3947217611bf637850cfc65e7538681c9. Verdict request_changes, partially_verified. Python suite 3/3, dedicated Rust target 1/1. Lifecycle strict: 3/3 scenarios and explicit boundaries pass; fresh explain 3/3. These verify review evidence, not candidate safety. Full candidate payload not available at latest observation.

Blocking findings: unknown old-parent birth treated as exit; malformed/absent proc and fd data treated as empty; socket listener state and pathname ownership not proven; read-only parent_owned is insufficient signal authority; baseline owned enumeration errors remain. See README and exact replay receipts.

No device/REA/environment retry. Dynamic-video manual matrix remains pending; historical sound retained. Screenshot/alive counts unknown (no device run). Only contract paths written. Root README/DIGEST additions are proposed through documentation.json for outer landing, not directly changed.

Canonical blackboard is not present in this worktree and is outside the card's allowed paths. ACK.md is a handoff artifact for outer posting, not a claim that a canonical ACK was sent.

Commit handoff: git add rc128, index.lock Operation not permitted. No retry or bypass; no commit SHA and no push. Outer must commit/land the exact listing.

16:50 CST addendum: 28 total observations. Added actual r4 newhost-loop two-edge control (one epoch/one spawn), and owned enumeration rc7 counterexample reaching TERM/unlink/start/spawn. Candidate replay 02: 16/16 observations reproduced, 8 adverse and 8 control. Initial replay 01 retained.

Adaptive replay: latest watchdog 9072bbfb032afc217ed01e369f3ce859b2c63e310e42815158780973f71391bc, common b806eb6c unchanged; snapshot candidate-02, candidate-replay-03 16/16 reproduced (8 adverse, 8 controls). Added WID guard/log reasons do not resolve the blockers. Latest request_changes.

Continuation: direct channel attempts stopped on user's instruction; outer relays TO-cc-video.md. Parameterized new-SHA runner and exact entry pin audit implemented. Latest source 3aba9d8e: previous 16 safety cases pass; 2 new counterexamples (malformed UID classified empty, original run inode absent from recorded epoch). See latest-review.json. No author files changed, no old SHA re-executed in this continuation; archived tests now check receipts and hashes.

Latest adaptive replay: r4c c73dadb3c0d6ba082c030d7c1096810129b5afec7e3aced4d896dce86e59f0e5 18/18 safety assertions pass, 0 harness errors. Real rc_record_bootstrap_epoch now generates the fixture epoch schema, retaining new runid. Full payload/entry pins still unavailable; candidate not accepted. See latest-review.json.

Final handoff: author fa2b91117fd49ec0119986b6c3174d0857d10229 committed the reviewed r4c source/package. Recorded exact committed-byte comparison in author-observation-final.json. Strict lifecycle-05 passed (quality 1.0); source safety 18/18, assembly 165/165, runner/evidence tests 10/10. Legacy full-suite gap explicitly preserved; no device acceptance claimed. No commit or bus retry.
