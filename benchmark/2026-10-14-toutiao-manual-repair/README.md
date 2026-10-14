# RouteB data-directory owner repair

The deployed JIT50 script ran as root, created `package/code_cache/art-volatile` with `mkdir -p`, and changed ownership only on the last directory. In5cd's actual parent5257 namespace, `/data/data` binds the host runtime's `app-data`; the package root was0:0/0755. UID20011300 could not create `app_webview`. The current child14587 log proves an AwDataDirLock ENOENT exception, return from ActivityThread/Looper, then `_exit(1)`. This incident is not a claim about historical random SIG11.

The system namespace's old UID20010053 path is a different object and is not the repair target. 61b has a correctly owned package root and existing0700app_webview; its surviving child6789/no-window incident remains separate.

## Evidence and actual experiment

`static-triage.json` pins the source and persistent raw evidence. Outer performed the sole directory owner experiment under its own5cd lock. The first attempt refused before mutation because OH lacks `/proc/task/*/children`. The next attempt changed owner but returned nonzero on an OH shell pipe-pattern parsing bug. Neither failure is erased. The successor uses strict PID/PPID `ps` parsing and IFS field splitting. A separately executed **read-only reconcile** confirmed the same inode/mode/label and desired owner against the original preflight. No chown retry was needed.

Outer then executed one original host_spawn request with existing parent5257/birth8214/WID29 and original JIT50. It returned child17175/rc0. Outer reports t20 true feed plus privacy dialog and application-created `app_webview`0700 owned20011300. This supports the directory-owner hypothesis; repeated article/return and long stability remain pending. We did not operate a board or click privacy. Original raw evidence stays in `$WORKSPACES/_verified-source-closeout-20261014/toutiao-owner-5cd-20261014T1758`.

## Persistent source candidate

`prepare_jit51-owner-5cd.sh` is a **new, not-installed** successor of the frozen `prepare_jit50.sh` (SHA b42a28e7a29a53c162a43ac25eaf52c24906f1afdd179c9414882772ccac34c8). It runs in the verified parent mount namespace with actual5cdUID20011300. It validates all existing explicit package/code_cache/art-volatile paths before changes; rejects symlinks, non-directories, foreign owners and wrong labels; creates only absent explicit directories; normalizes owner0:0 or the correct app owner; preserves existing modes/labels/inodes, then retains the original cache0700 requirement. It does not precreate app_webview, recursively chown, clear user data, or touch61b. It logs each metadata preimage and result.

Existing source pattern: MAIN `sources/api-implementations/FZ-001/archive-source/adapter/framework/package-manager/jni/apk_installer.cpp:1056–1080`, `CreateDataDirs`, applies owner after mkdir even for existing directories. This is an implementation precedent, not proof that BMS currently prepares RouteB's private namespace. The actual RouteB ordering remains `spawn-prepared.sh:28` → JIT → host_spawn. The data namespace bind is `source-build-native691/westlake/native/source_app_namespace.c:81–91`; its deployed ELF linkage is documented separately in the r4 directory closure. No replacement native build is required.

### Installation dependency delta (not executed)

1. Create a new restore/activation candidate; retain frozen JIT50 and old receipts.
2. Bind JIT51 full SHA in the candidate `STARTUP_JIT_SHA`, recompute `startup.env`/`startup.expected.sha256` through the existing compiler, and update the candidate file manifest/realization/selfcheck. The original `spawn-prepared.sh` checks both physical and parent-view JIT SHA/inode and must remain intact.
3. Installation/rollback of the script follows the original provider backup/CAS path. Do not bypass exact seal gates, or replace live startup pins piecemeal.
4. Owner experiment rollback is only the single package-root owner CAS described in OPERATOR.md; user-created app_webview and other new files remain. Persistent owner initialization is intentionally not reversed by deleting app data.

## Verification and boundaries

Run `python3 benchmark/2026-10-14-toutiao-manual-repair/test_owner.py` or `cargo test --manifest-path tools/spec-checks/Cargo.toml --test toutiao_owner`. The tests execute local shell with isolated metadata/privileged-command recorders: fresh creation, existing root-owned directories, already-correct owners, foreign-owner and symlink zero-write rejection, strict ps protocol, metadata parsing, and exact command binding. They are not physical OH/chown proof. Outer raw receipts are separately referenced.

`render_owner.py` only renders disabled command cards, never calls HDC. Only the outer executor can run the pinned argv with its current authorization. Require both host rc and explicit remote rc. `single_spawn_remote.sh` is one-shot diagnostic reuse of the original JIT/host_spawn argv; it does not install a supervisor. Desktop relaunch does not restart an exhausted guardian; persistent reentry is a separate investigation (p4), not silently included here.
