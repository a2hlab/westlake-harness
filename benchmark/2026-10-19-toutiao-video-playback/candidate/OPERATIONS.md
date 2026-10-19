# OPERATIONS — Toutiao video P1 board window (61b, outer-run)

Status: **static handoff only.** Prepared on top of `e3dee08a77`. No new build, nothing deployed. The candidate bytes are unchanged (DSO `9f558aaf`). The outer runs this after P0 r2, holding the 61b lock. The window lasts at most 30 minutes.

## 1. Which run.sh the entry actually executes (after the P0 change too)

We checked the P0 r2 payload in `westlake-harness-icon-reentry` at `ab487f388e`: `candidate-payload-r2/payload`, the same files as r1 for this path.

```
init cfg /system/etc/init/01_westlake_u13_toutiao.cfg
  -> <state root>/boot-entry.sh -> start-parent.sh
  -> real-start-parent-bounded.sh   (sha f77f0f70, pinned by P0 startup.env)
       sed -i "s/export WL_PARENT_ID=[0-9]*/export WL_PARENT_ID=$WID/" "$RT/run.sh"
       source_app_namespace "$RT" 20011206 /system/bin/sh /data/local/tmp/asx/run.sh
RT=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d
```

The file actually executed is the **physical `$RT/run.sh`**. Inside the private namespace, `$RT` is bound at `/data/local/tmp/asx`, so outer reads through `/proc/<parent>/root/data/local/tmp/asx/run.sh` see the same file. P0 verifies this by matching the physical inode to the view inode.

**Because every start rewrites `WL_PARENT_ID` to the current host window id, the whole-file SHA is not stable.** `d3518cef` is simply the `WL_PARENT_ID=33` instance. Verify with the **normalized SHA**, i.e. after `sed 's/^export WL_PARENT_ID=[0-9]*$/export WL_PARENT_ID=N/'`:

| State | Normalized SHA256 |
|---|---|
| before (= d3518cef family) | `ea575abea86e8afd0aebbbb6cdc1900df3ff40c5d9c40ed290e8ac1b1f9c1cf4` |
| after (LD_PRELOAD + compat) | `db82cc159412026d274300a4f0a80ac8bb65cfe53c69d11690cfeeb664b95561` |

P0 `members.tsv` and `startup.env` pin only P0's own payload scripts, **not run.sh**. So this edit does not trip P0 gates, and P0's WID rewrite does not undo it, because it touches a different line.

The earlier `rollback-plan.json` and `selected-change.json` steps targeted `/data/local/tmp/asx/run.sh` with a whole-file `d3518cef` check. Those steps are **superseded**, and both files now carry `entry_facts`.

## 2. Inputs (expected SHA256)

| Item | Path | SHA256 |
|---|---|---|
| DSO to install | `deploy-inputs/libopensles_android_compat.so` → `$RT/libopensles_android_compat.so` | `9f558aaf1d48cedbc10e6774073d71177efb6d1e196fe528f0203505d1ee761f` |
| run.sh edit | the line ending `libwebview_bionic_shim.so` in `export LD_PRELOAD=` gets `:/data/local/tmp/asx/libopensles_android_compat.so` appended (idempotent sed; tested to give the same result for any WID) | normalized after `db82cc15…` |
| Reference whole files | `../static/selected-change/run.sh.d3518cef.orig`, `run.sh.candidate` (WID=33) | `d3518cef…`, `ea984942…` |
| Link-only `libOpenSLES.so` | build only, `out/` | `486936c0…`, **never deployed** |

## 3. Commands — [ops/video_p1_window.sh](ops/video_p1_window.sh)

The script prints by default. `EXECUTE=1` runs the commands. Raw stdout/stderr/rc per step go to `RAW` (default `$HOME/.local/share/westlake/toutiao-video-p1-window/<ts>/`, never edited). `PIDS` must come from outer's own route-b-owner identification: the parent's comm is `main`, so do not use `pidof` or bare `pgrep -f`.

| Step | Mode | Writes | Pass criteria (else STOP) |
|---|---|---|---|
| 1 | `PIDS='<parent> <child>' preflight` | none | normalized run.sh == `ea575abe…`; DSO absent; record boot, cfg SHA, entry grep, `ls -lZ` of the sibling preload DSO |
| 2 | `stage` | `/data/local/tmp/ttvideo-p1-stage/` only | staged DSO == `9f558aaf…`; staged `run.sh.after` normalized == `db82cc15…`; diff = the LD_PRELOAD line only |
| 3 | `apply` | `$RT/run.sh.ttvideo-p1.bak`, `$RT/libopensles_android_compat.so`, `$RT/run.sh` (tmp + mv, owner 20011206, modes 0644/0755) | DSO SHA and normalized after SHA as above |
| 4 | outer restart via the existing entry (start-parent path); **never `kill -9` appspawn-x** | — | parent re-created, feed reached |
| 5 | `PIDS='<new parent> <new child>' verify` + outer's capture tooling (baseline/delta stderr, full maps, two screenshots, no `hilog -r`) | none | parent maps: one compat DSO + one `/system/lib64/libOpenSLES.so`; feed screenshot ≈ baseline; after one video tap: no `SOURCE-NATIVE-LOAD-FAIL` for libttmplayer, libttmplayer in child maps, no `_setSupprotSampleRates` UnsatisfiedLinkError |
| R | `rollback` (on any failure or regression, or at 30 min) | restore `.bak`, `rm` DSO | normalized == `ea575abe…`; DSO absent; after restart, no compat in maps and feed ≈ baseline. Fallback without `.bak`: the printed reverse sed |

SELinux is Permissive on 61b. Step 1 records the sibling DSO label. Step 3 records the new file's label. A label mismatch is noted, not a gate.

## 4. Raw logs and evidence locations

| What | Location (private, unmodified) | Public copy |
|---|---|---|
| t2 build + gates | `$HOME/.local/share/westlake/toutiao-video-t2-build/20261019T180522/` | `logs-sanitized/` + `raw-log-manifest.txt` |
| t1 closure rerun | `$HOME/.local/share/westlake/toutiao-video-t1-raw/20261019T1806/` | `../static/evidence/*.sanitized.txt` + `t1-raw-log-manifest.txt` |
| P1 confirmation | `$HOME/.local/share/westlake/toutiao-resume-20261019/video-live-r1/tap-1/` | `../static/evidence/live-r1-tap1-binding.txt` |
| This window | `$HOME/.local/share/westlake/toutiao-video-p1-window/<ts>/` (created by the script) | to be added after review |

## 5. Scope

This window verifies **only** that libttmplayer now loads in namespace 0 and that the main window is unaffected. The next wall is recorded verbatim (expected candidates: P2 OpenSL callbacks, P3 surface, network/content). **No audio or video playback is claimed.** The t3 two-cycle playback protocol starts only after this window passes and the outer schedules it.
