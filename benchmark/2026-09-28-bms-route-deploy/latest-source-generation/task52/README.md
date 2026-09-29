# B6 / task 52: first-frame relocation failure

Task 50's stack identified the VSync initialization boundary, but treating its
low PC as a library-relative code address would be wrong. The raw fault records
PC `0x29dcc` inside anonymous `0x10000-0x10010000 rw-p`, not an ELF executable
mapping. The fault is an attempted instruction fetch from non-executable data.

[Address evidence](diagnosis/fault-address-evidence.txt) and
[relocations](diagnosis/frame-relocations.txt) identify the path precisely:
`RsFrameReportExt::Init` calls `dlopen`; `libframe_ui_intf.z.so`'s third
`.init_array` slot (`0xc850`) refers to `OHOS::RME::BasicOpenRtgNode` (`0xa438`).
That initializer tail-calls `HiLogPrint@plt` at `0xa4c0`. Its GOT slot is
`load_bias + 0xcc18 = 0x7f0e9ccc18`; the fault's memory dump contains `0x29dcc`
there. This equals `libhilog.so`'s exported symbol value, with no load bias.
For the captured mapping, the resolved address should be `0x7fb4e29dcc`.
The saved argument registers also match the initializer's logging call. The
underlying reason why relocation omitted the bias is not yet established.

Both parent map snapshots contain the same OH/shared-library path set; neither
contains `libframe_ui_intf.z.so` or `libvsync.z.so`. The B5 HelloWorld child loads
them itself successfully. This independently agrees with the outer review's
older B5 observation. Both baseline parent and child have seccomp enabled; the
child has two filters. No permission relaxation is part of this experiment.

## One-variable candidate

Host `DT_NEEDED` order differs: task 50 puts `libhilog.so` first, whereas R155
places it after `libsec_shared.z.so`. Remove only the duplicate explicit early
libhilog link input, retaining the later `-lhilog`, to reproduce the exact R155
ordered list. [Patch](recipes/r155-needed-order.patch) records both the canonical
build recipe and its retained-provider executable slice. The historical recipe
also contains that duplicate input; R155's actual dynamic table, rather than an
assumed exact historical recipe, is the evidence for this restoration.

No code in seccomp, memory protection, RELRO, product TLS or namespace setup is
changed. Regenerating the identity chain updates sealed manifest, provider
identity constants, child and host; 26 R155 providers and the small abort bridge
remain byte-identical. The trial tests a loading-order hypothesis; a passing
host build alone cannot establish the diagnosis.

Generation `336d7cedb65b` uses host `27cbdfeb`, child `10e31fc2`, and
runtime-provider `5df16f8d`. Strict links, deterministic two-pass builds,
319-library/2831-edge host closure, six closure controls and four missing-symbol
controls pass. The known-answer suite reports 69 tests, 2 skipped, no failures.

The preliminary [static inventory](static/summary.json) lists all functions,
dynamic fields, dynamic symbols, init/fini arrays, TLS and readable `.rodata` /
`.dynstr` strings for the three objects. Its aggressive address normalization is
for triage, not semantic-equivalence proof. Full disposition review was reassigned
to cx-bms task 53 by the outer reviewer; subsequent deployment must consume that
review's restore list together. No unreviewed differences are called harmless.

## Link-order device result

The exact R155 NEEDED order did not produce a usable candidate. HelloWorld PID
562 passed the new identity/handoff gates and returned from handleBindApplication,
then libandroid.so relocation reported missing `WLTG_VerifyCurrentThreadReady`,
followed by skia/hwui abort. It did not reach onCreate or the former VSync failure;
this trial cannot establish whether that earlier relocation fault was fixed.
The final screenshot is the OH desktop. Wikipedia/NPE and candidate ZigZag were
not attempted after the prerequisite failed.

All seven generation mounts were removed and ten baseline hash checks passed.
B5 HelloWorld PID 4731 and ZigZag PID 5745 then displayed their own interfaces,
with no new fault files. See [trial](evidence/link-order/final.jpeg),
[HelloWorld rollback](evidence/rollback-helloworld/final.jpeg), and
[ZigZag rollback](evidence/rollback-zigzag/final.jpeg). Outer visual acceptance
remains separate from the agent's image inspection.

The delegated task53 comparison uses the R155 system/android provider alias
`977fb347`, whereas the preliminary inventory used route-a `80c9aee0`. Treat
that preliminary inventory only as leads; it is not the authoritative parity
assessment. Its 214 function differences must not count the single restored
DT_NEEDED field as one restored function.

## Authorized B2/B3 installer update

Both existing installer files were 184d40a5 (416384 bytes), root:root 0755,
SELinux system_lib_file. Backups are `/data/local/tmp/b6-task52-installer-backup/0.so`
and `1.so`. The exact B3 staging artifact 675536e8 was atomically installed to
/system/lib64 and /system/lib64/platformsdk with those attributes preserved.
The root filesystem was already rw and its mount mode was preserved. An initial
read-only dependency probe used the wrong libc++_shared directory; the actual
library is /system/lib64/libc++_shared.so and is in the configured search path.
No mutation preceded that corrected preflight.

Foundation PID 12753 saw the correct four path hashes, but its desktop capture
was black (36627 bytes). The explicitly authorized reboot recovered the UI.
The boot recovery service restored seven PR03 mounts after a delay; ten remaining
R155/B5 mounts were then restored from the exact pre-reboot mount table, after
source identity checks. The general HelloWorld restore script was inspected but
not executed because it would overwrite the new installer. No payload was rebuilt.
New parent PID 6097 runs signed B5 host/child/JAR identities. Foundation PID 886
sees 675536e8 at both /proc/886/root paths. The [desktop](installer/desktop.jpeg)
is visibly nonblack, with system icons, wallpaper and status bar (81034 bytes).
[Receipts](installer/results.json) retain the new boot ID and complete mount list.

Post-reboot HelloWorld PID 8448 passed. The first ZigZag attempt exited with
`android_set_abort_message` missing from original libmain.so: the five app-native
bind mounts under /data/app had been omitted from the initial restoration.
Restoring those five exact candidate files (source SHA checked before mounting)
restored ZigZag PID 12464 and its visible title/game screen. Both attempts are
retained under installer/. Complete recovery is seven automatic PR03 mounts,
nine R155 system overlays, five R155 app-native overlays, and one B5 JAR overlay.
The board was unlocked after successful recovery.

## Preparation for the grouped restoration

Task53's provider caveat is now resolved by [live evidence](live-provider-identity.txt):
PID 8448 maps route-a provider 80c9aee0; its /proc root reads back that SHA.
Task56 is assigned to repeat provider comparison and deliver RESTORE-PLAN.md.
No further B6 candidate will be deployed until that grouped plan is applied.
[The host stdio patch](preparation/host-stdio-parity.patch) is prepared, unapplied;
it removes the broker compilation/link input and its LIBC export block together.
This should restore AppSpawnDump's imported vfprintf/fflush binding; a later
strict link and static readback must confirm it. Child/host service changes
remain coupled to the pending manifest/provider plan. Identity checks stay on.

Public text excerpts normalize workspace home paths and strip trailing whitespace;
raw VM command receipts and original fault/maps logs remain in the recorded run
directories. SOURCE_CLOSURE and ROUTE_A_INPUTS ledger bytes are unchanged.
