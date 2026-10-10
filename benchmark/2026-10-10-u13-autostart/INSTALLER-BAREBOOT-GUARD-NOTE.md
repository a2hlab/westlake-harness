# Installer bare-boot empty-base guard + cx-bms pre-installer assertion (#91 cc-wiki, 2026-10-10)

**Incident (cc-t3, 5ea):** `/system/android` is bind-mounted by recover from `/data/westlake-demo/u13/
sources/seq1`. After `DISABLE` + a bare `target boot` the bind is gone and the physical `/system/android`
is an EMPTY (or degraded) mount-point dir. `install-westlake-u13-autostart.sh` step 2 (ARCHIVE) did
`rm -rf sources/seq1; cp -a /system/android/. sources/seq1/` — archiving the empty dir **destroyed the
only good base**. The first guard (`c9bea54a80`) only refuses a LIVE bind / READY receipt, not a bare-boot
empty physical target. 61b's v1 seal runs exactly `DISABLE → bare boot → installer`, so it would hit it too.

## ① + ② Done here (installer second guard + KA)

`install-westlake-u13-autostart.sh` directory-archive branch now, **before** the destructive `rm -rf "$dst"`:
- counts the physical target files and the existing archive files (`find … -type f | sed -n '$='`; no `wc`/`tr`);
- **if the physical target has FEWER files than the existing archive → REUSE the archive** (keep `seq$seq`,
  emit a `…\treused` TSV row, `continue`) — never overwrites a good base with a shrunken/empty physical;
- **if the physical is empty and there is no larger archive → `fail LIVE_TARGET_EMPTY`** (no good base to
  archive or reuse; restore the base first);
- otherwise (physical healthy, ≥ archive) → archive as before.

Fail-closed: it can never replace a larger archive with a smaller physical. KA
`tests/test_installer_bareboot_guard.py` (6 tests) **extracts and runs the actual dir-branch code** against
mock trees: empty-physical + 3-file seq1 → REUSE, **seq1 bytes unchanged**; degraded (2<5) → REUSE;
healthy (5≥3) → normal archive; no-archive + empty → refuse; both-empty → refuse. Existing `ka_tests` 46/46
still green; installer `bash -n` clean.

## ③ For cx-bms — add a read-only assertion in `demo_seal_61b.py`, after bare boot, before the installer

Between `assert_no_binds()` / `installer-sha` and the `installer` run (≈`:242`–`:245`), assert the archived
base is complete and that the installer will not overwrite it:

1. `hdc -t 61b shell "find /data/westlake-demo/u13/sources/seq1 -type f | sed -n '$='"` → **== 246**
   (the signed `/system/android` bundle file count; bind the exact count — and ideally a manifest SHA — from
   the signed 319 baseline, not a literal).
2. `hdc -t 61b shell "find /system/android -type f | sed -n '$='"` → **0** (confirms the bare-boot
   bind-gone state, i.e. the installer's REUSE path will trigger and seq1 is the source of truth).
3. Therefore REQUIRE: `seq1_files == signed_count AND physical_files < seq1_files` → the guard reuses seq1;
   STOP otherwise (do not run the installer against a degraded/ambiguous base).

This makes the orchestrator refuse **before** any write if the base is not the known-good signed bundle,
complementing the installer's own fail-closed reuse. Both are needed: the assertion catches a bad base
early; the installer guard is the last line even if the assertion is skipped.

Hand to outer to land; 61b v1 seal window stays closed until this is in.
