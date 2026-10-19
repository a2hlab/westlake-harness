# OPERATIONS — Toutiao video P1 execution card (61b, outer-run)

**Status: card only, nothing executable.** Revision r2 closes the four blockers in t4 `video-1919-review-final/ACK.md` (sha `d953c270…`). The candidate is not rebuilt: DSO `9f558aaf`, templates `d3518cef`/`ea984942`. The unguarded `ops/video_p1_window.sh` from `d6098ca03b` is **deleted**; no `EXECUTE=1` path remains. The outer composes every write from its existing Board/receipt primitives. This card only pins the targets, the expected bytes, the lifecycle and the pass/stop rules.

| Review blocker | Closed by |
|---|---|
| 1 real target, preimage, metadata | §1 |
| 2 fresh-parent lifecycle (apply and rollback) | §4, §6 |
| 3 dynamic WID, exact derivation | §2 |
| 4 exact object-specific load result | §5 |

## 1. Physical targets and preimages

`RT=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d` is r2 `config-common.sh` `AUTH_RUNTIME`. r2 `real-start-parent-bounded.sh` (`f77f0f70`) passes `$RT` to `source_app_namespace`, which binds it at `/data/local/tmp/asx` inside the private namespace. **Never write the global-shell `/data/local/tmp/asx`.** It is not proven to be this object.

| Target (physical) | Preimage | Postimage | Metadata |
|---|---|---|---|
| `$RT/run.sh` | exact bytes `before(W_live)` (§2) | exact bytes `after(W_live)` | owner `20011206:20011206`, mode `0755`; SELinux label = the value read in preflight, bound into the same guard |
| `$RT/libopensles_android_compat.so` | **absent** (`test ! -e`, `test ! -L`) | sha `9f558aaf1d48cedbc10e6774073d71177efb6d1e196fe528f0203505d1ee761f` | owner `20011206:20011206`, mode `0644`; label = preflight label of sibling `$RT/libandroid_native_network_compat.so` |

**View binding (kept from r2):** `stat -L -c %d:%i $RT/run.sh` must equal the same stat of `/proc/<parent>/root/data/local/tmp/asx/run.sh` for the identified parent, both before and after. The parent is identified by the outer's route-b-owner logic; its comm is `main`, so never use `pidof`/`pgrep -f`.

## 2. WID-exact derivation (no normalization, no guessed WID)

Each start of the existing entry rewrites one field: `sed -i "s/export WL_PARENT_ID=[0-9]*/export WL_PARENT_ID=$WID/" "$RT/run.sh"`. The committed templates carry `WL_PARENT_ID=33` on line 19.

- `W_live`: read the WMS value with the entry's own command, `hidumper -s WindowManagerService -a '-a' | grep imehost0` (4th column). Separately read the `WL_PARENT_ID` field of the live `$RT/run.sh`. **The two must be equal integers; otherwise STOP.**
- Host derivation, from the committed templates only:
  `sed 's/^export WL_PARENT_ID=33$/export WL_PARENT_ID=<W>/' <template>`.
  The result must differ from the template in **exactly one line**, or zero when `W==33`.
  - `before(W)` = derived from `../static/selected-change/run.sh.d3518cef.orig`
  - `after(W)` = derived from `../static/selected-change/run.sh.candidate`
- Self-test (host): W=33 gives `d3518cef…` and `ea984942…`, 0 lines changed. W=57 gives `251df434…` and `fff026ea…`, 1 line changed.
- **CAS:** the live `$RT/run.sh` sha must equal `sha(before(W_live))` exactly, or refuse.
- **After a fresh start:** the entry rewrites the field to `W_new`, read from WMS at that start. The running file must equal `sha(after(W_new))` exactly.

The earlier "normalized SHA" check is withdrawn as an acceptance rule. It may be logged as a diagnostic only.

## 3. Write primitive (existing, not new)

Use the same guarded remote-shell pattern as `benchmark/2026-10-19-toutiao-icon-deploy/deploy.py`:

- `Device.shell`: `( set -eu; <script> ); rc=$?; echo <TOKEN>_REMOTE_RC=$rc`. Accept only when exactly one marker equals `0`; hdc's own rc0 is never evidence.
- `file_guard`: sha + mode + label + no-symlink.
- `path_guard`.

Every write script starts with these guards:

- `boot_id` equals the planned boot;
- the 61b board lock is held, per RUNBOOK;
- the §1 preimage guards and the §2 CAS pass.

Each swap goes through a fresh `<target>.ttvideo.tmp`; refuse if it already exists. Then chown, chmod and chcon, followed by `file_guard(tmp, expected)`, `mv`, and `file_guard(target, expected)`.

The preimage bytes are kept as `$RT/run.sh.ttvideo-p1.before` (guarded as absent beforehand, sha = `before(W_live)`). Receipts store every stdout/stderr/marker unmodified in the outer's private run directory.

