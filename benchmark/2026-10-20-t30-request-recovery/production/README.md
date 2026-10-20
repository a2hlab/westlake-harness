# T30 two-unit production preparation

The T29 window exposed persistent failure after a resource-free RequestBuffer error. T30 changes the recovery implementation; the first RequestBuffer error itself remains unexplained. This directory prepares its offline build without compiling a candidate or operating a device.

The actual T29 production receipt is SHA `7625f504f313a658fde95616c08953ade8518e789fbc89f869e8ae981c95b27e`. `recipe.json` contains its exact compile/link argv with portable anchors, 82 existing input SHA/size records, and two null candidate source SHAs. The compile command is from `raw/20-shim-0.argv.json` (`6dfcfaac…`), and the link command is from `raw/30-shim-candidate.argv.json` (`ebef9248…`). These are actual successful T29 commands, not guessed build flags.

Only `window_module.c` and `provider_adapter.c` are recompiled, replacing `r14.o` and `r15.o`. The 16 original link object positions remain in order; all other objects, including pair, geometry, observers, RGBX and YV12, are unchanged. The bridge is copied byte-for-byte at `b0e5602a97133ebb1dca12972a8931a86528322685a211bb1a7a0a2185fefbd4`. A baseline relink must first reproduce shim `9f3cecdeec89bd7aaa09a2d71a34f24bdc59ce41059a551144cef682526d3087`.

The inventory includes the 32 actual compiler dependency paths, clang, ld.lld, llvm-readelf, version script, runtime objects, builtins archive and implicit link libraries. In particular `-ldl` uses the original 8-byte empty `libdl.a`; `-lc` uses the original OH sysroot `libc.so`. Compiler SHA is `6a5ec84488cd11db8118fab8160affc40b90885f82481dbc31624f561f7b72a1`; linker SHA is `489c6d6628a56c027eac4dceee87910f7ca28b0c5a0e5188c32cb0108c08a837`. Do not replace these with host libraries or recompile unrelated objects.

Default preview makes zero compiler/linker/device calls and creates no candidate directory:

```sh
python3 benchmark/2026-10-20-t30-request-recovery/production/build.py
```

After the outer freezes and reviews the real t1 source, it supplies a manifest shaped like `candidate-pins.template.json`, with status `T30_SOURCE_FINAL_REVIEWED`, two actual relative paths (`source_r14` ending `window_module.c`, `source_r15` ending `provider_adapter.c`) and their separate SHAs, plus a review path and SHA. All three files must remain inside `CANDIDATE_ROOT`. The checked-in template deliberately cannot execute. No future source SHA is invented here.

The later execution entry is:

```sh
python3 "$REPO/benchmark/2026-10-20-t30-request-recovery/production/build.py" \
  --baseline "$T29_OUT" --t29-tree "$T29_TREE" --orb-root "$ORB_ROOT" \
  --sdk "$SDK" --repo "$REPO" \
  --candidate-root "$CANDIDATE_ROOT" --candidate-pins "$CANDIDATE_PINS" \
  --out "$NEW_PERSISTENT_OUT" --execute
```

`T29_OUT` is the preserved actual `production-01`; `T29_TREE` locates the preserved T28/T29 objects and headers; `ORB_ROOT` locates the original build workspace; `SDK` is the pinned OH native SDK. All bindings must reproduce recipe hashes. Output must be a new persistent absolute directory. The source/review are copied before compilation, original command stdout/stderr/rc are retained, dependency closure is checked, and final ABI must preserve 78 definitions and nonempty DT_NEEDED with no TEXTREL. Three export offsets come from the newly built ELF. Candidate build success remains pending independent peer/runtime review, not deployment authorization.

Preparation tests run through `ttvideo_t30_production_prepare`: default no-op preview, unfrozen execution refusal, actual source/review SHA and path checks, and the two-object recipe. The first test run exposed only macOS `/var` versus `/private/var` fixture path normalization; the original failure is preserved and the test now compares resolved paths. No production compiler was invoked. The t2 contract depends on t1 and was parsed/linted before handoff.

The first preparation (commit `be43bfd32`) remains historical. The peer full-chain fixture exposed an additional R15 retained record, so the two-unit successor is required. T28 R15 source SHA is `5fc32ea58014a43a78d2942ccbe5e79229abef372bb612f8f14a7bfcd8b01617`; its actual object is `b6917536bdc29f19a2c249efabd9b3ff91fd526268ea87be3b26514978948f8b` (9,560 bytes). Exact argv comes from T28 `raw/20-compile-1.argv.json`; the recipe records its full hash and receipt. Its original clang-15 has the same compiler bytes as clang. The successor adds `-MD/-MF` to record actual dependencies; original T28 SDK header pins and provider/window headers are included. The old compile did not emit a dependency file, so this is not presented as an observed old R15 `.d` closure. Unknown new dependencies will reject the candidate after compilation and require separately reviewed input pins.

The existing `check_frozen.py --git REPO --registry REGISTRY` command is legal: its implementation treats the argument as the repository directory, while each frozen registry entry supplies its own commit/branch. A real read-only run returned 30 checked, 0 violations, rc 0. No production compiler or linker was run for this revision.
