# Immutable T4 review: disabled offline pass, production admission pending

## Identity and independently replayed evidence

Only git commit `e5763d369cf61e925a2a09f1c7ace8019f818931` was exported, never
t0's editing payload. Release manifest SHA365ac62b5545ed9b45b0d53a64010ff4f2ed3596a2856a9314172dfde98fb370,
bindings SHAd352c7681d733a11f759a38039477610d0ead79f6cfb7469cab0f9bf67d536f8,
all17 manifest entries and17 bound source objects match. Accepted R1 watchdog
9763171a and helper80a263d9 remain unchanged. This did **not** rerun R1's suite.

`review_t4_e576.py` ran16 new integration scenarios using the immutable shell
logic with documented absolute-path relocation and external native/identity/
frame recorders. `evidence/t4-e576-independent.json` includes original80 raw
case-file SHAs, exact source/relocated provenance, diagnostics and data sentinel
comparisons; `evidence/t4-e576-replay.txt` preserves the replay output.

Important harness limit: sandbox denied AF_UNIX binding in the first attempt.
The final replay substitutes isolated socket-readiness files and the Bash -S
test, in addition to t0's already synthetic native/identity/frame substitutes.
It is not a real socket, OH shell, decoder or board proof. The second attempt
failed only because the reviewer had not created the evidence parent directory;
both failed export directories remain intact. Third attempt completed all16.
The frozen source files were not changed; only generated fixture tools/paths
were relocated or fault-injected. No board/VM/remote command, permission change,
privacy action, data rotation or signature occurred. Original R2 files52/52
remain unchanged, as does landing SHA197a9d4f.

## Decision

**Offline pass of the disabled package and tested conservative error handling;
production admission remains pending.** Do not call this a ready-to-execute
recovery release. Default authorization binding is NONE; host preview rejects
execution regardless of an authorization argument. Both are real conservative
controls. Preimage/JPEG/budget readiness, however, is not closed by those
controls or by the fixture's synthetic flags. No rendered UI/seal was accepted.

| Independent scenario | Actual result |
|---|---|
| normal existing-parent fixture | rc0, synthetic READY, nsenter before host_spawn; not a real UI |
| unsigned/wrong boot/expired/wrong candidate/wrong authorization SHA | each rc2, no namespace/JIT/spawn |
| missing helper | rc2, no launch |
| missing socket/JIT/private-JIT mismatch/stale parent WID | each rc3 START_FAILED, no host_spawn |
| incompatible-format approval flag=no | rc2 CAPTURE_FORMAT_PENDING, no launch |
| omitted preimage proof, other synthetic flags=yes | **rc0 READY; no preimage-specific refusal** |
| classifier missing, format flag=yes | **rc0 UI_UNVERIFIED after nsenter+host_spawn** |
| classifier rejects frame, format flag=yes | rc0 UI_UNVERIFIED after nsenter+host_spawn; no false READY or app cleanup |
| third WMS call delayed17s, independently enforced real15s timeout | rc3 START_FAILED, no namespace/JIT/spawn |

The first12 rows' individual baseline/negative cases meet their control criteria.
The last four cases are specific admission observations, not four more green
production readiness assertions. Recorded old stop and three data sentinels are
unchanged in every completed case; no forbidden hdc/orb/ssh/kill/uinput command
was recorded by the harness.

## Six-item final disposition, without expanding scope

1. **JIT:** real8s parent-namespace preparation order is restored. Frozen
   spawn-prepared now checks physical/private-view SHA and device:inode before
   JIT, then rechecks parent/WID. Private-JIT mismatch independently refuses.
   Effective UID/run/request derivation is pinned, not live-readback proof.
2. **HERE/aliases:** both historical watchdog/helper aliases plus independent
   attempt execution copy are explicitly listed. Default entry is disarmed.
   F/screen-gate remains an external prerequisite, not a placed16th control
   member; missing classifier is not rejected before spawn when flags say yes.
3. **Environment:** runtime/stage/socket exports and new/existing parent modes
   are present. Real helpers retain fixed Route B paths. No exact-path equality,
   forced TT_PROC=/proc, cleared/bound inherited child attach variables or
   finalized poll/attempt/PATH policy is implemented in frozen entry. This must
   be settled by the actual new authorization/entry integration, not inferred
   from successful relocated fixtures.