## 4. Lifecycle: the change takes effect only in a fresh parent

The running parent keeps the environment it started with. A child or icon respawn reuses it. r2 `boot-entry.sh` refuses an existing `boots/$AUTH_BOOT` directory, and entry/start-parent refuse an existing socket. So the only route is the one already authorized for P0: **reboot → new boot_id → first manual host tap → existing entry/guardian → `start-parent` → `real-start-parent-bounded.sh` → new parent.** Do not remove per-boot refusals, do not delete old `boots/*` or stops, do not kill a parent, and **never `kill -9` appspawn-x**.

New-parent proof, all read-only:

- new `boot_id` ≠ the apply boot;
- new parent PID and birth (`/proc/<p>/stat` field 22);
- `tr '\0' '\n' < /proc/<p>/environ | grep '^LD_PRELOAD='` ends with `:/data/local/tmp/asx/libopensles_android_compat.so`;
- the running `$RT/run.sh` equals `after(W_new)` (§2) and the inode binding holds (§1);
- parent maps contain exactly one compat DSO mapping set and one `/system/lib64/libOpenSLES.so` (`05d8ac90`);
- the feed is reached and the screenshot is equivalent to baseline (main window unaffected).

## 5. Success = exact object-specific load result (t1 threshold)

RouteB's loader trace emits only `[SOURCE-NATIVE-LOAD]` (an attempt) and `[SOURCE-NATIVE-LOAD-FAIL]`. It has **no completion record**, and app native logs did not reach stderr in tap-1. So "no LOAD-FAIL + library in maps + no native error" is **supporting evidence only**. The exact result is the bound relocation itself, read without writes after one video tap in the identified Toutiao child `C`:

1. The delta contains `[SOURCE-NATIVE-LOAD] path=/data/local/tmp/asx/lib/arm64-v8a/libttmplayer.so` and **no** LOAD-FAIL for that path.
2. `/proc/C/maps` gives `B` = the start of the offset-0 mapping of that exact libttmplayer path, and `Cb` = the start of the offset-0 mapping of `/data/local/tmp/asx/libopensles_android_compat.so`. Record full lines with dev/inode. libttmplayer has 0 null init_array entries, so no `.westlake-init` copy is expected; a different path means STOP and report.
3. GOT read: `dd if=/proc/C/mem bs=8 skip=$(((B+0x4730b0)/8)) count=1 | od -An -tx8` must equal `Cb+0x3b98` (`SL_IID_ANDROIDSIMPLEBUFFERQUEUE`). The same read at `B+0x4730e8` must equal `Cb+0x3b90` (`SL_IID_ANDROIDCONFIGURATION`). The offsets are the `R_AARCH64_GLOB_DAT` slots of libttmplayer `b427614d` and the dynsym values of compat `9f558aaf`.
4. In the same window, no `Rejecting re-init … com.ss.ttm.player.TTPlayer` and no `UnsatisfiedLinkError` for `com.ss.ttm.player` natives (the tap-1 failure was `_setSupprotSampleRates`). Consumer attribution: `C` is the route-b-owner child with uid 20011206 and the new parent as ppid.

All four must hold for **"P1 load blocker removed"**. If step 3 cannot be read, the result is **unknown**, not success. The next first fatal is recorded verbatim. **No audio or video playback is claimed.**

## 6. Rollback (same CAS + fresh reboot)

- Read `W_live2` as in §2.
- CAS: the live run.sh must equal `after(W_live2)` and the DSO must equal `9f558aaf`. Any other state is foreign: refuse and report.
- Swap run.sh to `before(W_live2)` with the §3 primitive.
- Remove the DSO under `file_guard`, then confirm `test ! -e`.
- Fresh reboot via the same §4 route. Verify that the running run.sh equals `before(W_new2)`, that environ `LD_PRELOAD` lacks the compat path, that parent maps lack the compat DSO, and that the feed screenshot is equivalent to baseline.

Triggers:

- any main-window/feed/icon regression;
- a parent or child failing to reach the feed;
- a §2 or §5 STOP;
- 30 minutes elapsed.

`$RT/run.sh.ttvideo-p1.before` remains as evidence.

## 7. Raw logs and inputs

| What | Private, unmodified | Public |
|---|---|---|
| P1 confirmation | `$HOME/.local/share/westlake/toutiao-resume-20261019/video-live-r1/tap-1/` | `../static/evidence/live-r1-tap1-binding.txt` |
| t1 closure rerun | `$HOME/.local/share/westlake/toutiao-video-t1-raw/20261019T1806/` | `../static/evidence/*.sanitized.txt`, `t1-raw-log-manifest.txt` |
| t2 build/gates | `$HOME/.local/share/westlake/toutiao-video-t2-build/20261019T180522/` | `logs-sanitized/`, `raw-log-manifest.txt` |
| This window | outer's private run directory (receipt CAS outputs) | added after review |
