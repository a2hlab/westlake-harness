# BACK51: exact Route-B article-back callback experiment

The click reached the article title icon. The status bar did not intercept it. The
actual `ea5d8b27...` BCP implements `onBackPressed(token, callback)` as return-void,
while `finishActivity` already schedules local destruction without an OH token.
This candidate forwards the non-null callback and catches RemoteException. It does
not additionally invoke finishActivity/nativeBackPressed. The original framework
callback posts finishAfterTransition on the activity handler; the original
ActionBar/Fragment checks and local DestroyActivityItem path remain unchanged.

**Experimental scope: non-root article only.** The patch forwards every non-null
callback; it does not implement the AOSP root/home moveTaskToBack policy. Root/home
navigation is neither accepted nor claimed. Actual entry into BACK51 and a return
screenshot are required; static findings do not prove this article's click calls
that method. No device calls have been made by this producer.

## Exact deliverable

- Original BCP SHA: `ea5d8b277f1207c928d289196876ad69505d73ab586815daccbda7080169523e`.
- Candidate SHA: `ae82e987b708441b3d6069ad04cb81e7846401a09fc9f34a84e854cc79783c33`.
- Candidate file: `$WORKSPACES/westlake-harness-t4/benchmark/2026-10-14-toutiao-manual-repair/back-callback-overlay/build-01/adapter-runtime-bcp-back51.jar`.
- Physical target: `/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/fw/adapter-runtime-bcp.jar`.
- Metadata: UID/GID20011300, mode644, appdat label. Fresh readback is mandatory.
- All170 BCP classes retained; normalized disassembly changes exactly one method.
- All9 boot jars and every DEX were inspected; framework has6 DEX/44888 classes.
  The adapter, Activity, and RequestFinishCallback each occur once in the actual BCP.
- Registry checker:8entries, **0checked**,0violations. This is not eight API validations.
  `evidence/unchanged-classes.json` and before/after method comparison provide the
  actual bytecode-preservation check. The target is not named by the local8-entry registry.

## Build and sources

Use existing locked tools, no network or Android/Unity rebuild:

```sh
python3 build.py --input "$MAIN/benchmark/2026-10-12-v1-seal-execution/exact-5cd-preview/runtime/fw/adapter-runtime-bcp.jar" \
  --out "$OUT" --tools "$WORKSPACES/westlake-inputs/tools" --java "$JAVA" --javac "$JAVAC"
```

`BackCallbackPatch.java` is the transformation source; `tools.lock.json` pins each
library. Four commands really ran rc0; raw stdout/stderr and invocation hashes are
in `build-01/`. JDK binary hashes are in `evidence/results.json`. Small sources,
locks, method evidence, results and command receipts belong in Git. The JAR,
complete disassembly and raw stderr stay in the persistent producer build directory
until outer archive; archive status is pending, not fabricated. The original full
child log is private and must not enter Git.

## Outer-only execution (5cd, <=30 minutes, restore reserve)

`window_remote.sh` is a narrow command body, not a new daemon/installer. The trusted
launch argv comes from the original `real-start-parent-bounded.sh`; its sed is
omitted because actual run.sh and WID29 already agree. Its old parent.log is not
overwritten. No board reboot, broad kill, data removal, JIT51 installation, or
runtime family update is included. Outer holds the exact board lock, authorizes
these pinned commands, and records real transport/stdout/stderr/time per command.

Set `PKG` to this landed package, `HDC` to the already verified transport, and a new
remote `AUDIT=/data/local/tmp/back51-<unique-id>`. `render_window.py` only generates
JSON and never calls HDC. Execute its `argv` using the existing outer recorder;
require host rc0 **and** `BACK51_REMOTE_RC=0` **and** `BACK51_VERIFIED`.

1. Render/run readonly preflight (already actual PASS in `back51-preflight-r2.*`):

```sh
python3 "$PKG/render_window.py" preflight --parent 5257 --birth 8214 \
 --child 17175 --child-birth 7265477 --audit "$AUDIT" --want old --hdc "$HDC" --out "$OUT/preflight.command.json"
```

2. Outer creates the fresh remote audit directory (mkdir must fail if existing),
   sends the exact candidate to `$AUDIT/candidate.jar`, and reads its complete SHA.
   Retain this staging and all command logs. Do not overwrite either old parent log.
3. Render/run `stop` with the same exact identities and `--want old`. Only TERM is
   sent to child17175 then parent5257. Unknown descendants, identity drift or a
  10-second TERM timeout refuse; no escalation or retry. Host5079 is never signalled.
4. Render/run `apply` with the same identities and `--want old`. It verifies no
   private-runtime consumer remains, backs up the original JAR to
   `$AUDIT/original.jar`, verifies backup, stages a new inode with exact metadata,
   rechecks target SHA+inode+metadata, and renames. It never truncates a mapped inode.
5. Render/run `start` with old stopped identities, `--want new` and the same audit
   directory. It immediately returns `BACK51_NEW_PARENT_LAUNCHED pid=N`.
6. Outer reads `/proc/N/stat`, captures actual birth B, and polls readonly `ready`
   for at most15seconds. **Do not reuse5257/8214 or infer birth from PID.** Inputs:

```sh
python3 "$PKG/render_window.py" ready --parent "$N" --birth "$B" \
 --audit "$AUDIT" --want new --hdc "$HDC" --out "$OUT/ready.command.json"
```

   Required: unchanged boot/host5079-birth8050/WID29/runSHA; exact spawner and private
   runtime; no child; private JAR candidate SHA; **fresh** audit parent.log contains
   `Listening on /dev/unix/socket/A2HSourcec91d26bfb4db4fd5a002`.
   A pending ready is not a repeated start. If parent exits or15seconds expires,
   inspect actual state and take the rollback branch below.
7. Render/run `spawn` with N/B, child0(default), `--want new`. This executes original
   nsenter JIT50 then original host_spawn/request once; its nonzero rc is preserved.
8. Outer binds actual new child/PID/birth, opens the same non-root article, captures
   click route, `[BACK51]`, lifecycle/window evidence and before/after images. Feed
   return needs human image acceptance. Do not click consent automatically.

For steps3/4/5 the renderer invocation is identical to step1 except action and
`--want`; use a fresh output command filename each time. The script has no lock
acquisition and must never run outside the outer authorized window.

## Failure and single-file rollback

- Before rename, original JAR still exactOLD: after proving the original family is
  gone, start **old** and spawn using the same launch chain. No unnecessary overwrite.
- After rename, exactNEW: capture actual candidate parent/child PID/birth; render
  `preflight`, then `stop` using `--want new`. If no child exists use child0/birth0;
  any unlisted child refuses. No blind reused PID signals.
- Render `rollback --want new` against stopped candidate identities and original
  audit directory. It validates exactOLD backup before any rename and restores
  original bytes/metadata via atomic temp+CAS+rename. Unknown current bytes refuse.
- Outer creates `$AUDIT/rollback` fresh; render `start --want old --audit
  "$AUDIT/rollback"` with stopped candidate identities, then bind new parent birth,
  readonly `ready --want old`, original `spawn --want old` and actual screen.
- If launch failed before a PID was recorded, inspect original `start` stdout and
  audit log; never guess or broad-kill. If there is no live consumer, use the known
  stopped identities for the guarded restore. Unknown state retains lock for outer.
- Keep original backup, staged partials and all logs. No recursive cleanup.

This description is not a signed deployment or a new seal. Original proof/selfcheck
expected hashes remain unchanged: a candidate mismatch is expected and must be
represented by the isolated experimental authorization, never waived as a PASS.
