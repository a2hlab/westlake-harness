# U12 JAR layer, ready for one board round: minimal stubs (S1+S2) + FZ-005 boot-image re-bake + T8's four gates

#90, offline, no board. The outer reviewed U12 r2 (`2026-10-02-u12-java-walls`) and asked for two changes:

1. Drop the 8 `android.net` classes (138 members) from the stubs. They are predicted to move 0 first fatals, so U12
   stubs carries only **S1** (`TelephonyFrameworkInitializer.getTelephonyServiceManager()` + field) and **S2**
   (`com.android.internal.util.Predicate`). Runtime `0482c9b1` is unchanged.
2. Bake the boot image that a boot-class-path jar change requires, with the FZ-005 frozen tools.
   - The dex2oat output is teed **at run time** (AGENTS line 16; T8 had no bake log).
   - Bake twice and compare all 27 files.
   - Run T8's four gates.

**Result: U12 stubs `615b8bbe`, image run 1, all gates PASS.** The two bakes are identical except boot.art's
registered 3-byte backtrace field. The candidate list is `candidate.json` / `candidate-image.csv`. The outer
merges it with the U12 native layer.

## What was wrong before

- **U12 r2 stubs `00b30467` carried 140 added members** (138 `android.net` + S1 + S2). The 138 have no predicted
  key, and every extra variable makes a regression harder to bisect. That jar is **superseded, not a
  candidate**; neither was r1's `3a12918a`.
- **T8's effective re-bake kept no execution log.** Its paired receipt had to be re-run after the fact. This round:
  - every dex2oat invocation goes through `bake/dex2oat64-tee.sh`, which runs the frozen binary by its absolute path,
    so the `dex2oat-cmdline` the image embeds is unchanged, and tees its full stdout+stderr while it runs;
  - the whole bake session is also teed live on the Mac side.

## Stubs: `build_stubs_min.py`

- Base: the unified state's `adapter-mainline-stubs.jar` `2f365a75` (v3 bundle, the framework/ overlay copy the
  boards run).
- Merge: only `../2026-10-02-u12-java-walls/stubs/` (donor S1/S2 + `members.tsv`), through
  `../2026-10-02-android-net-stub-members/merge_smali.py`. Report: "merged 2 member(s) into 1 deployed class(es);
  1 new class(es)".
- Toolchain: the same pinned one (JDK ≥ 11 javac, d8 37.0.0, baksmali/smali 2.5.2 + jcommander-1.64, `smali -j 1`,
  fixed zip time). Built twice → `615b8bbecaa7…`, deterministic, and the same SHA from a bare `PATH`.

`gates/class-diff-stubs-u12.txt`, output lines verbatim (command lines omitted):

```
deployed  $WORKSPACES/westlake-inputs/generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle/framework/adapter-mainline-stubs.jar  (2f365a75581b, 265 classes)
candidate benchmark/2026-10-02-u12-jar-r2-bake/build/adapter-mainline-stubs-u12.jar  (615b8bbecaa7, 266 classes)
0 dropped, 0 reshaped, 0 added (after allow lists), 0 frozen class(es) broken
rc=0
265 deployed classes, 1896 deployed members, 0 changed; 2 member(s) added to deployed classes, 1 class(es) added
rc=0
frozen: 8 entries, 0 checked, 0 violation(s)
rc=0
```

The only allowed add is `Lcom/android/internal/util/Predicate;`. The outer's earlier runtime check
(`deployed_class_diff --deployed` against the 318 copy `5ae3dd29`) still stands, because the runtime did not change.

## Bake (hw248, FZ-005 tools)

- Tools: dex2oat64 `ae865ddd` (`$HOME/aosp-14.0.0_r1-art/out/host/linux-x86/bin/dex2oat64`) driven by
  `t5_gen_image.sh` `14b1f709`. Their SHAs are printed at the head of every session log.
