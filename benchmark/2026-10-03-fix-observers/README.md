# Fix-observer matrix v3 — SHA-prefix + smoke-marker matching, final gaps (2026-10-03, report-only)

`scripts/lab/check_fix_observers.py` v3 (+7/7 unit tests). Matching now has four channels
(outer 11:10's mapping), in order:

1. **Token match** — a per_key source naming a deliverable token (as before).
2. **SHA-prefix match** — a per_key source naming a 6-12-hex SHA prefix observes every
   increments row whose baseline/candidate sha256 starts with it (e.g. vlc/fennec's `f8619ad5`
   → the native-ABI artifacts; mcdonalds/im-vector same SHA; toutiao's ICU-74 alias shim;
   fd-plus's stubs `87cf65cc` → the stubs JAR, and via the derived rule all 16 BCP boot images).
3. **Smoke markers** — the U14 stage-A window-1 smoke proposals (master bfb9c2a695) are read
   with `--smoke`: `probe.files` path+SHA pins observe their artifacts (liboh_adapter_bridge,
   libicu74compat, boot.art/boot.oat, ...); `fixes[].id` names map to artifacts
   (U14-BRIDGE-M5/M6 → liboh_adapter_bridge.so, U14-RUNTIME-BIND-ORDER / [B8-AMB-ORDER] →
   oh-adapter-runtime.jar 0349, U14-FLUTTER-EGL → flutter libandroid fff9).
4. **Derived-image rule** (v2) — boot images derive from their source JAR; the combined
   boot.art/boot.oat derives from any observed JAR in the increments.

## Final counts (verbatim from the runs)

- **U14 v5 keys vs U14 increments + smoke proposals: 56 artifacts, 0 without an observer** ✅
  (the 11:10 outer mapping is reproduced: M5/M6 markers observe liboh_adapter_bridge.so,
  [B8-AMB-ORDER] observes oh-adapter-runtime.jar, Flutter ANW observes libandroid, SHA-prefixes
  cover the native-ABI trio and the ICU shim, and the stubs JAR covers the 16 BCP images).
- **U15 keys vs U15 increments (no U15 smoke proposals yet): 56 artifacts, 2 without an
  observer** — `libapp_native_loader.so` ×2 (system + route-a sealed copy), kept pending
  cx-bms's answer on which fix it carries (outer 11:04).

## Repro

    SM="$WORKSPACES/westlake-harness/benchmark/2026-10-03-u14-stage-a-plan/window1"
    python3 scripts/lab/check_fix_observers.py \
        $WORKSPACES/westlake-harness/benchmark/2026-10-03-u14-on-u13-base/increments.csv \
        benchmark/2026-10-03-u14-observation-keys/u14-stage-a-keys.json \
        --smoke $SM/common/smoke-5ea-proposal.json $SM/common/smoke-5cd-proposal.json \
                $SM/61b/smoke-61b-proposal.json --csv u14-matrix.csv
    python3 scripts/lab/check_fix_observers.py \
        $WORKSPACES/westlake-harness/benchmark/2026-10-03-u15-on-u14-base/increments.csv \
        benchmark/2026-10-03-u15-observation-keys/u15-stage-a-keys.json --csv u15-matrix.csv
    python3 scripts/lab/tests/test_check_fix_observers.py    # 7/7 OK
