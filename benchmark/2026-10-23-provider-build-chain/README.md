# G37: exact provider entry found; frozen inner producer is still missing

The old lookup stopped at Android.bp and a provider manifest. This follow-through binds one actual producer entry byte-for-byte, but **does not close the build chain**. A same-named script at the recorded generation path has different bytes; it must not replace the frozen input. No runtime was built or run, and no game first-frame progress is claimed.

## New evidence

| Component | Established fact | Limit |
|---|---|---|
| Container entry | `sources/container_build.sh`, SHA `766edce071252c1506d575ecb22db6319f50436b98c4f450ec326531b02754cb`, matches full base-inputs line5 | Recipe bytes verified, never executed |
| Main source | `knowledge/toolchains/art-r155/recipe/adapter/build/provider_generation/container_build.sh`, Git blob `317621b48c104f45b9287c1f7f4e572b1140647d` | Byte-identical copy; original comments preserved |
| Second layer | Entry lines38–57 invokes `bash "$ADAPTER_ROOT/build/inner/cross_compile_arm64.sh" --clean`; frozen line4 requires `775c8ae837306c06a24fc0e2562291f63ee3854bdb5154d82c48a2ee37a6b93a` | Main copy is `fd306585…`; outer-read exact generation path is52102B/`b358f08a…`; neither adopted |
| Toolchain | Entry lines13–14,48–55 selects OH toolchain, sysroot, builtins; manifest lines19577–19578 declares clang++/clang-15 `4806f4f1…`,20608 declares builtins `05bb3f2f…` | Manifest pins plus recipe selection, not tool binary rehash or proof of actual invocation |
| Container | Full lock declares `westlake-oharm64build:local-tools`, image ID `76236bc1…`, network=none, inputs_read_only=true | Declaration only |
| Unwindstack | Full audit declares two identical `d2c1cbc7…` outputs and build-id `085331ff4a2afba3006ac15db31fb344fc692032` | No artifact rehash or original compile/link/rc0 log |
| Sigchain | Target remains `6d5d5538…`; provider-v12 instead declares `ea7becd0…` | Different object, unbound |

`results.json` separates source manifest, exact entry, compile command, toolchain, link inputs, original logs and final object. The full input index (21011 rows,2662991B, SHA `84ddec0e2dbbc249d6f7ef912663b015356500272f1ce9647302dd936b319ef1`) stays in outer persistent storage; `evidence/base-inputs-selected.txt` contains exact numbered producer/toolchain rows. Full small verification/audit/lock files are retained, not their old truncated prefixes alone.

Entry line18 names `/work/aosp-build-errors.log`; lines59–62 create `/artifacts/providers.sha256` and `build-result.env`. These are **container-local recipe paths**, not recovered original records or known host archive locations. The current remote generation root is not a proven mapping to the frozen `/inputs` mount.

## Bounded stop and next missing

The chain resolves one producer hop and stops before accepting the second. Exact775c8ae8 inner source and its frozen-input/archive mapping are required next, followed by real compile/link commands and original stdout/stderr/rc0 evidence. No justified new remote path is known from the files read; do not guess a log location or search broadly.

Outer supplementary history checks two known repository paths, at most200 commits each:4 unique blobs, no775c8ae8. `evidence/outer-exact-git-lookup.json` is the exact outer result; this is not proof of absence across all history. The mismatching remote script is indexed privately as drift evidence and was not used to infer the frozen recipe.

## Validation and reproduction

```sh
python3 benchmark/2026-10-23-provider-build-chain/check.py --self-test
# Optional, on the evidence host: add --private to verify persistent raw and excerpts.
CARGO_TARGET_DIR=benchmark/2026-10-23-provider-build-chain/.private/cargo-target cargo test --offline --manifest-path tools/spec-checks/Cargo.toml --test provider_build_chain -- --nocapture
```

Final checker:18 input pins plus5 rejected negatives (wrong sigchain, missing reference, third hop, read-rc promoted to build-rc, drifted producer accepted). Rust:1 passed,0 failed,0 ignored. These validate evidence boundaries, not build success. Initial checks and final reruns are both retained; no old failure or receipt replaced. `raw-index.json` pins local validation logs; `exact-read-raw-index.json` pins the outer-only remote reads.

Only the already-public main entry is copied, with original text unchanged. No file-specific license notice was present in that script or an adjacent tracked LICENSE/NOTICE in the inspected recipe scope; attribution remains explicit and no upstream license is invented. A missing art-r155/README read and unmatched LICENSE glob are recorded in the private notes, not silently counted as source proof.

No SSH/Orb/ADB/HDC/REA/debugger/runtime build by this reviewer. No old record or main change, commit or push. `landing-paths.txt` is the fixed path-only delivery list; `SHA256SUMS` binds its contents except itself.
