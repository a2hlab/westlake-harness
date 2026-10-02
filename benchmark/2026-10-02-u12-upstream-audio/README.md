# U12 upstream audio: verified transplant primitives, not working playback

## Correction and status

The four requested upstream commits do **not** repair the pinned OH05d8 PLAY
callback rejection by themselves. c7d2992 forwards RegisterCallback at872–877
and SetCallbackEventsMask at879 to OH. Both actual owner vtable entries return12.
Its identifier comparisons also compare OH24 bytes with Android16, not equivalent
UUID layouts. Do not equate an upstream ledger fix with a route-A unlock.

**Real PLAY completion and route-A media owner registration are incomplete.**
This first delivery implements verifiable width/IID/continuous-queue primitives
plus a negative control. `execution_enabled=false`, no device access, no current
bundle changes, and **no candidate admission**. Completion design/minimal work
continues separately after this first delivery, as requested.

## Four commits versus our architecture

Full revisions, git-show patches/stat output, exact source snapshots and hashes
are in `architecture.json`, `upstream/` and `evidence/commit-*`/`patch-*`.
The local current checkout HEAD is not assumed to contain these historical files.

| Upstream revision | Original mechanism | Route-A mapping; reuse versus adaptation |
|---|---|---|
| 0b5c9af4cec9bab0828a1a95e6027d4a4b54cdbe | preloaded webview_bionic_shim interposes slCreateEngine; Android32→OH64 wrappers, locator/PCM and required arrays; OH pull queue→Android push callbacks | data/queue algorithms reusable; original preloaded-shim owner and bare dlopen cannot be copied into our namespaced facade; it still delegates PLAY |
| 1e981623b2a1387fdf57cce777b677fe24554791 | per-object Android configuration hints; canonicalize app IDs to OH own ID addresses by contents | configuration storage reusable but values are not applied to OH audio policy; raw IID comparison must be rewritten16↔24 field-by-field |
| c7d29921d5a39057ba3c2c2c4dccbd1b391bedc3 | refill each OH buffer after Android consumption callbacks; caller-address dlopen routing to shim itself plus a real OH dependency | refill loop reusable and fixture-tested; shim-self NOLOAD and caller classification do not prove route-A ns visibility and cannot be copied as a new default owner; facade resident backend injection/publication needed |
| 5ae6b7547407ca343565fc3ccf650be704f74e19 | libwl_missing_natives JNI_OnLoad binds MediaPlayer49 and missing AudioTrack/AudioSystem methods; AVPlayer callbacks/data-source/invoke | route-A ac59 already registers MediaPlayer49 stubs; blindly loading another missing-natives DSO can overwrite ownership/caches. Port method bodies only after exact current JAR signature and one registration-owner design; backend AVPlayer libraries/namespace availability remain unverified |

Upstream framework68 plus preloaded shim/extra missing-natives architecture is
**not** our route-A bridge/sealed-owner and SystemLoader architecture. In our
recorded current payload, WHOIS finds only Android facade5891 (four exports,
no engine, DT_NEEDED libc) and runtimeac59. The OH05d8 implementation is an
independently pinned system-library snapshot, not the facade. U9 maps show
runtime in168 processes and no facade mapping; these are historical maps,
not current live residency. A media_jni logical alias to resident runtime moves
an alias wall, not the 49 stub method bodies. No media JAR/runtime is changed here.

## Verifiable transplant candidate

Candidate **0e9b211e3debd1443ab5aa9eab14fcbca0098150b1b4e71b9a8845c60ea3a020**,
two byte-identical builds, source recipe `stage.py` plus retained upstream snapshot:

- Android extension identifiers use explicit16-byte structures. Compare Android
  fields against OH24 fields, reject nonzero high32 time_low, retain exact canonical
  OH pointer. No raw24-byte memcmp against an Android16 object.
- Original PCM28→OH56 and object output64→temporary→Android32 paths retained;
  fixture executes actual candidate functions and checks an output canary.
- Original c7 continuous refill preserved: four callback-refilled2-byte packets
  fill one8-byte OH request, no periodic silence; empty queue pads silence.
- No bare backend dlopen. Explicit U12BindOpenSLESResidentOwner takes a pre-existing
  handle and validates slCreateEngine's exact `/system/lib64/libOpenSLES.so` identity
  plus required IDs. Missing/wrong owner refuses binding, never fresh-loads.

