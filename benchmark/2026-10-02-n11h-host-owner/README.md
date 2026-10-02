# N11h: publish resident host owners on the accepted r3 baseline

## What the old assumption got wrong

Using the U9 host `1d3b0881` as the experiment baseline would discard the promoting r3 resident-compat change. Publishing a second inheritance edge to the same parent would overwrite its first whitelist on OH 6.1, reproducing the U10 OrganicMaps regression. A first reproduction experiment also used a different source basename: prefix mapping did not rename `STT_FILE`, so that output was not accepted as a reproduced baseline.

**New rule:** reproduce accepted r3 bytes first; assemble each parent whitelist once; publish both owner edges before any fresh domain load; distinguish static coverage, unapproved gates and dynamic acceptance.

This is an **offline review candidate**, not a deployed generation or an approved window. Blueprint: `benchmark/2026-10-02-n11h-host-owner-blueprint/README.md`, master `475cb61692`, outer ACK(80) `2026-10-02T11:01:18+0800`. No board command, lock, U10.1/T8 mutation or single-owner/t20 claim is made.

## Byte identities and durable inputs

| Object | SHA256 |
| --- | --- |
| Accepted/promoting r3 baseline, reproduced twice | `65cc3535ebf22bdf664b3c8ddf932ccd7f42d936be1c861e1221a80b12a00284` |
| N11h host candidate, two identical fixed-path builds | `65ac50894de8d06e32439d2aee91f61eb1c45d6c0822826d529f671ca3c49aed` |
| r3 source snapshot | `507bf160dfae87851345c8fc564c9378356a773cc84272d2ec0635b1c0ef0c50` |
| Unchanged resident-compat header | `e4f7321547d6cafac5734a7ff3b9338cc0e8a93e94ff5932bafa3caa23cb35e0` |
| Frozen OH clang15 | `6a5ec84488cd11db8118fab8160affc40b90885f82481dbc31624f561f7b72a1` |
| Unchanged five-system-library/SoundPool-preserving policy | `0718f01e237d322b5a16a1858265f8cc05cddd5ddca6d1ceb28bcc33023913a9` |

The baseline is the **accepted/promoting r3**, not a claim that it is already live. `deployed_whois.py appspawn-x` still identifies signed U9 `1d3b0881`; its raw output is retained in `evidence/whois.txt`. The actual comparison file is explicitly pinned to the r3 promoting bundle, not selected by glob or by the whois default.

Artifacts are durable in `$WORKSPACES/westlake-harness-bms/benchmark/2026-10-02-n11h-host-owner/.artifacts/frozen-r1/`:

- `candidate/appspawn-x`, `baseline/appspawn-x`, compiled objects and dependencies.
- `build.log`: unfiltered compiler/linker output captured with `tee`; `--trace` records selected link inputs.
- `build-receipt.json`: all commands, two repeat identities, compiler/linker hashes and 132 input hashes.
- `input-files/<sha256>`: content-addressed byte copies of every recorded input, including compiler/linker, host source/header closure, reused stock objects, CRTs, shared link inputs and version script. Old stock objects are explicitly reused, not falsely described as rebuilt from this host patch.

Public source snapshots, generator and patch are in `inputs/`, `src/`, `n11h-owner.h`, `source.py`, `stock-host.patch`; `evidence/build-receipt.json` binds them. Baseline source/header log identities are recovered from the pinned ELF and prefix-mapped, so the old basename and `__FILE__` values survive without writing old inputs. New candidate paths are script-relative. The source snapshot and content-addressed inputs do not depend on an ephemeral build machine.

## Actual change and original permissions

Only `StockCreateConfiguredNamespaces` and `StockOpenNamespace` change in the original host translation unit; the new header supplies small owner helpers. All other source bytes, stock object identities, INET/security callbacks, service ABI and policy files remain unchanged. The audit composition verifies every other one of the 292 sealed package files against its original SHA.

`StockCreateConfiguredNamespaces` validates the original inputs/PID-owned names, gets `westlake.sealed.child`, and checks both canonical owners there with NOLOAD. Missing namespace/owner returns the existing typed result fence and a real-call log. These are **resident read probes**, before domain creation, not fresh application-view NOLOAD probes.

The new minimal owner whitelist is exactly `liboh_adapter_bridge.so:liboh_android_runtime.so`:

| Child / pre-existing branch | Single sealed-parent whitelist |
| --- | --- |
| bridge domain | The exact two owner names |
| ordinary app, compat in default/unavailable | The exact two owner names |
| ordinary app, verified compat owner is the same sealed namespace | The two owners plus the pre-existing `libbionic_compat.so` permission, merged once |
| Flutter/native private app, original sealed permission already exists | Original runtime/compat/log/libc++ names plus bridge, merged once |