- Inputs: T8's `jars9` (`t8-rebake-effective/jars9`), with only `adapter-mainline-stubs.jar` replaced by
  `615b8bbe`. The other 8 jars are `cmp`-identical to T8's. BCP order: core-oj, core-libart, core-icu4j, okhttp,
  bouncycastle, apache-xml, adapter-mainline-stubs, framework, oh-adapter-framework.
- Both runs used the same `--work` path, so the cmdline strings in the image match.
- `bake/bake_u12.sh N` produced runs 1 and 2: 2026-10-02 19:14 and 19:15. dex2oat rc=0 in both, 666 log lines each.

**t5's own rc is 6 in both runs, and that is expected:**
- t5's L1 check compares against the `--ref` list, which here is the board image.
- It reports "vdex 8/9". The one vdex that differs is `boot-adapter-mainline-stubs.vdex`, the segment this round
  changes on purpose.
- t5 is frozen and was not edited. The decision rests on the gates below.

**Logs and products** (persistent, `$WORKSPACES/westlake-inputs/generations/u12r2-v1/bake/`; SHAs in
`gates/bake-receipt.json`):

| file | what |
|---|---|
| `logs/bake-run{1,2}.session.log` | whole session, teed live (tool SHAs, t5 output, product SHAs) |
| `logs/dex2oat-run{1,2}.log` | full dex2oat stdout+stderr, teed on hw248 while it ran; ends `[dex2oat64-tee] rc=0` |
| `logs/image-sha256-run{1,2}.txt` | 27 SHAs per run (copies in `bake/`) |
| `run1/`, `run2/` | the images; run 1 is the candidate |

The bake work directory is also staged on hw248 at `$HOME/u12r2-bake/`. `bake/` here holds the repo copies of the
two scripts; they differ from the run copies only by writing the hw248 home prefix as `$HOME/`. It also holds
`t5-ref-u12.sha256` and `jar-sha256.txt`.

## Gates (T8's, unchanged)

| gate | command / reference | result |
|---|---|---|
| repro, 2 bakes | `compare_runs.py`; exception read from `knowledge/gates/image-provenance-exceptions.json` | **PASS**: 26 identical; boot.art differs only at 0x3e3b9–0x3e3bb, inside T7D-REPRO-BACKTRACE-001 `[0x3e3b8, 0x3e3c0)`; 0 other |
| rb | `check_boot_oat_rb.py` | **PASS**: oat 230, concurrent-copying=false (read barrier off, = board R155), image 108 |
| t4b | `t4b_build_switch_gate.py`, libart `59e1bb45`, boot.oat run 1, `evidence/U12-BUILD-snapshot.md` | **pass**, `deploy_allowed: true` |
| G1 | `image_predeploy_gate.py`; reference = board image (`t8-rebake-effective/image`) and its jars9; `--swap adapter-mainline-stubs` | **PASS**: every segment checksum matches the jars in effect; stubs `0xadb12041` (new) vs `0x2bce588e` = the declared swap |
| G2 | same, `oatdump_remote.sh` on hw248 | **PASS**: `String#hashCode` 36 insns cand = ref (explicit suspend-check shape) |

Versus the board image, 16 files are byte-identical and 11 differ:
- the three stubs files;
- the `.art` of core-oj (`boot.art`), core-libart, core-icu4j, framework and oh-adapter-framework;
- `boot.oat`, `boot-framework.oat` and `boot-oh-adapter-framework.oat`.

All vdex except the stubs one are identical, so every other jar's dex content is unchanged. The other `.art`/`.oat`
differences are image layout and offsets shifting around the new stubs segment, and G1 confirms the checksums.

## The candidate (`candidate.json`, `candidate-image.csv`; also `u12r2-v1/candidate.json`)

