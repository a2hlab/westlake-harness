# Spare-board physical installer alignment — offline window proposal

**Corrected assumption: matching the61b installer is necessary, not proof of
autonomous lighting.** cc-wiki's fresh61b reboot (`0178de5c0e`) replayed56 mounts,
matched319/319 paths and routed AMS to AppSpawnX, but the ondemand daemon never
started and both control screenshots were white. This package changes **only two
physical installation-service files**, not that independent init-startup wall.

Latest outer correction (board ACK91,09:48): label-only experiment failed;
`ServiceStart invalid:appspawn-x` comes from init's stat-failed permanent
`SERVICE_ATTR_INVALID` latch (init_common_service.c:675–687). A connection before
the late boot.completed replay can poison this boot. cc-wiki is assigned autostart
v2 with earlier readiness. This supersedes the label-only root hypothesis in its
09:48 progress; do not import either an unvalidated label fix or a new service
config into this installer-only transaction. A fresh reboot and the separately
approved v2 are pending; dmesg must be part of acceptance.

No device, SSH, VM, lock, reboot or remote copy was used to prepare this package.
`plan.json` is disabled. **Request: outer review and a separate5cd time window**;
5ea remains a later, separately authorized task.61b is never writable by these
scripts. USB can disappear on remount/reboot; arrange an operator able to reconnect.

## 1. Exact bytes and source, not a new donor from a live board

| Role | SHA256 | Persistent local source |
|---|---|---|
| Factory rollback | `2c9a5294a253acb57394cc79956a4b30182a7a0ecad570844c395b38d34d82e0` | `$WORKSPACES/oh61-bms-kit-b79/board-baseline/libinstalls.z.so` |
| Reviewed51e1 | `51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5` | `$WORKSPACES/oh61-bms-kit-b79/out/wukong100/bundlemanager/bundle_framework/libinstalls.z.so` |
| Complete frozen kit | `61ff2def4508cafa6c1acd30c0c8436a5a760d5869a3520a140a216e39548bb6` | `$WORKSPACES/oh61-bms-kit-b79-r3-final.tar.gz` |

`provenance.json` freshly hashes39 local artifacts/receipts. It pins both original
and candidate source snapshots, the two patch files, Ninja recipes, the compiler,
linker and all historical build logs. Small receipts are in
`$WORKSPACES/westlake-harness-bms-deploy/benchmark/2026-09-29-install-wall-validation/`;
the same report is available at Git commit
`70fc62aa7e0369427f4ba22b1d370d2a58496eab` even though it is absent from current master.

- Patch lineage: `22de5ddb52212f3640a7214194472e30991e0c65`, approval digest refresh
  `e89d1af4fe7a29c4d095d5cebcb6367c3c87474f`.
- Operator source: `candidate-source/foundation/bundlemanager/bundle_framework/services/bundlemgr/src/installd/installd_operator.cpp`,
  SHA `7a6b2101c2fcf54a19ac2d1c9879cec144dd25b1d00d4b668b7fa17545b1d607`.
- Frozen clang15: `b107ce0366299ba5ace7095c19dfed65004415c09c57597fdf5c2b7c79ff3913`.
- R2 produced51e1; R3 changed companion BMS only. Logs include failed earlier
  rounds and are not silently converted to successes. **Do not deploy historical
  companion BMS2220df48 or the failed43bcde50 installer.**
- Persistent remote archive recorded by the old matching receipt:
  `$LAB_HOME/westlake-oh6.1-b79-bms-2220df48-installs-51e1b525/oh61-bms-kit-b79-r3-final.tar.gz`.
  No fresh SSH or rebuild was done; this is archived provenance, not new reproduction.

One unpacked working-tree source now differs: `foundation/.../base_bundle_installer.cpp`
is `6e4c0287…`, while the frozen archive member and candidate snapshot are both
`b8d3c90a…`, matching the original build receipt. `prepare.py` verifies that archive
member directly; it **does not accept the mutable working copy as build input**.
This is a companion-BMS file, not a reason to rebuild or replace unrelated services.
Because exact51e1 bytes and provenance are already local, the permitted61b readonly
`file recv` fallback was unnecessary and was **not executed**.

## 2. Scope and physical-file preconditions

Only:

1. `/system/lib64/libinstalls.z.so`
2. `/system/lib64/platformsdk/libinstalls.z.so`

cc-wiki `34509981a7` proves route-A host libraries are physical on both boards,
not transient mounts. libbms/libapk_installer/libappms/client/wrapper already match;
leave them, all app data, all JARs, boot images, init configuration and56 replay
layers untouched. No foundation restart, process kill, direct su-domain AppSpawnX
execution, SELinux mode change or broad namespace repair is present here.

