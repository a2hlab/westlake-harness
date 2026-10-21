# Exact bridge incremental AudioTrack candidate

The initial T18 source-only package could not justify replacing the deployed bridge. The original producing records and objects have now been located and independently checked: **an untouched relink reproduces deployed d4fa exactly**. The historical AudioTrack source SHA is exactly the already-reviewed 8e922c5d profile. This package compiles that one owner with the single getter addition and reuses the remaining original link inputs. It is a statically reviewed production candidate; no device or audible-output claim is made.

| Evidence | Result |
|---|---|
| Untouched deployed bridge relink | `d4fae8e5802f3153a85175243edf665714900381d463ffc5ca1e64d0b308775b` |
| Unchanged owner, original 385-argument compile recipe | 78 ELF sections unchanged except 38 bytes in non-ALLOC `.comment`; code/relocations/symbols identical |
| Single-getter candidate, two complete builds | `dca530eb4b1b53e5dd0ecc41c36953f7463609c5b70bbdf67a49dc3cae17f9d9` |
| Candidate AudioTrack object | `4b5d80a6687bc24e5e397ce7a534b9ccf2469c68689e5afe60faaaf2535e7614` |
| Original owner/source | object `bca071e6…`; source `8e922c5d…` |
| Static ABI | 2675 dynamic symbol records, 42 DT_NEEDED and SONAME unchanged; `abi_diff.py` rc=0 |
| Independent real ELF registration check | exactly one added `native_get_buffer_size_frames`, `()I`, required=1, table VA 0x16a8c0 → function VA 0xede80 |
| Verification | 3 spec scenarios, lint 100%; Rust runs real evidence verifier plus four negative host checks |

## Reproduction

`recipe.json` holds the original compile/link order with machine paths replaced by explicit roots. `input-pins.json` records 720 exact required files, including the actual linker and system headers discovered by `-MD`. The first successful run used 119 pre-pinned inputs and recorded 607 include files afterward; the second successful run pre-checked all 720 inputs. These are different receipts, not retroactively upgraded evidence.

```sh
python3 benchmark/2026-10-20-t18-audiotrack-production/build.py \
  --inputs "$T18_INPUTS" --sdk "$OH_SDK_NATIVE" \
  --out "$HOME/.local/share/westlake/t18-production/new-run"
# Default previews/checks pins only. Add --execute to build in a new output directory.
```

`T18_INPUTS` is the original build workspace supplied as an exact input set, with the relative paths specified by `$INPUTS` pins. Outer durable archival is pending until its separate archive receipt is recorded. `OH_SDK_NATIVE` is the pinned Mac OH SDK native root. This is an incremental rebuild recipe using original object and library inputs, **not** a claim that every object has been rebuilt from source. Original source-profile and getter remain in `../2026-10-20-t18-audiotrack-size/`; no prior signed evidence is overwritten. `-MMD` becomes `-MD` solely to record system includes. No source code/compile define/optimization change is hidden by that metadata change.

Execution first runs the frozen source gate, then the original bridge relink, original owner recompile/section comparison, single-getter owner compile, and candidate relink. All stages retain actual argv, stdout, stderr and rc; timeouts retain partial bytes and rc=124. Outputs go to a fresh persistent directory. Failure preserves the incomplete state instead of claiming success. Baseline/source/input drift aborts the build. Raw paths and SHA are in `private-raw-index.json`; large ELF files and original logs are retained outside Git for outer archival.

The original compiler is Linux clang15 `b107ce03…`; the Mac clang15 has a different LLVM build string. This is disclosed rather than rewritten: original AudioTrack object `bca071e6…` and unchanged recompile `7be34fe5…` differ only in `.comment` (LLVM feef13a… vs 99548401…). The actual baseline bridge relink still matches d4fa byte-for-byte. No objcopy or binary patch is used to manufacture that equality. Original source/build records are `out-touch21/fd/bridge15/artifacts.json` and `out-ability38/native-stack/artifacts.json`; the historical mc46 object supplies the deployed MediaCodec change.

## Reviewed static differences

The link argv changes only the AudioTrack object and output file. The candidate owner is the same T18 getter plus one registration row; other original owner bytes remain intact. The getter uses the existing owner lookup and mutex, returning its effective ring limit rather than free space, Java requested frames or OH hardware capacity. The pre-existing concurrent-release lifetime limitation remains explicit in the source-only package; this change introduces no independent raw-pointer lookup or retain claim.

`abi_diff --calls` reports one non-audio call-set change: the linker moved an existing `ldr x8,[x8,#40]` through an A53 erratum thunk after code layout shifted. Original instruction at 0xd0ebc is f9401508; candidate 0xd1004 branches to 0x16081c, executes the identical load, then branches back to 0xd1008 (`blr x8`). This is recorded and independently reviewed, not silently omitted from the report. The underlying non-audio input object is unchanged. `checks/abi.json` retains the exception; `checks/needed.json` retains the exact 42 dependencies.

The one tested ABI consumer is exact Android runtime `8ab6742d…`; unchanged exports additionally show no removed bridge export. Static ABI success cannot prove arbitrary runtime behavior. Next: outer 5cd-only admission with exact before/after files, CAS/rollback and fresh process binding, then actual AudioTrack exception disappearance and audio/video observations. ANW and continuous playback remain separate gates. Expected first-wall beneficiary: **toutiao**.