| target | U12 | board now |
|---|---|---|
| `/system/android/framework/oh-adapter-runtime.jar` | `0482c9b13fbc6ab5bce3902807eb7972736463b772773fde276cae679ce9bd4f` | `5ae3dd29d45c…` |
| `/system/android/framework/adapter-mainline-stubs.jar` | `615b8bbecaa7b07fa27d40d25bd13eb6dfb33e6ec6bc7660bc2fc9aeaff1e610` | `2f365a75581b…` |
| `/system/android/framework/arm64/` 27 files | `u12r2-v1/bake/run1/`; 11 changed (below), 16 = board | T8 effective image |

Changed image files (U12 run 1):

| file | sha256 |
|---|---|
| boot.art | `02fd9590279a4bd9a945e1b8f57d3847e7280190d76cd5bae7c28e4df3038967` |
| boot.oat | `6ec1a4c0cce68a845943187de4bf9dc9e337a6482431e6d4bff0a55d0abca907` |
| boot-adapter-mainline-stubs.art | `9575e74d8be5a84204b8772e8f6414c5ffc4b7bdbe874e3016f8ed78ab1d3593` |
| boot-adapter-mainline-stubs.oat | `338d02ea8ac55ae961931be9c6d19dbb1482cec8cad82f8232947e84951ccbe1` |
| boot-adapter-mainline-stubs.vdex | `86d3baa00e912200896c27e48116967263409ef214a5581817ba0e091e85b4f5` |
| boot-core-icu4j.art | `d676307aba8a55873cfbbb548ff37ab8ac4f12e331510f8b011c1b18109d96ea` |
| boot-core-libart.art | `a7644e4753c5d50f6f2f6c9e02f792b6036f4eae094fa39c4ec0e35df13b4aac` |
| boot-framework.art | `a7734e99c6820afb9d2e37b757283bd39ac6bfe009fc6c68969146b008f28022` |
| boot-framework.oat | `d9d788f6b0bdbb414b82b3d90fbcedc3bbb1ec805f5b9717c39da957d96602fc` |
| boot-oh-adapter-framework.art | `3c8cacd7bdd326dea54223319a8adfa74b3d103d9907c5a6f339066d32fcb699` |
| boot-oh-adapter-framework.oat | `fc433c0789b5672976bcde7077f9816a59745293b8ef590fdce1aa654a7534ad` |

**Deploy rules:**
- The runtime is a single-file replacement: it is loaded by the runtime PathClassLoader and is not on the boot class
  path.
- The stubs and the 27-file image go together or not at all (the G1 swap).
- The other 8 boot jars stay as the board has them (`candidate.json` `unchanged_boot_jars`). That includes framework
  `3e106350` and oh-adapter-framework `2257b835`.
- The libart is not touched. The outer combines this with the U12 native layer (ICU `1e206531`, libmediandk
  `8fc0752d`, N11h-r2).

## Rule this round sets

A boot-image bake keeps its own execution log, or it does not count. Route dex2oat through a tee wrapper (absolute
path to the frozen binary, `PIPESTATUS` rc, log in the persistent generation directory) and tee the bake session. A
frozen driver that hides the tool's output (t5 pipes dex2oat through `tail -5` and tests tail's rc) is wrapped, not
edited.

## Files

- `build_stubs_min.py`: the minimal stubs, built twice.
- `make_candidate.py`: writes `candidate.json` and `candidate-image.csv` and checks the persisted jar SHAs.
- `compare_runs.py`: the 27-file repro with the registry exception.
- `bake/`: `bake_u12.sh`, `dex2oat64-tee.sh`, `t5-ref-u12.sha256`, `jar-sha256.txt`, `image-sha256-run{1,2}.txt`.
- `gates/`: `class-diff-stubs-u12.txt`, `stubs-merge-report.json`, `repro-27.txt`, `gate-rb.txt`, `gate-t4b.txt`,
  `gate-g1g2.txt`, `bake-receipt.json`.
- `evidence/U12-BUILD-snapshot.md`: the t4b build snapshot.