The injected-handle entry has **no caller/publication implementation yet**. Its
precondition is serialized setup before any engine/queue threads and a separately
attested resident backend; pathname alone is not content-SHA/single-copy proof.
Do not install this DSO just because its direct open-site count is zero.

Original unsupported/unknown interface fallback and PCM_EX representation handling
are not admitted as complete Android ABI coverage. Configuration hints are stored,
not actual OH policy. Consumer imports are not proof of which vtable methods run.

`test_adapter.c` executes candidate code with an explicit local owner-method fixture:
positive IID/PCM/state/queue results and **negative PLAY RegisterCallback/mask=12**.
This is host ABI/algorithm proof, not OH audio, hardware completion or owner binding.
OH OnWriteData is a data request; a queue callback after app bytes are copied into
an OH buffer must not be relabeled PLAY HEADATEND or proof of audible playback.

## Static gates: preserve rejection

- open_site_scan deployed vs candidate: zero candidate direct opens/edges/findings;
  indirect injected-handle availability remains unproved.
- ABI4→6: only slCreateEngine and U12BindOpenSLESResidentOwner added; no removals,
  drift, call-set changes or broken removed exports in **seven real ARM64 ELF
  samples** spanning nine recorded copies/seven corpus keys.
- deployed_strings_diff **exit1: two dropped,73 added**. UUID-byte fragments changed
  with IID layout; canonical ID table/config/translation logs account for additions.
  `strings-review.json` maps literal source lines or explicitly labels byte fragments;
  every allowance remains **outer-review required**, no generic allowlist applied.
- N1/N2 run on a470MiB local-only copy of the exact current292-file package,
  replacing only root facade and adding its source profile. Baseline PASS with53
  N1/103 N2 exceptions; new manifest175fd375 REJECT with53/103 unrebound historical
  findings. New source profile findings0; N2 details/findings otherwise identical.
  This is not GATE PASS and no exception registry is edited.

Source/toolchain/frozen SLES headers/build commands and persistent ELF/raw outputs
are in `build-receipt.json`, `namespace-gates.json` and `.artifacts/`. SLES width
assumptions are checked against05d8 binary evidence retained by the U11 profile,
not inferred from a different DevEco header version. No large ELF/package in Git.

## Predictions and ledger controls

Existing166 input consumer scan finds seven exposed keys: fd-libre, fd-minetest,
fd-mpv, fd-stk, mindustry, ppsspp, toutiao; seven distinct ELF/nine copied members.
Only Mindustry has the pinned PLAY RegisterCallback/mask call-site profile (libarc
03275660,0xa2290/0xa22a4), a **conditional later wall**, not a proved current
first-fatal reached in this phase. Its facade has no engine yet. This first delivery
does not fix its true PLAY completion. Other six indirect-method profiles unknown.
Expected first-fatal movement and new t20 lights from this unintegrated candidate:
**none supported**, not a blanket forecast that the portable algorithms have no value.

Historical ledger controls include Mindustry0b5, Ball2Box/Jigsaw/V3/DuckRun1e98162,
RhythmEngine/canonical-IDs/continuous-fill c7d2992, ntfy/DoorsOfDoom/media-native
5ae6b75 and upstream `game` (the supplied Astro Loop name must not be inferred from
that key without its manifest). These are different corpus identities; full ledger
rows are included but not counted as166-input beneficiaries or this batch lighting.

## Reproduction and review

```sh
python3 benchmark/2026-10-02-u12-upstream-audio/collect.py
python3 benchmark/2026-10-02-u12-upstream-audio/namespace_gates.py
python3 benchmark/2026-10-02-u12-upstream-audio/test_audio.py
cargo test --manifest-path tools/spec-checks/Cargo.toml --test u12_upstream_audio
```

Python6/Rust3/three contract scenarios run; `evidence/preflight.txt` is the land
preflight. Root README/DIGEST landing is additive via documentation.json.
The primitive test compiles the committed candidate and frozen headers inside a
temporary directory on every invocation; no `.artifacts` executable is required.
Clang compile/run failures fail the test rather than silently skipping coverage.
Next work first freezes observation-limited completion predictions, then designs
and implements true callback semantics without treating OnWriteData as presentation.