The private app's original **12-name default whitelist**, including `libsurface.z.so`, `libstdc++.so` and `libOpenSLES.so`, is byte-preserved. Its existing app→bridge edge remains. Ordinary compat from verified default retains one separate default edge; unavailable/mismatching compat remains nonfatal. The resident-compat helper itself is unchanged and never inherits or probes application views.

Compat is now queried before bootstrap so its complete whitelist can be chosen for the single app→sealed call. This timing is a deliberate behavioral delta: a compat mapping created only by a later bootstrap would not be observed then. The owner premise is that it is already resident; failure still continues without a compat edge. Host replay covers sealed/default/missing/mismatched compat, but does **not** prove dynamic equivalence or that premise on a board.

Bridge bootstrap load, pthread-ops installation, runtime/audio publication and ABI promotion retain their old calls/guards, after domain sharing. Private sealed inheritance is ordered before private default inheritance to prioritize the resident owner; realized OH loader selection remains a window question.

`StockOpenNamespace` intercepts only these exact canonical paths:

- `/system/android/lib64/liboh_adapter_bridge.so`
- `/system/android/lib64/liboh_android_runtime.so`

It gets sealed and returns only a sealed `NOW|LOCAL|NOLOAD` handle. A bare owner SONAME or noncanonical path with either owner basename rejects; missing namespace/handle rejects without application/default/fresh fallback. Non-owner requests, including `libandroid.so`, retain the old application callback and mode/PID/input guards. Handles are caller-owned; preflight probe references are closed and no cached parent handle is introduced. `[N11h-HOST-OWNER]` records actual checks/inherits; `[N11h-HOST-OPEN]` records actual resident/reject decisions, not an inferred success banner.

## Static-first and ABI results

Raw listings: `evidence/open-r3.{txt,json}` and `evidence/open-candidate.{txt,json}`. Scanner SHA is pinned in the handoff; its namespace-edge extension was landed as `bbffc1336e`.

| Check | r3 | N11h |
| --- | ---: | ---: |
| Direct open sites | 8 | 11 |
| Listed namespace APIs | 17 | 19 |
| INHERIT-REPEAT | 0 | 0 |
| INHERIT-AFTER-OPEN, syntactic may-path | 4 | 0 |
| Dynamic exports | 15 | 15 |
| Removed / added / signature drift / consumer break | — | 0 / 0 / 0 / 0 |
| Common-function call-set changes | — | Only the two intended callbacks |

Two sealed edges are `bridge@0xd280`, `app@0xd3d4`, before the first fresh `StockCreateConfiguredNamespaces` load `0xd4d0`. The three new direct sites are `StockOpenNamespace@0xda24` and two inlined owner checks `N11hCheckOwners@0xdb38/0xdba0`; all are NOLOAD. Old generic open, main default NOLOAD and two compat probes remain; runtime/audio/ABI calls remain with relocated PCs.

`StockOpenNamespace@0xda24` has an unresolved `csinc` path expression in the scanner; source/real-callback tests bound it to the two canonical owner paths. The scanner does not recover the ordinary sealed-compat three-name alternative at `0xd3d4`; the source branch and C replay retain it explicitly. These are bounded resolver limits, not deleted uncertainty. JSON findings retain `DEFAULT-NS`, both generic `UNRESOLVED` rows and runtime `MULTI-NS possible` verbatim. The preserved private runtime publication is still a potentially fresh application load; inheritance alone is **not** proof that it reuses the resident owner.

### All four r3 after-open may-paths

| r3 open → inherit | N11h open → relocated inherit | Result |
| --- | --- | --- |
| runtime `0xd13c` → app→bridge `0xcfc8` | `0xd640` → `0xd464` | Inherit now dominates fresh loads; no returning path reaches it |
| audio `0xd1dc` → app→bridge `0xcfc8` | `0xd6e4` → `0xd464` | Same reordering; no returning path |
| runtime `0xd13c` → optional compat `0xcffc` | `0xd640` → `0xd480` | Optional edge selected before bootstrap/runtime/audio; no returning path |
| audio `0xd1dc` → optional compat `0xcffc` | `0xd6e4` → `0xd480` | Same; original native-private branch does not request ordinary compat, but old syntactic may-path is not waived on that basis |

These four old CFG results are explicitly compared, not suppressed by PC order or an exception. The candidate has no after-open findings. Replacement-inheritance replay additionally asserts no repeated `(child,parent)` and no fresh load before both new owner edges for ordinary/private paths.

`abi_diff --calls --consumer …` scans **102 payload DSO copies / 86 distinct identities**, normalizes symbol versions, and reports zero breaks. All common functions outside the two callbacks have zero call-set differences. Callback/service tables have **352 bytes / 35 relocations** with equal scalar bytes and resolved pointer/string meanings; ordered NEEDED/SONAME/search/flags/init-array sizes are unchanged. Export/UND checks do not prove indirect callback behavior, so both actual callbacks also run in C fixtures.