4. **Parent/window and budget:** foreground/current-parent-WID gates are present
   and stale WID refuses. **Budget gap remains:** captured real-start-parent can
   sleep20*.25s, wrapper birth20*.1s and socket40*.25s: up to17s of sleeps plus
   tools, while unchanged976 uses timeout15. Final wrapper SHAeee4d652 is the
   same as the earlier handoff. Donor timeout recorder has no timeout enforcement
   and donor sleep is a no-op, so its green startup tests do not close this.
   Our real-time fault shows outer refusal on a slow WMS read, not a viable
   worst-case startup envelope or absence of a post-parent orphan. Do not alter
   accepted976 or extend an expired driver to hide this discrepancy.
5. **JPEG/integrity:** manifest/member SHA checks exist, and format flag=no is
   genuinely rejected. Actual classifier808f58a1 is documented as PNG-API with
   jpeg_verified=false. No decoder was executed in this review. A yes flag plus
   an absent/rejecting classifier still starts the child; observation then stays
   UI_UNVERIFIED, which safely avoids fake UI READY but is **not** fail-before-
   launch compatibility admission. Exact decoder/placement/format proof remains
   pending; renaming a JPEG or a synthetic feed label does not supply it.
6. **Preimage/rollback:** all16 member preimages are literal unbound strings.
   New plan says to reject missing metadata; preview only lists it and rejects
   every execute request. **There is no executable preimage-specific guard in
   entry.** A synthetic exact-hash authorization omitting preimage fields can
   reach READY. This does not bypass NONE in the distributed package; it proves
   default refusal comes from unsigned status, not verification of preimages.
   Concrete backup SHA/mode/uid/gid/label/absent and restore provider are still
   absent. Future outer approval must bind and enforce them before any writes
   or execution. Retain original stop/data, no unsafe old-watchdog restart or
   parent/U13 signal; a preview rollback description is not a tested restore.

## Minimal future read-only evidence requests (not executed)

Outer/authorized collector only, on the specified61b; no lock/write/repair is
performed by the commands below. Require fresh boot before and after, and never
reuse captured parent9529 merely because it existed in followup1406.

```sh
SERIAL=61b0657200000000000000000324012c
"${HDC:?}" -t "$SERIAL" shell 'cat /proc/sys/kernel/random/boot_id; getenforce; ps -A -o PID,PPID,UID,NAME; hidumper -s WindowManagerService -a "-a"'
```

Once the collector independently selects the current exact Route B parent,
read its stat/status/exeSHA/mnt and init mnt, only the WL_PARENT_ID environment
field (not a complete potentially private environment), and public/private
run.sh/JIT SHA+device:inode. Example data-source commands, not an adoption rule:

```sh
"${HDC:?}" -t "$SERIAL" shell 'RT=/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d; sha256sum "$RT/run.sh" "$RT/prepare_jit50.sh"; stat -L -c "%d:%i %u:%g:%a" "$RT/run.sh" "$RT/prepare_jit50.sh"; ls -lnZ "$RT/run.sh" "$RT/prepare_jit50.sh"'
# Substitute a freshly verified numeric PID, never the historical one:
"${HDC:?}" -t "$SERIAL" shell 'p=<fresh-verified-parent>; cat /proc/$p/stat; grep "^Uid:" /proc/$p/status; readlink /proc/$p/exe /proc/$p/ns/mnt /proc/1/ns/mnt; sha256sum /proc/$p/exe /proc/$p/root/data/local/tmp/asx/run.sh /proc/$p/root/data/local/tmp/asx/prepare_jit50.sh; stat -L -c "%d:%i" /proc/$p/root/data/local/tmp/asx/run.sh /proc/$p/root/data/local/tmp/asx/prepare_jit50.sh; grep -ao "WL_PARENT_ID=[0-9]*" /proc/$p/environ'
```

Replace the placeholder before any future command; it is deliberately not a
direct executable PID. For the exact16 member targets and three external
prerequisites in frozen bindings: per-target `ls -lnZ`, `stat -c '%u:%g:%a:%s'`,
regular-file SHA or explicitly observed ABSENT, plus mountinfo. No globbed app
data read, permission repair or guessed absent preimage. Also read current stop
SHA, actual stage host_spawn/source_app_namespace/request SHA and request bytes
312..319, socket metadata and caller tools/caps. Read the **already-existing**
frame header using `od -An -tx1 -N16 <existing-frame>` and pin classifier SHA;
this does not invoke snapshot_display or a decoder. Actual JPEG decoding and
bounded delayed-start/restore fixture evidence need a separately reviewed local
test/candidate; read-only board collection alone cannot fix those code gaps.

Scope is unchanged Plan-2:61b local20-key + existing5cd128 comparison. The next
review input is a frozen correction/readiness package or exact outstanding
evidence, not live editing paths, old04d plan or old no_mac_repair signature.
