# T38 status audit — read-only, 2026-10-21

**Disposition: r4c is landed and offline-reviewed; the white-screen repair has NOT passed device/manual acceptance. T38 remains stopped and its transaction derivation UNVALIDATED.** This audit executes no T38 code, tests, preparation, device/VM/REA command or runtime change. Historical observations below are not current board observations. All source paths, full SHA-256 values and last commits are in `sources.json`; all 12 read documents equal their committed bytes.

## Exact landed objects

| Object | Main commit / identity |
|---|---|
| T35 actual white-screen evidence | `06c26e2fcbd6b64c643ef099c6393537386b2e21` |
| Latest offline implementation, T36 r4c | `db5ebfa0c136d41d346f5054156b05244f90f2e3`, landed from author `fa2b91117f` |
| T37 independent review | `53e5c670aa72ef226bb0332608f59e265355eb88` |
| Migration review / legacy regression appendix | `0d251eae18db5a8d84a4cda75cf2a1a8a090cb24` |
| T38 disabled package, unvalidated transaction and safety-stop archive | `d2ff2fa9e9a23977b6f3dc34a95e76483b40426f`, landed from `eda748ac68` |

Latest watchdog SHA-256: `c73dadb3c0d6ba082c030d7c1096810129b5afec7e3aced4d896dce86e59f0e5`; common: `b806eb6c1bb390be357f2ac689024bf3947217611bf637850cfc65e7538681c9`. Earlier r4 `9072bbfb` and r4b are retained failures/intermediate revisions, not the accepted latest candidate. The T38 archive is not a deployment or repair acceptance commit.

## Evidence already recorded (not rerun)

- T35: three identical white frames after close/icon; old child/host gone, guardian and private parent alive, child retired and guardian awaiting reentry with no new spawn. Deployed r3's static focus path lacks parent rebinding. A stale live parent WID is **inferred**, not observed; live `WL_PARENT_ID` is missing. The earlier frozen-video allegation was withdrawn and is not a confirmed bug.
- T37 latest review: **18/18** safety cases, **165/165** assembly pins, five replayed production files equal packaged files; malformed UID and original run-inode epoch counterexamples resolved. Carrier disabled/unapproved; `manual_video=pending`, `deployment_authorized=false`.
- T38 appendix: four historical production-path probes cover bound-epoch-before-spawn, unbound fallback, no epoch grant to adopted r3, and existing-socket refusal. Disabled new-root package has **165/165** pins, manifest `6dfd6d6c0c1aa1a500da3b0288cf4ebf08b45288355570d31739e24339d28beb`. This is offline evidence only.
- Native peer receipt: **70 behavioral passes, one expected old common-hash failure**. Original results SHA `ebd6a6a5b4765cc5e3b519a0e3e04117e36db97e0bd799ba117b4c67ee262da9`; appendix records ten artifact hashes checked. This audit relies on the committed receipt index, not a new test execution.
- Historical fresh-01: old r3 still loaded, new r4c ROOT absent, boot `be4badc3-5a79-4fa8-8758-e6aacc0ca05f`. Fresh-02 later captured six W05 video-file hashes/metadata/labels, run.sh bytes/WID normalization, power/debug/mount before-images. Thus the slice-01 statement that those before-images were absent is superseded **for capture availability**, not for a completed recovery binding or recovery proof. The historical screenshot probe itself wrote its diagnostic screenshot file; do not describe the entire historical sampling as literally zero filesystem writes.

## Stops and exact knowledge limits

Primary available record: `host-reentry-window/SAFETY-STOP-20261021T1731.md`, SHA-256 `0d2c162ba085a7b9951c8c399f0074230e7c230b80054e667dfc6e8ef2ad317e`. It is the author's committed verbatim transcription of the notice, not an independently available raw classifier event.

| Record | Stopped action / result | Original stated reason and limit |
|---|---|---|
| T35 white-screen README | Follow-up reporting environment-derived content stopped; no retry. Earlier pipeline failed because board `tr` was absent (`env_rc=1`). | Tool failure and classifier stop are separate. No original classifier notice is present in this T35 source: **original refusal reason unknown**. Do not infer a reason from the environment-read context. |
| T38 first stop, about 17:31 | Response after donor-test diagnosis output withheld. Last completed work ran two donor cases in root-only variant A and displayed fixture lines. | Notice: “Your response above was stopped by a safety classifier — this is not a tool or API error.” It also forbids reproducing the withheld content, even reworded. **Exact withheld operation and specific classification reason unknown**, explicitly so in the record. |
| T38 second stop | Write of disabled `window/t38_window.py` returned `Interrupted`; subsequent read-only check found file absent and worktree clean. | Same classifier notice, with warning that Interrupted calls might have partly/completely executed. The later file check resolves this instance as absent. **Specific classification reason unknown**. No retry, rewrite or handoff to another model. |
| Ordinary startup admission gate | Disabled package preparation refused `ValueError: startup authority`. | Expected product gate, not a classifier refusal and not authority to sign. |
| Transaction validation | Donor passes 22/22; both root-only and full derivation fail the same 6/22. | Test failure, not classifier reason. One fixture/path mismatch established; other five causes not established. Raw unittest logs were never persisted; LOGS.md is a labelled transcription. No rerun here. |

The first-stop record's “independent” orchestration suggestion was subsequently stopped by the second refusal. It is **not** a remaining permitted task. This report does not recreate either withheld response or propose a substitute implementation.

## Exact remaining acceptance gaps

1. No final armed successor's complete plan/session/source/member/startup/entry/recovery binding. Slice-01 specifically found the claimed CHAIN join absent; a complete equivalent binding, not a filename, was the issue.
2. No executed migration/recovery evidence binding actual boot, parent and epoch/socket/run inode. First spawn can succeed with an unbound epoch; first launch/feed alone cannot prove host-recreation recovery.
3. Fresh-02 supplies historical video/settings before-images, but no completed video-preserving recovery proof. Old pre-video W05 rollback is not evidence for preserving the fixed video stack.
4. The v2 start-parent leaf/authority changes remain UNVALIDATED after donor failures; do not promote README slice-01 claims or the correct current package leaf into a validated execution gate.
5. Manual two-cycle close/icon/video acceptance remains pending: changing content frames, pause/resume and reentry, plus actual host-switch events where claimed. Progress bar, alive process or READY is insufficient. Historical sound evidence remains accepted; no new sound question.

## Independent work outside the stopped actions

Permitted current read-only work is documentary: preserve and hash existing committed receipts; reconcile historical versions and superseded observations; index existing source/assembly/acceptance evidence; identify missing raw refusal/log records and accept them if later supplied. Existing receipts can be reviewed without executing their programs. These tasks cannot establish current device state, recover missing live WID, validate the stopped transaction or prove a repaired UI.

No further technical execution is authorized by this audit. Do not rerun donor diagnosis, recreate the interrupted orchestration, run T38 preparation/tests, switch tools/models, or pursue an alternative route around a refusal. Any future task requires its own permitted scope; a new scope does not erase the recorded stops.

## Handoff

ACK token: **T38-STATUS-AUDIT-READY**. A local-worktree blackboard entry is included in `landing-paths.txt`. The shared main-tree blackboard is outside this session's writable roots; it was not modified or accessed via a replacement messaging channel. Outer can land/relay the local ACK. No commit or push was attempted.
