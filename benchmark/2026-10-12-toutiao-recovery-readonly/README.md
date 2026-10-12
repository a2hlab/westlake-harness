# Toutiao SIGSEGV followed by no recovery: five-minute read-only findings

## Evening outer follow-up: deployment objects, not archive assumptions

The later outer collections `followup-1906/`, `followup-1910/` and
`followup-1913/` contain 52 read-only command receipts. Each ordinary receipt
retains an explicit remote exit marker; HDC's host exit alone is not success.
The first NUL-containing environment read was filtered on the host and produced
no retained fields; it is not evidence of an empty parent environment. The
subsequent `strings` observation explicitly proves `WL_PARENT_ID=33` and
`ASX_RUNTIME_OWNER_UID=20011206` for parent9529.

`preimages-1915/preimages.json` records 24 proposed/control targets: 11 existing
files were received byte-for-byte and checked against their live SHA, and 13
are absent with exact-target or traversable-ancestor evidence. It records mode,
UID/GID and label for existing files. These are preparation evidence, not a
write ticket; every affected target must be rechecked immediately before apply.

The live JIT script has SHA `aa1234d2` and device/inode `66352:437034` through
both the public runtime and parent9529's namespace. The native namespace helper,
host_spawn and effective request match the integration candidates. Conversely,
the two old watchdog aliases differ (`9ae770bd` versus `7f4fc311`); the second
alias has no sibling owner helper. Do not restore both aliases from one assumed
preimage.

Neither `tr` nor `toybox tr` exists on this board. `strings` is available and
was exercised against the real parent environment. `snapshot_display` is
`1af5524c`, while the PNG-only classifier is `808f58a1`; a filename extension or
an approval boolean is not proof that their image formats are compatible.
No app data, old stop, deployment, runtime, service, consent or reboot was
changed by these collections. API atlas verification is unrelated to board UI
acceptance.

## Confirmed chain — current boot, not the old Bug7 attribution

Input root: `$WORKSPACES/westlake-harness-wiki/benchmark/2026-10-10-demo-seal-61b/seal-run-20261012T094950/acceptance-evidence/`.
Boot is **ac87bbbe-5f9b-496f-8002-43279e072042**. No device operation,
source/plan/evidence change, build, consent input or recovery attempt was made
by this lane. Only this bms summary was written.

1. The user personally accepted privacy. Outer/t0 report that screenshot61
   shows the consent-free real feed. At10:07:10.100, PID9548/TID32446
   (`platform-defaul`) has its own **DfxSignalHandler signo11**, not handled
   MUSL signal4. Original `63-refresh-hilog.txt:13284–13285` proves this signal;
   the process table then lacks article.news. We do not diagnose the crash PC.
2. `72-receipt-env-original.txt` says ARMED, guardian5936 and keeper3956 in
   this boot. **ARMED is a startup receipt, not current supervisor health.**
   `81-guardian-live-readonly.txt` explicitly says `GUARDIAN_PROC_ABSENT` in
   this boot; `78-owner-presence.txt` says the supervisor lock owner is absent.
3. `75-stop-presence.txt` proves a zero-byte **selfheal48/stop EXISTS**, with
   mtime09:58. `74-state-original.txt` is **CLEANUP_BLOCKED**. The current tail
   of `76-events-log-original.txt:576–578` is:
   `250 CLEANED ...`, `254 START seq=118 child=9548 parent=9529 mode=fresh`,
   `454 STOPPED`. The matching child/parent joins this tail to the current
   receipt/process evidence; earlier rows span other boots and are not this run.
   Stop mtime is before the10:07 SIGSEGV. Nothing here proves that SIGSEGV
   itself stopped the watchdog; supervision was already gone.
4. t0's one normal icon reentry waited97.58s and still had no new article.news
   or route watchdog (`70-one-normal-reentry-evidence.json`; `69` process file).
   Keeper3956, imehost5903, Route B parent9529 and U13 parent4792 remain.
   **onscreen_keeper keeps the screen usable; it is not the child supervisor.**
   The surviving host/parent cannot be counted as automatic child recovery.

Therefore the supported immediate explanation is **the Route B watchdog is
not running, its stop latch is present and its state is blocked**; a feed
already launched can remain alive independently until it later crashes.
Desktop reentry has not recreated an Android child. This is a recovery-control
failure observation, not a new runtime regression or a proven crash root.
Refresh/article acceptance remains incomplete; no signature is supplied.

## Actual deployed script, and why blind restart is unsafe

`79-deployed-watchdog-sha.txt` and the received `79-deployed-watchdog.sh`
both bind SHA **9ae770bd03e9846b9868b895ddc84f894c63811f6e30c1d1a61ce581172ab2ad**.
Placement source `toutiao-placement/data/scripts/watchdog.sh` has SHA
`e78d3691c3bae7ea8916f4cd6aef2587da1e60aa2471b1a853af86c07b3d6573`.
A text comparison finds only line68 `chown` UID/GID changed
20010053 -> **20011206**, matching the receipt's reconciled host UID. Do not
mistake the expected mutable UID field for an otherwise changed watchdog.
`evidence.json` records original references and verified hashes; no original
file is copied over or modified.

