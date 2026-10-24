# T137 — static ELF compatibility: candidate.so vs rollback.so (2026-10-25)

Bounded static comparison via `llvm-readelf` (already installed; read-only). Inputs verified: `candidate.so` 2,154,616 B (SHA `3291f76d…`, manifest-matched), `rollback.so` 2,023,136 B (SHA `b0e5602a…`, the known T18 production bridge identity). Raw parser outputs persisted privately in `.private/t137-raw/`.

## Identical (no compatibility delta)

- **Arch/class/endian/type**: ELF64 / little-endian / AArch64 / DYN — identical.
- **SONAME**: `liboh_adapter_bridge.so` — identical.
- **DT_NEEDED**: 44 entries, byte-identical list — **no new library dependency**.
- **LOAD segments**: alignment & flags identical.

## Delta: undefined dynamic symbols (591 → 603, +12, none removed)

`_ZN4OHOS5Rosen21WindowSessionProperty13UnmarshallingERNS_6ParcelE`, `…SetSubWindowLevelEj`, `OHOS::Parcel::WriteUint8/ReadUint8`, `std::_h::mutex::try_lock`, `std::_h::thread::join`, `getegid/geteuid/getgid/getuid/lstat/open`.

**F1 (final, build-input provider table):** outer supplied the actual candidate-link providers (`.private/t137-provider-input/`, 5/5 SHA verified). `llvm-readelf --dyn-symbols` per provider, matching names modulo `@@VER` suffixes: **12/12 verified defined** in the candidate's own declared dependencies as built: `std::_h::mutex::try_lock`, `std::_h::thread::join` in `libc++.so`; `getegid/geteuid/getgid/getuid/lstat/open` in `libc.so`; the Rosen/Parcel four above in `libwindow_scene_common.z.so` / `libutils.z.so`. **4/12 RESOLVED by the full 44-lib link set**: `WindowSessionProperty::Unmarshalling` & `::SetSubWindowLevel` → defined in `libwindow_scene_common.z.so`; `Parcel::WriteUint8`/`::ReadUint8` → defined in `libutils.z.so` — both already in the candidate's DT_NEEDED list. **12/12 now provider-verified in the actual link inputs.** This is build-input evidence, **not** current-61b-export proof and **not** a missing-dependency finding — the four may come from another already-needed lib variant on the device image. Non-blocking for the rollback-capable load verification; if a loader error names one of the four, this provider set is the first place to extend.

## Verdict

**No actionable compatibility blocker within scope; symbol-provider presence unresolved (12 × unknown).** Static pass ≠ device load success (runtime on 61b unverified). Candidate is 5-unit recompile + 103 reused objects, not a whole-library rebuild. B1/C1 not re-reviewed.

Files: `README.md`, `results.json`, `landing-paths.txt`. Not committed this round; outer collects/commits per the landing paths. Raw parse outputs remain private under `.private/t137-raw/`.
