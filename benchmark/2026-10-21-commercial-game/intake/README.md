# COMMERCIAL-G01 — Genshin exact-input intake (status: MISSING in searched scope; macserver INACCESSIBLE)

Contract: `specs/commercial-game-round1/t1-input-discovery.spec.md` (dispatched @ `fb08522d6`, updated @ `8189ec8d7`
install-set / startup-assets / full-content tiers). Runtime verdict: **NOT_TESTED**. Device ops: 0 (no HDC/ADB).
No download, install, login, package execution or REA. Elapsed: see `results.json.elapsed` (budget 900 s).

## What was wrong first (kept)

- The prior GENSHIN-T1 intake searched only local **filenames** and never read package identities of the 441 APK/XAPK entries, so a
  renamed package would have been missed. This round read 393 APK AndroidManifests and 48 XAPK container metadata records; the 48 embedded APK manifests remain unexamined.
- cc-video opened two **whole-disk** name finds (`r02` hw248 `/`, `r06` a2hlab `/` as root) — this violates the
  contract ("不扫整盘"). Both were stopped on outer correction (TaskStop + pkill), rc unknown, partial stdout kept,
  classed `CANCELLED_OVER_SCOPE`, not counted as coverage. `r01` (non-root a2hlab rootfs `-xdev` name find) did
  complete rc0 but is also over-scope and is kept as `OVER_SCOPE_KEPT`, not counted.

Rule set by this round: remote discovery searches only the input/artifact roots named in `env.md` /
`OPS-RUNBOOK.md` / `infra/demo-artifact-cache.json`, non-root, `maxdepth`-bounded, names only.

## Result by source

| Source (alias) | State | Receipt | Observation |
|---|---|---|---|
| local APK stores (reused GENSHIN-T1 s08 list, SHA `07237009`), layer 1: 393 `.apk` | MISSING | c01 | `aapt2 dump badging` of each APK's own binary `AndroidManifest.xml`: 0 parse failures, 117 distinct packages, no `com.miHoYo.*` / genshin / hoyo |
| same stores, layer 2: 48 `.xapk` | MISSING (container claim only) | c01 | `manifest.json` packer metadata: 45 distinct packages, none miHoYo. **Boundary:** this is container metadata, not the embedded base APK manifest, which was **not read**; a mislabelled container is not excluded |
| local names + text indexes | MISSING | GENSHIN-T1 s03/s04/s07 (reused, not rerun) | — |
| a2hlab `~/a2hlab/ws/inputs` | MISSING | r07 | toolchain dirs only, no apk/xapk/apks/obb |
| hw248 documented artifact/input roots (`westlake-artifacts`, `*-inputs`, boat-v2 inputs, final61b-game) | MISSING | r08, r09 | 0 package files, 0 name matches (maxdepth 6) |
| hw248 linux_cache root from `demo-artifact-cache.json` | MISSING_ROOT | r08 | directory absent (r08 rc 2 for this reason only) |
| hw248 `LAB_STATE_DIR` mirror | NOT_SEARCHED | — | env.md: name given by operator |
| macserver (documented route; owner doc says emulator + Genshin live there) | **INACCESSIBLE** | r03 | existing ssh config, BatchMode: remote closed connection, rc 255 |
| macserver primary artifact store | INACCESSIBLE | (r03 host) | — |
| `mac-server-128` alias | INACCESSIBLE | r04 | rc 255 |
| macserver emulator userdata (installed Genshin) | INACCESSIBLE | — | host unreachable; pulling an installed app would need ADB (forbidden here) |
| rest of `$HOME`, other hosts | NOT_SEARCHED | — | — |

No claim of global absence. Tiers: install-set **MISSING**; startup-assets / full-content **UNKNOWN** (no base to
derive them from). `input-index.json` has empty inputs and `install_command: null`. Every Genshin dimension
(versionCode, signer, splitName/uses-split, ABI, SDK) is UNKNOWN. Small-app smoke results are not Genshin admission.

Known tool defect (kept, not rewritten): `pkgnames.py`'s `split` field is always null because aapt2 reports
`split=` inside the `package:` line; the split name is still present verbatim in `package_line`.

## Next action

Outer loop selects an **official** acquisition source for the `com.miHoYo.Yuanshen` install set (base + every split,
plus OBB/startup assets if present) into a private dir; fixing the macserver route is not a prerequisite. Then rerun
G01 manifest / signer / split reads on exact SHAs. Optional bounded follow-ups: hw248 `LAB_STATE_DIR` mirror if its
name is supplied; the 48 XAPK embedded base manifests if the reviewer wants layer 2 closed. No device task proposed.

## Reproduce

`tools/` holds the reproducible sources (no credentials, no user-bound paths; private root via
`COMMERCIAL_G01_PRIVATE`, default `$HOME/.local/share/westlake/commercial-game-20261021/intake`):

- `rec.sh` — receipt recorder (argv/rc/stdout/stderr/start/end); differs from the private original `05ce4640` only
  in the parameterized root.
- `pkgnames.py` — byte-identical to the private original (`d8e70583`) that produced c01;
  `python3 -I tools/pkgnames.py <aapt2> <list>`.
- `gen.py` — output generator; private original `5a23a9a0` kept unchanged. Public version adds the root env var,
  `-p <port>` aliasing (no literal port), the two evidence layers, `tool_sources` and the official-source next_action.
  Outputs were regenerated with the original start/end epochs; `results.json.tool_sources` records both hashes.

## Files

`results.json` (status, scope, elapsed, limits, unknowns, tiers, next_action, 10 command receipts with aliased argv,
rc, class, note, sha256/size raw_refs), `input-index.json`, `source-index.json`, `local-package-summary.json`.
Raw argv/rc/stdout/stderr (exact, unaliased) live in `$COMMERCIAL_G01_PRIVATE/raw/`
(`$HOME/.local/share/westlake/commercial-game-20261021/intake/`). Check: `cargo test --test commercial_game_intake`
in `tools/spec-checks` (receipt shape only; review is human).
