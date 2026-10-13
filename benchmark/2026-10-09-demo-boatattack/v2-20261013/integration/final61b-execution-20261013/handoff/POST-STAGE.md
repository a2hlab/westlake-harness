# Original-tool post-stage command card (61b)

Outer owns the canonical lock and all device execution. Active window:00:06:16→00:26:16 execution cutoff;00:36:16 recovery cutoff. All commands below use main frozen tools. Do not run snapshot/boot until original provider receipt is complete. Keep each actual argv/rc/time plus stdout/stderr through root's existing process recorder. No new driver is needed.

```sh
cd "$WORKSPACES/westlake-harness"
B=benchmark/2026-10-09-demo-boatattack/v2-20261013
P="$B/integration/final-v2-f28"
RUN="$WORKSPACES/westlake-harness/$B/outer/final61b-approved-execution"
STAGE="$RUN/stage"
SERIAL=61b0657200000000000000000324012c
HDC=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
SNAP="$B/outer/r5-preflight/candidate-snapshot.r4.json"
COMP="$RUN/boat/composed/composition.json"
export WORKSPACES B P RUN STAGE SERIAL HDC SNAP COMP
```

## Before the single candidate boot

Require `stage/boat/receipt.json`:executor_rc0/statusPLACED_PENDING_AUTHORIZED_SINGLE_BOOT, exact11 placed records, transaction planSHA/serial/boot and preserved-verified496. No source-directory targets are added to snapshot. The original62 inventory covers every actual7bind, including runtime in U13seq13 and libandroid.

```sh
python3 scripts/lab/board_state_snapshot.py "$SERIAL" --hdc "$HDC" \
 --plan "$SNAP" --out "$STAGE/preboot-snapshot"
python3 scripts/lab/sepolicy_gate.py \
 --policy "$WORKSPACES/westlake-inputs/sepolicy/oh-6.1.0.31/policy" \
 --recipe knowledge/gates/selinux-label-recipe.json --evidence "$STAGE/preboot-policy.json"
```

Use the same native environment/PATH as the successful5cd policy invocation (sesearch must resolve); do not replace a missing command with PASS. Require snapshot complete,boot_stable,errors[] and unchanged9f5af7c8-d359-4c25-99c6-63206b50cf0a; policy rc0/failures[]. Record candidate-boot-intent once, containing serial/origin/window-authorization pin/ordinal1, before the following single command:

```sh
"$HDC" -t "$SERIAL" target boot
```

Do not retry `target boot`. Transport disconnect rc1 was allowed by the original hook, but is not successful boot evidence. Reuse the original polling body from `integration/runtime-successor-r6/window_hooks.py:61` with61b serial and this stage auth: poll at5sec, maximum240sec and no later than execution cutoff. The actual readonly commands are:

```sh
"$HDC" -t "$SERIAL" shell 'cat /proc/sys/kernel/random/boot_id'
"$HDC" -t "$SERIAL" shell 'cat /data/westlake-demo/u13/receipt.env; param get sys.westlake.demo.u13.ready; getenforce'
# Set NEW_BOOT only from the successful actual boot read, never from the origin or a guessed UUID.
: "${NEW_BOOT:?actual changed boot required}"
"$HDC" -t "$SERIAL" shell "cat /data/westlake-demo/u13/boat-v2-20261013-r4/boat-$NEW_BOOT.receipt"
```

Keep explicit remote rc wrapping from the existing recorder. Per-line strip as in the acceptedr4/r6 hook. Require changedboot, receipt `state=READY`, `layers=56`, matchingboot, globalready`true`, `Permissive`; Boat `state=BOUND`, `layers=7`, matchingboot. No parent/child launch untilBOUND. Save actual candidate-boot-result; no UI PASS inferred.

## Original desktop host before954

This is the exact BMS desktop_launch/capture API sequence used by5cd `postboot-host` and `finish_window.py`; only serial/boot/output are parameters. Run this once before initial954; repeat after controls with a new HOST_OUT for final954. It does not click consent.

```sh
export NEW_BOOT
HOST_OUT="$STAGE/postboot-host"; export HOST_OUT
python3 - <<'PY'
import hashlib,importlib.util,json,os,sys,time
from pathlib import Path
root=Path(os.environ['WORKSPACES'])/'westlake-harness';out=Path(os.environ['HOST_OUT']);serial=os.environ['SERIAL'];boot=os.environ['NEW_BOOT'];stage=Path(os.environ['STAGE'])
a=json.loads((stage/'window-authorization.json').read_text());assert a['serial']==serial and time.time()<a['recovery_deadline_epoch']
p=root/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='f41efa6ae2450adadda1f02c3c09335b74479c7d025872bbf95b3c8a444b177c'
s=importlib.util.spec_from_file_location('original_bms',p);b=importlib.util.module_from_spec(s);sys.modules[s.name]=b;s.loader.exec_module(b)
out.mkdir(parents=True,exist_ok=False)
board=b.Board(serial,os.environ['HDC'],'bash '+str(root/'scripts/lab/board_note.sh'),'outer(codex)',out/'commands');board.ready();assert board.boot.strip()==boot
record=dict(serial=serial,boot_id=boot,package='org.westlake.imehost',consent_interaction=False)
remote='/data/local/tmp/final61b-host-'+str(time.time_ns());board.shell('test ! -e '+remote+' && mkdir '+remote)
b.desktop_launch(board,{'package':'org.westlake.imehost','launch_activity':'EntryAbility'},remote,out,record)
record['capture']=b.capture(board,remote+'/host.jpeg',out/'host.jpeg');b.save(out/'record.json',record)
PY
COMP_SHA=$(shasum -a 256 "$COMP" | cut -d ' ' -f 1)
python3 "$P/selfcheck/selfcheck_entry.py" \
 --composition "$COMP" --composition-sha256 "$COMP_SHA" --serial "$SERIAL" \
 --boot-id "$NEW_BOOT" --hdc "$HDC" --out "$STAGE/postboot-selfcheck954.json"
```

Use original preboot composition directly. The accepted selfcheck entry derives only the original single WL_PARENT_ID field from independent sameboot WMS/host observations and saves parameter-observation.json. Require rc0/PASS954, original nonfile gates and matching boot bookends. Do not hardcode oldWID or copy5cd parameters. The resulting actual parameter pin can feed original bind_request/compile_selfcheck for final running composition.

## Original controls, then foreground and final954

```sh
python3 scripts/lab/activation_smoke.py \
 --spec "$B/outer/r6-experiment-main/candidate-smoke.json" \
 --serial "$SERIAL" --lane 'outer(codex)' --hdc "$HDC" \
 --lock-cmd "bash $WORKSPACES/westlake-harness/scripts/lab/board_note.sh" \
 --out "$STAGE/final-controls"
```

Expected runtime9745004d10ce/boot_fpee927db88a67; exact candidate child-view f28/ADC/8ab/633. Require original smoke-result passed, actual facts and human t20 review. Do not blindly overwrite fingerprints if a mismatch appears. After smoke, repeat the desktop snippet with `HOST_OUT="$STAGE/final-host"`, then repeat the954 command with `--out "$STAGE/final-selfcheck954.json"`. The original smoke can hide imehost; omitting foreground restore previously caused a real nonfile failure. Save human image verdict and actual unlock receipt only after all gates. Failure keeps transaction/raw evidence and invokes the already-authorized original rollback path; no second candidate boot.
