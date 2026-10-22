# Owned host lifecycle entry gap — static evidence

The earlier reentry-donor explanation must not be applied to current 5cd. The captured watchdog is the original **2b635ef1ea9e00546e1306b0fe6872a415a8c7d5653e19f9fb42fca04386db4a**, with owner helper **6bce7c3c8f84ad1047313c5dd76bcb084637d9095b9163dc710c88aaee12fe4c**. This report separates three proven observations: a non-reentrant per-boot entry, an absent guardian, and working host lifecycle callbacks. It does not diagnose third-party exits or claim all white screens share this cause.

## Evidence and exact connection

Local source prefix below is `$MAIN_WORKTREE/benchmark/2026-10-12-v1-seal-execution/seal-final-20261013/appendix-5cd/sealed-realization/package/payload/`. `$MAIN_WORKTREE` is the sibling westlake-harness directory. These six deployed-source copies exist on disk but are absent from recorded main commit7d6a24c9ed8fc42a78e20346687a8c34a7f54aae. Their SHA256 and computed Git blob IDs identify bytes, not committed provenance. Four other source/evidence pins match that commit. All hashes, lookup failures, raw paths and sizes are in `results.json`. Six deployment-to-source bindings were compared locally; no device command was issued.

| Observation | Exact evidence | Interpretation |
|---|---|---|
| Boot service | T45 `raw/02-dirs/cfg_01_westlake_u13_toutiao.stdout:8–29`; source `recovery.cfg:7–28`, SHA19d0201b… | The condition `sys.westlake.demo.u13.ready=true` starts `westlake-u13-toutiao-overlay`; service has `once:1`. No desktop event is wired into this cfg. |
| Same-boot reentry refusal | T45 `raw/03-entry/bootentry.stdout:15–16`; source `boot-entry.sh:14–15`, SHA7fbfdf05… | Existing `boots/$AUTH_BOOT` is refused with `BOOT_ATTEMPT_ALREADY_EXISTS`. Even another service invocation is not a reusable same-boot entry. This conclusion does not require assuming how often init reevaluates the condition. |
| One execution chain | `config-common.sh:21`; `boot-entry.sh:27`; `entry.sh:7,17,22,30` | State binds to the boot. Entry waits for host foreground, rejects existing lock/stop/socket, then execs watchdog. There is no outer restart loop after watchdog exits. |
| Guardian termination/absence | T45 `raw/04-state/cat_events.log.stdout:25`, `cat_state.stdout:1`; accepted `benchmark/2026-10-22-toutiao-existing-bridge-evidence/t45-a-guardian-absence.json` | State is OWNER_REFUSED. T45-A reports `/proc/3978/stat` absent and explicitly stops before reading fd2. The exact disappearance time/status is not available. `watchdog.sh:297` returns2 on the recorded refusal branch; main is called at333. |
| Ordinary host callbacks | T44 `raw/06-click1/obs.stdout:13`, `raw/07-click2/obs.stdout:13` | onCreate/seq1 and onNewWant/seq2 share instance ca09a4f8…; manual origin remains unverified and eligibility false. These callbacks worked. |
| Host has no restart call | `benchmark/2026-10-20-toutiao-launcher-page/sources/baseline/EntryAbility.js:18–34`; T39 candidate `EntryAbility.js:59–78,99–115` | Baseline records lifecycle and loads Index; observer additionally records callbacks. Neither connects to a service, restarts guardian or sends a bridge launch request. |

The bound state directory is `/data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/boots/8b64b087-b46f-4704-922f-d1ef36832472/`. Current root binding is proven by T45 configuration; it is not the61b donor default. With guardian3978 absent, another ordinary desktop click can still show the host, but this chain has no surviving callback consumer/restart caller that would issue a new bridge request. This is a missing restart connection, not a failed host callback or proof that passive JSON caused the white screen. A still-existing parent/socket is not itself evidence of a new request.

T44/T45 already show child22549, later child27648, classifier observations and recovery. No globally child-free interval, exact click-to-birth causality, third-party crash cause, or visual success is inferred. READY is a classifier state. The raw btime/uptime alignment has clock uncertainty. T45 outer corrections remain authoritative.

## One bounded next-step proposal

The minimum modification target is **owned service lifecycle admission at the boot-entry/entry boundary**, not the identity helper. A future separately reviewed change could connect the normal host lifecycle to a narrowly authenticated owned service request, reusing strict launch checks. Normal callbacks are reusable application events, but this deployment has no proven host-UID service endpoint; callbacks and observer files do not confer authority.

Before implementation or execution, establish the supported service interface/caller permissions, fresh residual parent/socket/child and attempt ownership, and a reviewed recovery rule. An identity refusal or unknown state must remain refused pending explicit reconciliation; repeated requests and an existing child must not create duplicate starts or overwrite historical attempts. Do not merely switch init restart flags, clear locks/stops, reuse the old boot directory, or start the historical T12/T13 tools. Their bounded outer-authorized attempts are not a deployed normal lifecycle service. No T38 orchestration or tests are proposed.

## Limits and delivery

Detailed rb_deny stderr destination, exact identity failure subtype, third-party exit cause and a usable ordinary-app service interface remain unknown. Six exact bindings do not prove whole-package equivalence; the earlier startup.env comparison differed. Original private logs are unchanged and not copied. `$HOME` aliases are sanitized; local source copies use `$MAIN_WORKTREE`, and tracked source paths are repository-relative. Two files only; device/runtime/build/deploy actions0; `author_commit=null`. No deployment or implementation is included.

The first local verification returned rc1 with `AssertionError` at line6: it incorrectly required all ten repository-side pins to exist in HEAD. Six are local disk copies. The failure and exact assertion are retained in `results.json.verification_history`; no first-attempt PASS is claimed. Corrected verification separately checks local bytes/deployment bindings and the four actual committed blobs.

## Preferred tracked sources (final correction)

The original local-copy paths and absent-HEAD lookup failures above remain historical evidence. Use these exact tracked, byte-identical copies for mainline source references; line numbers are unchanged because entire bytes match. `git ls-files`, the fixed main commit blob and SHA256 were all checked. No old package was added to Git.

- `recovery.cfg`: `benchmark/2026-10-12-v1-seal-assembly/restore-v6/package-composed-disabled/payload/recovery.cfg`; exact SHA/blob and cited lines in `results.json`.
- `config-common.sh`: `benchmark/2026-10-12-v1-seal-assembly/restore-v5/package-r3-disabled/payload/config-common.sh`; exact SHA/blob and cited lines in `results.json`.
- `boot-entry.sh`: `benchmark/2026-10-12-recovery-executor/payload/boot-entry.sh`; exact SHA/blob and cited lines in `results.json`.
- `entry.sh`: `benchmark/2026-10-12-snapshot-path/candidate/entry.sh`; exact SHA/blob and cited lines in `results.json`.
- `watchdog.sh`: `benchmark/2026-10-12-snapshot-path/candidate/watchdog.sh`; exact SHA/blob and cited lines in `results.json`.
- `route-b-owner.sh`: `benchmark/2026-10-12-child-readiness/r3-lowfork-audit/candidate/route-b-owner.sh`; exact SHA/blob and cited lines in `results.json`.

Any unresolved tracked source is explicitly listed as unknown in results. The deployed startup.env source remains unbound; this is not whole-package equivalence.
