# Ordinary log increments — offline-tested observer

**Not run on a device.** Existing child22035 is reported alive; this delivery does not create a new spawn. A separately prepared ordinary UI close/reentry session is needed to observe one. The observer itself never performs UI, starts/stops an app, sends a device signal, or reads control implementations/env. It is independent of all stopped executors.

The initial sample establishes EOF offsets for the two already-identified ordinary logs. Subsequent serialized samples run no faster than once per second (slow commands reduce cadence; no catch-up bursts). Hard limits:90s overall,10s per local HDC invocation,1MiB **combined captured stdout/stderr** across the run, and64KiB maximum increment per file per sample. Local metadata/argv/receipt files are additional to the stream budget. No automatic retry. A gap exceeding64KiB stops before copying that increment.

Boot,parent PID/birth/root UID,fd1/fd2 destination,regular-file dev/inode/size and child identity are checked. Child identity includes exact PID,PPID,birth,all four UIDs and full first cmdline argument. A missing exact matching ps row is only a selector result, not proof that every process was observed. Remote POSIX read/case checks all numeric rows but returns only the target rows. No awk/tr or new wc dependency is used. A fixed-length raw dd prefix includes the complete expected cmdline first argument and its terminating NUL; it never enters a shell variable. Short-lived processes between samples remain unknown.

**Birth transition:** pre-ps absent/post-ps new child is `identity_transition/partial`, not a fatal change when no child is bound yet. Raw increments and uptime bracket remain in the command stdout. Previously established offsets are not advanced; the next stable sample re-reads those bytes and binds the child. Consumers must use offset ranges to avoid double counting. An initial transition sample only establishes its zero-data pre-size origins. Once bound, replacement/disappearance stops. Mid-sample changes to an already observed child also stop.

Detected truncation/rotation,identity drift,malformed/short frames,nonzero command status,timeout or byte cap stop the run. A truncate-and-regrow fully between observations may be undetectable; no complete audit-history claim. Raw failed-command output is preserved. Each run requires a new output directory; exclusive file creation prevents overwriting originals. Canceling a timed-out local HDC client never invokes a device kill command; remote cancellation/completion is not claimed on timeout.

## Entry

Set BOOT/PARENT_PID/PARENT_BIRTH from a fresh independently obtained identity; no old identity is silently supplied. OUT must be new and private. First preview only:

```sh
python3 benchmark/2026-10-24-ordinary-host-timeline/incremental-observer/observe.py \
  --boot "$BOOT" --parent-pid "$PARENT_PID" --parent-birth "$PARENT_BIRTH" \
  --out "$PREVIEW_OUT"
```

This writes exact initial argv without starting any subprocess. For the later authorized observation use the same entry with a **different new OUT** and `--execute`; no UI action is implied. `--hdc` optionally selects the existing local tool path. Serial61b and UID20011206 are fixed.

Outputs: `plan.json`, immutable `command-NNNN/{argv.json,stdout,stderr,receipt.json}`, `sample-NNNN.json`, `result.json`. Length-framed stdout contains original binary increments; offsets and SHA in sample receipts identify accepted ranges. Whole-command receipt SHA includes framing/metadata. Partial samples use `ranges_unaccepted`. Approximate observation time comes from device uptime before/after plus local monotonic timing; it does not supply a missing per-log timestamp or remove buffering ambiguity.

## Validation

15 local tests pass, including actual local shell production against synthetic proc/files, actual local pipe byte cap,actual timeout with partial output,nonzero exit and no overwrite. Rust selector `ordinary_launch_increment_fixtures` passes; task lint100%,warnings retained. No real HDC command was run. First test run failed because process-stat/log-stat frame labels collided; `.private/test-01` is retained, corrected labels tested in subsequent runs. Public validation and raw-index record these separately.

Read `readonly-whitelist.json` for every remote command/read target. Existing collection conventions come from T114 PID/birth bracketing and this task's already-verified ordinary parent/events files; no old collector/control source is copied.

## Target-tool and byte-budget revision

The first version assumed awk/tr and retained two full ps tables. Those assumptions were corrected offline. A restricted-PATH actual shell fixture excludes awk/tr/ip/route/wpa_cli/ndc/wc. It reads an18,592-byte synthetic ps table with unrelated names containing spaces, returns only target rows, and completes90 samples totaling704,806 captured stdout+stderr bytes (including padded process-status fixtures). The15 original test methods remain and pass. This is a deterministic local90-sample budget test, not90seconds of board evidence. Larger real log increments can still stop at1MiB. The prior source/manifest snapshot remains private; no old evidence is overwritten.