Fresh precheck before any device write requires root ro, no nested `/system`
mount or alias bind, both regular non-symlink/non-hardlinked files at2c9,
UID/GID0, mode0644 or0755 and `u:object_r:system_lib_file:s0`. Any different topology
is a **stop for outer review**, not an invitation to remount another partition.
All319 U13 baseline paths are checked, allowing only those two2c9 exceptions before
apply. In particular, the old5cd Boat bridge/JAR overlay must not still mask U13;
this script cannot remove it. An existing mismatched overlay needs another approved
provider/window, not a hidden cleanup inside an installer transaction.

`reference.json` is extracted from the original61b window2 journal's **baseline**,
not its U14 candidate. Runtime124 paths compute `452447a4a0ba`; boot36 paths compute
`ee927db88a67`;319 exact paths in total. Serial is projected to5cd only; hashes are
not weakened or substituted with common821de739.

## 3. Prepared commands — NOT permission to execute

Set `WORKSPACES` to the workspace root; `HERE` below is this report directory.
All commands run on Mac with no VM requirement. Local-only dry-run:

```sh
HERE="$WORKSPACES/westlake-harness-bms/benchmark/2026-10-10-spare-installer-unify"
python3 "$HERE/install.py"
```

At the **separately approved** window: announce, acquire the real board lock using
the standard `board_note.sh`, take fresh read-only boot/physical/mount evidence,
and have outer complete `approval-template.json` in a new immutable file. Bind
`install.py`, `remote-transaction.sh`, `plan.json`, `reference.json` SHA, the exact
boot/serial/lane/action, expiry and approval evidence. `--execute` plus this exact
approval is the opt-in; the committed plan remains disabled.

```sh
python3 "$HERE/install.py" apply --execute --approval "$APPROVAL" \
  --hdc "$HDC" --lane cx-bms --out "$APPLY_EVIDENCE"
```

The sequence is guarded at every host mutation: fresh approval/expiry, real held
lock, unchanged boot → readonly319 check → unique `/data` transaction → two
`cp -p` factory backups → verify both remote hashes → **receive both to persistent
Mac evidence and independently hash them** → stage/hash51e1 → root rw → same-directory
atomic replacements → restore captured original mode, owner and SELinux label →
metadata/hash readback → sync → root ro in exit trap → full319 readback. No stale
fixed transaction directory is reused. Root-ro restoration failures are nonzero.

If interrupted after the first alias, keep the lock and logs, stop testing and
issue an explicitly authorized rollback with **this transaction's** `state.json`.
Both stock backup files must still match2c9 on Mac and board. A partial mix of
2c9/51e1 is accepted only by rollback, never by a fresh apply. The script removes
only its own unfinished temporary file and never auto-rolls back or unlocks.

```sh
python3 "$HERE/install.py" rollback --execute --state "$APPLY_EVIDENCE/state.json" \
  --approval "$ROLLBACK_APPROVAL" --hdc "$HDC" --out "$ROLLBACK_EVIDENCE"
```

Rollback approval binds the original state SHA and fresh current boot, including
after a reboot. It restores both original aliases with original metadata, returns
root ro and hashes319 paths with only the explicit old-installer exception.
Rollback does not itself reboot or repair runtime overlays. Incomplete metadata,
backups, mount topology, USB or root-ro restoration require outer intervention.

## 4. Autonomous reboot acceptance, not warm-process acceptance

Outer must decide whether to resolve the independent init daemon wall **before**
this reboot or run it as a knowingly incomplete installer-only observation window.
Existing56 autostart layers must be enabled and ready; this package neither installs
nor modifies that recovery service. A separate reboot approval binds completed
apply state, fresh boot and action. Have a physical USB operator available.

```sh
python3 "$HERE/install.py" reboot --execute --state "$APPLY_EVIDENCE/state.json" \
  --approval "$REBOOT_APPROVAL" --hdc "$HDC" --out "$REBOOT_EVIDENCE"
```

The requested reboot may break transport before the reply; a nonzero HDC exit
stays recorded and is **not** success. Wait for the same full serial and a new boot
ID. From reboot until acceptance, **no Mac replay, mount, service start, direct exec,
install or repair**. Transport reconnect and readonly collection are allowed:

```sh
python3 "$HERE/collect.py" --hdc "$HDC" --out "$POSTBOOT_READS"
```

