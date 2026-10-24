# t3 offline normalized-receipt checker

The first checker incorrectly accepted a same-SHA activation mapping with a different published inode, rejected a legitimate UID0 parent, and accepted two different first-open click times. The outer review preserved those failures in `$HOME/.local/share/westlake/native-validation-checker-review-20261024/review-01/results.json`. The corrected checker binds cross-stage objects, permits the parent's actual nonnegative UID, compares host identity tuples (including birth), and requires activation and first-open to share **the identical click receipt**. The outer review02 independently checked those regressions; both reviewer originals remain unchanged.

**Normalized receipt consistency is not raw-output parsing, source authenticity, or board acceptance.** This checker does not parse arbitrary HDC text. It reads an explicitly supplied receipt directory, checks referenced bytes/hashes and normalized values, and never executes recorded argv. Normalization must be independently reviewed against the original outputs; putting manually entered values in JSON does not make them HDC observations. In particular `body_errors`, process identities, metadata and command roles are normalized assertions, not inferred from text by this checker.

The actual main interruption directory currently has no `packet.json` or complete device receipts. The real offline invocation returned **rc2, pending_missing, device_validation=unverified**; [actual-interruption-result.json](actual-interruption-result.json) pins the unchanged interruption record. Lack of visible lock/write invocations is not a complete backend audit. No stopped action was retried.

## Small v1 schema

`packet.json` contains `schema: native-validation-receipts/v1`, explicit `origin: recorded|synthetic`, `run_id`, `serial`, `clock_id`, `plan_sha256`, and ordered `receipts`. Every reference is exactly `{path, sha256}`: a relative file below the explicitly supplied receipt root. Traversal and symlinks are rejected. Artifacts are hashed, not loaded as code. The explicitly supplied plan is an additional read-only input. An absent packet can report the existing `execution-interruption-01.json` hash without interpreting it as validation.

Each referenced **normalized phase receipt** has matching run/serial/clock/origin/boot, `kind`, finite `phase_start/phase_end`, `commands: [reference...]`, and `observations: reference`. Phase aggregation may cover multiple ordinary command receipts. It is not a fabricated single command interval.

Each referenced **command receipt** has `command_id`, matching run/serial/clock/origin/boot, finite monotonic `start/end`, string-array `argv`, `role`, boolean `write`, separate integer `transport_rc/remote_rc`, normalized `body_errors`, and hashed `stdout/stderr` references. Recorded argv is data only. Supported roles are read, icon, touch, publish, rollback, power and reboot. Nonzero/unknown rc or normalized body errors prevent internal consistency. Shared first-click references are deduplicated by command SHA; reuse of one command ID with different bytes is rejected. All writes must lie strictly within the acquired/released lock interval. NaN/Infinity and boolean numeric fields are rejected by the relevant checks.

The observations file repeats the phase identity and supplies these required evidence fields:

| Phase | Normalized fields checked |
|---|---|
| `lock` / `unlock` | owner/token, held-before rc1+empty output/acquire rc0; release rc0/held-after rc1+empty output |
| `preflight` | host/parent/child, mapping, candidate/rollback artifact references, review02 manifest and callback-review references matching plan SHA; frozen-gate reference with positive checked count/no violations; non-target fingerprints, base/override power, screen |
| `publish` | target, SHA, metadata, atomic-rename method, sibling staging path/device, new inode, unchanged non-target fingerprints; publish command reference |
| `activation` | new-boot host/parent/child, actual mapping and child identity bracket, shared `click` command reference, observation_end |
| `first_open` / `same_host_return` / `new_host_old_child` | host/parent/child and child_after, mapping, one click reference, observation_end, timestamped screenshot references, outcome `review_pending|failed`, ordinary touch command/after-image references; host_window_id and logical/actual/parent association fields for new-host phase |
| `rollback` | target/baseline SHA/original metadata and rollback command reference |
| `final` | recovery new-boot host/parent/child, actual baseline mapping, unchanged non-target fingerprints, original power/screen, final screenshot |

Process identity is `(boot,pid,birth,uid)`. Host and child UID must equal the target UID; parent UID is any observed nonnegative integer. Same-host return keeps the original identity; new-host/old-child requires a different host tuple while retaining the child and parent tuples. PID reuse with a new host birth is valid; a reused child PID with changed birth is not old-child retention.

A mapping includes `mapped_path`, `backing_path`, `device`, `inode`, `sha256`, `mount_namespace`, bracketed `child_before/child_after`, and `process_root_stat` with matching device/inode/SHA/namespace and metadata. Activation device/inode must match the published object; UI mappings must retain activation device/inode/namespace. Root-only disk SHA is insufficient. Final recovery requires the actual baseline mapping, not just rollback disk bytes.

Activation and first_open use the exact same click reference. The first-open aggregate begins at that click and may overlap activation's observation interval; subsequent UI phases are ordered separately. Icon observation is at most120 seconds from the referenced click command's end. No new publish/icon/touch at or after LOCK+900; rollback begins before1200; closure finishes by1800. A failed candidate can have internally consistent receipts and complete restoration. Its candidate outcome remains activation_failed or failed_observation, never repair PASS. Incomplete/invalid cleanup remains recovery_required_or_unverified. Producer identity stays unknown.

## Verification and limits

`test_receipts.py` creates explicitly **synthetic** JSON/raw fixtures in unique `.private/synthetic-*` directories. Its argv values are non-executable synthetic labels. Image fixtures intentionally contain only a recognizable signature plus synthetic text: the checker verifies the byte reference/container signature, **not image validity or meaning**. Fixtures are not device evidence. The twelve test categories cover identity/artifact/metadata errors, activation failure, command errors, run/time/birth mixing, lifecycle identity distinctions, numeric and120-second limits,900/1200/1800 deadlines, write/lock bounds, full rollback evidence, reference integrity, and failure/missing-result separation, including review01 regressions.

The actual final Cargo invocation returned rc0, one Rust selector passed, and all12 Python test categories passed. Earlier tests and outer review01 failures remain indexed. No complete agent-spec lifecycle or board test is claimed.

```sh
cargo test --manifest-path tools/spec-checks/Cargo.toml --test host_window_native_validation host_window_native_validation_receipts -- --nocapture
python3 benchmark/2026-10-24-native-host-window-recovery/device-validation/check_receipts.py --receipts "$RECEIPT_DIR" --plan "$PLAN_FILE"
```

Use `--synthetic` only with explicit synthetic fixtures. CLI rc0 means internal receipt consistency only; a complete recorded packet still reports **pending_review**, with **device_validation=unverified**, **visual_review=pending_review**, and **authenticity=not_established_by_hashes**. CLI rc2 means missing/invalid evidence. Every image decision remains independent external human review.

[results.json](results.json) pins the untouched t3/plan/interruption inputs and reviewer results. [raw-index.json](raw-index.json) lists persistent command/stdout/stderr hashes. Exact public delivery is [landing-paths.txt](landing-paths.txt); generated fixture trees, raw streams and unrelated worktree files are excluded. There is no collector, scheduler, deployment helper, candidate change or device operation in this delivery.
