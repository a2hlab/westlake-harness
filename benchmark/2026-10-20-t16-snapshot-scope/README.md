# T16 exact5cd preboot snapshot scope partition

The historical5cd544-target plan cannot be passed unchanged to today's `board_state_snapshot.py`: its `selinux_label_audit.safe_target` accepts only `/system` and `/data/app`. It refuses26 original `/data/westlake-demo` and `/data/local/tmp` targets before device access. Do not weaken that shared gate or silently lose these targets.

`capture-scope-plan.json` is exactly the518 currently supported original targets. `supplement-targets.json` is exactly the26 rejected original file targets. Their disjoint union equals the original544 targets; current main's actual `plan_targets(..., load_recipe())` accepts the518 plan. Original plan file SHA is `622f61676ec6f44c0c1a19fa9cc0d95b4da00efd0e75a176de59381a573b213b`. Its note binds the original57 baseline targets plus487 actual5cd restore members. This is not61b's64-target plan. `results.json` pins tool, recipe and collection sources and both JSON/file and canonical plan SHA.

The518 plan already contains the actual5cd run/media/player/liblog/hwui/shim and the full original physical runtime file inventory. The existing snapshot tool additionally captures system/android recursively, appspawn/seccomp, mounts, parameters, init CFG hashes/content, layer policy probes and sandbox scope. The26 supplement includes5cd control scripts and the three actual source-app staging files. It records labels, hashes and metadata without changing permissions or contents. It also explicitly records the new compat DSO's absence/presence; absence is valid evidence here, whereas declaring the absent DSO as an existing `file` in the normal plan would manufacture an INCOMPLETE result.

Before capture, use a fresh output directory and verify the5cd lock is absent. If collecting inside the outer deployment window, use that exact holder. This collector never acquires/releases a board lock. The outer must reject other tasks' lock acquisition and freshly recheck identity before later deployment. The normal snapshot tool has no built-in whole-window deadline/lock guard; outer scheduling remains responsible. Both parts must finish on the same expected boot before reboot; neither a plan-validation PASS nor518-only `complete=true` establishes combined scope completeness.

```sh
python3 scripts/lab/board_state_snapshot.py 5cd1e3dd00000000000000000923012c \
  --plan benchmark/2026-10-20-t16-snapshot-scope/capture-scope-plan.json \
  --hdc "$HDC" --out "$SNAPSHOT_OUT" --label t16-5cd-before
python3 benchmark/2026-10-20-t16-snapshot-scope/collect_supplement.py \
  --execute --repo "$REPO" --hdc "$HDC" --boot "$EXPECTED_BOOT" --out "$SUPPLEMENT_OUT"
# Add --holder "$EXACT_HOLDER" when the outer window holds the lock.
```

Repeat the same plan and supplement after restore; compare matching plan and collection hashes, scope membership, raw receipts, labels and hashes. Compat must return to its original ABSENT state. Changes from reboot, known WID rewriting and any diagnostic parameter must remain explicit rather than ignored. The supplement's stable-boot terminal marker and rc0 are required; timeout, missing target, symlink or lock drift leaves PARTIAL with all received raw bytes retained. Overall acceptance is a human comparison of both complete parts, actual runtime identity and screenshot evidence. No device operation was executed while preparing this package.