This collects raw boot, uptime,319 hashes, mountinfo, processes, package list and
ready state. It writes no board file, starts no app and emits no visual verdict.
It deliberately leaves autonomous replay-count, parent/child/single ART proof and
human image signoff pending. Use the existing native-ticket/read-only view verifier
to bind actual evidence; do not mark those fields true from socket/READY alone.

Actual acceptance requires:

- boot differs from reboot receipt; root ro; both physical aliases51e1;
-56 autonomous mounts, all319 hashes exact, runtime452447a4/boot ee927db8;
- at least128 installed packages; init-owned AppSpawnX UID0/PPID1 after launch,
  matching parent/child views and a single ART owner;
- fresh-boot dmesg contains no `ServiceStart invalid:appspawn-x`; a permanent
  invalid service rejects even if a later warm-process intervention could render;
- physically tap HelloWorld, wait20 seconds, take a fresh `snapshot_display`
  capture and pull it; repeat ZigZag. Outer signs **both lit**, bound to current
  boot, image paths and full SHA. A white screenshot or daemon absent rejects;
- service-loader evidence (actual installd/BMS maps and process-root hashes),
  no `(deleted)` old library mapping after the true reboot.

Snapshot commands, only in the authorized acceptance window, for each physical
tap (no `aa start` or synthetic Mac launch counted as autonomous proof):

```sh
sleep 20
"$HDC" -t 5cd1e3dd00000000000000000923012c shell \
  'snapshot_display -f /data/local/tmp/spare-installer-helloworld-t20.jpeg'
"$HDC" -t 5cd1e3dd00000000000000000923012c file recv \
  /data/local/tmp/spare-installer-helloworld-t20.jpeg "$POSTBOOT_READS/helloworld-t20.jpeg"
```

Repeat with `zigzag-t20.jpeg`. Capture files are evidence, not runtime repairs.
Assemble `observation.json` and `outer-signoff.json` from these actual reads;
`acceptance.py --observation … --signoff …` checks strict proof. Fixture tests
are labeled mock-only and do not manufacture a live verdict.

On failure: retain logs and lock, request outer rollback/recovery decision. No
new fix is attempted here. After signed recovery, release the lock through the
standard owner. **Do not advance to5ea without a fresh assignment.**

## 5. Offline verification and honest gate scope

`test_installer.py` uses mock transport and a temporary filesystem: unauthorized
execution, wrong board/boot/lock/metadata, corrupt candidate/backups, atomic partial
failure, explicit rollback and remount-ro failure are known answers. Runtime
fingerprints with daemon absent, same boot, Mac repair or white controls refuse.
The simulator substitutes board paths and command helpers; it is not OH execution.

Fresh static outputs are in `evidence/`, raw original stdout/stderr in
`.artifacts/static/` with hashes in `static-results.json`; published copies only
replace the workspace prefix. Preserve all string drops/adds and existing
DEFAULT-NS diagnostics. `deployed_whois`'s native/app-map scope does not establish
installation-service ownership; fresh service maps remain a window check.
These installation-service files are not route-A native-package members, so
native N1/N2 package admission cannot be fabricated from a modified package.json.
Historical source51e1 approval and this fresh service diff must be reviewed by outer.
No JAR/class changes exist in this transaction.

Fresh result:2→2 open sites,0 namespace edges, two unchanged DEFAULT-NS findings;
raw strings29 dropped/41 added (rc1, not waived);1096→1096 exports, zero
removed/added/signature drift (rc0). The one stripped call-set difference adds
`strlen` under the spanning callback-thunk label; same-byte supplemental-symbol
analysis in `benchmark/2026-10-02-libinstalls-unification/` attributes it to exact
payload tuple validation, not a new callback-only behavior claim. Consumer list
is empty:0 reported breaks is **not a service-client closure test**. Live client
closure, install canaries and exact owner mapping remain pending. The first ABI
attempt used NDK23 llvm-nm without `--format=just-symbols` support and failed;
its raw rejection stays in `.artifacts/static-ndk23-rejected/`. Fresh rerun used
compatible LLVM, with tool hashes in `static-results.json`, without modifying
the ABI checker. This is a tool correction, not an exception to the gate.

Generate `provenance.json`, `reference.json`, `plan.json` twice byte-identically:

```sh
python3 "$HERE/prepare.py"
python3 "$HERE/test_installer.py" -v
cargo test --manifest-path "$WORKSPACES/westlake-harness-bms/tools/spec-checks/Cargo.toml" \
  --test spare_installer spare_installer_offline -- --nocapture
```

See `results.json` for fresh exit codes, input hashes, landing/preflight and the
explicit unverified real-board acceptance. No old PASS is substituted for a new run.