Actual deployed script lines:

- **12 / 88 / 113 / 158:** stop refuses initial start and terminates monitoring.
- **89 / 160:** failed `clean_all` writes CLEANUP_BLOCKED, touches stop and
  breaks; **168–169:** STOPPED, live app may remain for the operator. This
  matches the observed latch/state, but does not identify which cleanup check
  failed or whether the state predates this boot.
- **53–69 / 87:** starts `mode=fresh`; profile preparation moves app-data/data/
  webview-t-data and may delete its previous disposable profile. Re-running
  this script is **not data-preserving recovery** merely because it saves one
  earlier copy.
- **145:** `privacy` classification directly sends a consent tap. This is
  incompatible with the user-personal-consent rule.
- **150–154:** READY requires feed and `consented=1`; otherwise a180s bootstrap
  timeout remains possible, even when the user, not the watchdog, accepted.

Placement overlay source `data/scripts/westlake-u13-toutiao-overlay.sh:58–60`
refuses another same-boot receipt / existing Route B socket; `:86–90` launches
the guardian once and records ARMED. This is a **source-side explanation** of
why an existing host/icon is not a watchdog re-arm mechanism; its current
deployed overlay bytes were not received in this evidence set. Do not manually
rerun the overlay to test it.

## History is context, not the current cause

Canonical blackboard25550–25625 records the old Bug7 (CAPTURE_SCREEN missing ->
snapshot fails -> label unknown -> bootstrap_timeout), outer03:38 stop request,
03:43 guardian exit/CLEANUP_BLOCKED and later human-consented feed evidence.
That belongs to the old b43cd5fd boot and guardian5345, **not** today's
ac87bbbe/guardian5936/child9548. It demonstrates that stop can leave a live feed
without supervision; it does not establish today's snapshot permission failure.
Historical B feed-only evidence is not today's successful refresh/article.

## Unknowns and the smallest next step

- Exact reason guardian5936 exited / stop was created: its actor and failed
  cleanup branch are not proven. `73-watchdog-boot-log-original.txt` only shows
  missing `fresh48/stop` path, not CAPTURE_SCREEN or bootstrap_timeout.
- The old cumulative state/event files lack per-row boot IDs. Correlate the
  current seq118, instance/uptime and same-boot receipt; do not borrow old READY,
  CONSENT or STOPPED rows. No same-boot snapshot.log/ui.log/instance118 evidence
  yet proves today's bootstrap label/permission or reason field.
- Native SIGSEGV root, existing parent ownership/cleanup details and a safe
  data-preserving re-arm provider remain unproven.

**Minimum next step:** outer/t0 may first supply only already-existing
seq118 `instance`, `ui.log`, `snapshot.log` and the relevant same-boot child/
parent log tail (with hashes and boot/PID context), plus the deployed overlay
pin if needed. This lane can read those local receipts, not contact the board.
Outer then decides a separately reviewed recovery path that never auto-consents,
never rotates existing user data and respects Route B ownership.

**Not recommended or authorized:** clear stop, restart watchdog, rerun full
seal/overlay, kill the main spawner, mutate configuration, reboot, erase data,
or automatically press consent. Keep current driver/run and original failure
evidence. Do not expand this task into SIGSEGV repair or sign acceptance.

## 14:06 read-only integration follow-up

The board remains on boot `ac87bbbe-5f9b-496f-8002-43279e072042` before and after
nine read-only captures. The captured process table has U13 parent 4792 and Route B
parent 9529, but no `com.ss.android.article.news` child. The supervisor lock directory
is absent; stop remains at its 09:58 timestamp and state remains `CLEANUP_BLOCKED`.
This is process/control evidence, not a screenshot or successful UI observation.

The actual deployed owner helper is now captured: SHA
`eaba972bbfb5de827341df3bd40e85b99d5ba9cd355f0c1aeddaa34186147abd`.
Comparing with candidate helper `80a263d9` shows only one comment-wording difference;
executable lines match. This resolves the missing live-helper-bytes gap without
claiming current process identity guards have passed. Actual `start-parent.sh` and
`spawn.sh` are also captured for integration review. The former updates the host
window ID in runtime `run.sh` and starts the namespace parent; the latter calls
`host_spawn`. Candidate tests replacing these entrypoints cannot prove their actual
startup behavior, JIT readiness or screenshot/classifier compatibility.

[The raw capture index](followup-1406/index.json) pins each stdout file and command.
No app start/stop, touch, screenshot, permission change, data change, reboot, runtime
build or signature occurred. The original seal driver has separately exited with
`acceptance exit=124`; old UI observations are not a new seal authorization.
