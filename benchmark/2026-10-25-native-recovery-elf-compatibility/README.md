# T137 — static ELF compatibility: candidate.so vs rollback.so (2026-10-25)

Bounded static comparison via `llvm-readelf` (already installed; read-only). Inputs verified: `candidate.so` 2,154,616 B (SHA `3291f76d…`, manifest-matched), `rollback.so` 2,023,136 B (SHA `b0e5602a…`, the known T18 production bridge identity). Raw parser outputs persisted privately in `.private/t137-raw/`.

## Identical (no compatibility delta)

- **Arch/class/endian/type**: ELF64 / little-endian / AArch64 / DYN — identical.
- **SONAME**: `liboh_adapter_bridge.so` — identical.
- **DT_NEEDED**: 44 entries, byte-identical list — **no new library dependency**.
- **LOAD segments**: alignment & flags identical.

## Delta: undefined dynamic symbols (591 → 603, +12, none removed)

`_ZN4OHOS5Rosen21WindowSessionProperty13UnmarshallingERNS_6ParcelE`, `…SetSubWindowLevelEj`, `OHOS::Parcel::WriteUint8/ReadUint8`, `std::_h::mutex::try_lock`, `std::_h::thread::join`, `getegid/geteuid/getgid/getuid/lstat/open`.

**F1 (CORRECTED, unknown-pending):** identical DT_NEEDED proves only the dependency *list* is unchanged — it does **not** prove the 12 new UND symbols are exported by those libraries. Provider verification was attempted per outer instruction against the local build inputs (`$HOME/.local/share/westlake/wmc-baseline-build-20261024/`, `native-host-recovery-build-20261024/`): both directory reads → **Operation not permitted** (sandbox home-dir denial), so argv.json dependency paths and provider dynsym listings are unobtainable in this lane. **All 12 symbols are UNKNOWN-pending** (class-level expectations — Rosen/Parcel from libwm*/libipc_single, std::_h from libc++, uid/lstat/open from libc — are hypotheses, not verified facts). Per outer ruling this is **non-blocking** for the normal rollback-capable load verification; decisive resolution is provider dynsym from build inputs/61b image or the runtime load itself.

## Verdict

**No actionable compatibility blocker within scope; symbol-provider presence unresolved (12 × unknown).** Static pass ≠ device load success (runtime on 61b unverified). Candidate is 5-unit recompile + 103 reused objects, not a whole-library rebuild. B1/C1 not re-reviewed.

Files: `README.md`, `results.json`, `landing-paths.txt`. Not committed this round; outer collects/commits per the landing paths. Raw parse outputs remain private under `.private/t137-raw/`.