### Raw strings failure is not hidden

`deployed_strings_diff` exits **1**, with **3 dropped / 16 added** (`evidence/strings.txt`):

- Drops: two old absolute `__FILE__` log identities and the original four-name sealed whitelist.
- Adds: replacement script-relative source/header identities, the canonical bridge path, owner basenames, minimal/two merged whitelist variants, actual-call log templates and `resident`/`reject` labels.
- The old four permissions remain in the new five-name private union. All other original rodata strings survive; all 352 relro bytes normalize identically. These exact differences need outer review, not an arbitrary strings waiver.

No JAR is modified, so `deployed_class_diff --frozen` is not applicable.

## N1/N2: raw reject, no exception transplant

`audit.py` creates an **offline-only byte copy**, with `rollout_ready=false`, of the r3 native composition and substitutes only the host. It updates artifact/source hashes and profile bindings and adds the new header's namespace profile. It does not mutate any source bundle, issue a deploy command or pretend to be a coordinator-approved generation.

| Raw canonical native-predeploy check | r3 composition | N11h audit copy |
| --- | ---: | ---: |
| Exit | 0 | 1 |
| N1 rejected / excepted | 0 / 53 | 54 / 0 |
| N2 rejected / excepted | 0 / 103 | 103 / 0 |

The first raw r3 invocation rejected all 156 historical items because the canonical registry had no matching rows. Outer ACK(90) `2026-10-02T13:19:17+0800` then recorded the omission and appended those rows in master `28682ccd25`. The handoff refreshes against that registry: **r3 PASS with 53 N1 / 103 N2 exact exceptions; N11h still REJECT with zero exceptions**. The original 53 N1 observations remain (host unknown, runtime/registration bounded unknowns/unresolved calls and child finding). New item: `n11h-resident-owners/N11hResidentHandle`, line 29, parameter target and pre-existing namespace not proven by N1's source-order checker. It is retained as REJECT, not self-approved. This one source-level site corresponds to three compiler-emitted NOLOAD sites.

N2's full details **and finding bodies are byte-equivalent as JSON values** between baseline and candidate: no domain/DSO/NEEDED/search/permitted/closure change, no inherit used. Its 103 existing closure findings are not new N11h breakage or silently passed. All issue IDs still change with manifest/input binding; old approval must not be copied to a new package identity.

Complete raw tool JSON is durable under `.artifacts/gates/native-{r3,candidate}.txt`; portable copies are `evidence/native-{r3,candidate}.txt`. The exact new issue and raw SHA are in those files. Outer/coordinator must review/rebind N1/N2 exceptions, approve exact static delta/strings differences and perform final package/child/boot/policy identity checks before any window. **Current rollout readiness is false.**

## Replay and reproduction

`test_namespace.c` compiles the actual candidate helpers, predicates, guards and both callbacks, replacing only platform effects. The fake OH loader enforces replacement (not union) semantics and checks every `(child,parent)` is called once. Cases cover ordinary/native/Flutter/audio paths, three compat availability states plus mismatch, missing owners, namespace/create/inherit/load/bootstrap failures, pthread installation, no-bridge inputs, exact/alias/non-owner routing and guard rejections. This is host behavior evidence, not real OH linker equivalence or screenshot acceptance.

Run from repository root:

```sh
set -o pipefail
python3 benchmark/2026-10-02-n11h-host-owner/build.py 2>&1 | tee benchmark/2026-10-02-n11h-host-owner/.artifacts/frozen-r1/build.log
python3 benchmark/2026-10-02-n11h-host-owner/audit.py 2>&1 | tee benchmark/2026-10-02-n11h-host-owner/.artifacts/gates/audit.log
python3 benchmark/2026-10-02-n11h-host-owner/archive.py
python3 benchmark/2026-10-02-n11h-host-owner/test_candidate.py
cargo test --manifest-path tools/spec-checks/Cargo.toml --test n11h_host_owner
python3 scripts/lab/land.py "$PWD" benchmark/2026-10-02-n11h-host-owner/landing-paths.txt -m x --preflight
```

`audit.py` succeeds only when the declared raw reject/ABI/static comparisons are preserved; its success is **not** N1/N2 PASS. Public evidence replaces only local repository/workspaces prefixes with `$REPO`/`$WORKSPACES`; `raw-index.json` gives original/portable hashes, and unmodified raw outputs remain durable. Board ACK includes original open-site/strings/ABI/audit/preflight output and anchors to the full N1/N2 JSON. Large ELF/toolchain/source-input bytes stay in persistent `.artifacts`, not Git. Landing is performed by the outer loop; the unrelated staged set is untouched.
