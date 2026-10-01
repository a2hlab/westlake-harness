# T7d reproduction: strict mismatch, three-run provenance exception proposed

**The final T7d is not byte-reproduced. The authorized three-run follow-up below supports `verified-with-exception` provenance, pending outer approval; deployment remains blocked.** One authorized generation completed successfully in 6.608 seconds using frozen FZ-005 dex2oat64 and the exact embedded command. **26/27 output files are byte-identical; `boot.art` differs at exactly two bytes.** Under the initial R1 order no original file was replaced and no second build was attempted. The later explicitly authorized R2/R3 results are below; the U7 example still remains `deployable=false`.

## Protocol and immutable inputs

`PROTOCOL.md` was written before execution and the criterion published in PROGRESS(95): compiler exit 0, exactly 27 outputs, 27 matching SHA-256 values and unchanged original tools/inputs/images. Any mismatch stops promotion.

- Tool `dex2oat64`: `ae865ddd6a7e4b25a18b7c07402920c69e5599b329778eff647a08803948322b`.
- Generator `t5_gen_image.sh`: `14b1f709cbeae35c2e606ee923d26a9f59e92dd827da84bdf5126de79a675d46`.
- Nine input JARs match the final T7d inventory, including stubs `d8b2406e…`.
- Frozen generator ran `--check` successfully. Its normal `work/incoming` staging would change the embedded command paths, so the compiler was invoked directly with the exact `boot.oat` argv after that check. This use of the generator is recorded explicitly; it was not edited or represented as a full generator invocation.
- A private `unshare --mount --propagation private` namespace bound a fresh output directory over the original output pathname **only inside that process**. Inputs and tool trees were remounted read-only in that namespace. `/tmp`, HOME, logs and outputs were directed into the fresh directory. No host-global mount changed.
- Remote root: `/home/alvin/cx-t0-t7d-reproduction-20261001T0645/`; output/logs in `run/`. `before.json` records hostname, exact time and supporting host-library hashes. `compiler-exit.json` records exit 0. Frozen tools, input JARs and all original T7d outputs were rehashed after generation and remained unchanged.

## Initial R1 file-level comparison

`result.json` records both full SHA-256 values for every one of the 27 files.

| Family | Exact | Difference category |
| --- | ---: | --- |
| OAT | 9/9 | None: all headers, embedded command paths and code bytes match |
| VDEX | 9/9 | None |
| ART except boot.art | 8/8 | None |
| boot.art | 0/1 | Image object payload: two bytes in a backtrace long-array element |

Both `boot.art` files are 4,644,864 bytes. Reference SHA is `13aeb841e492e87c577e30d61b5e736274098e34deb3452ddd5b5380c9b0353c`; reproduction is `08e9c666e1eb53acff296c0ab6e88d896a23b4a7d1ba10d82ea7121bcd453bb9`.

Exact zero-based byte offsets: **254905–254906 (`0x3e3b9`–`0x3e3ba`)**. No other byte differs. The first 256 bytes of the image header are identical (`1475a0ee…`). Host oatdump exits 0 for both images and places the offset in `SectionObjects` (range 0–2,091,712), not an image header or embedded path.

The two oatdump excerpts agree on the object graph:

```text
0x7003e360: java.util.concurrent.CancellationException
  backtrace: 0x7003e380 java.lang.Object
0x7003e380: java.lang.Object[] length:2
  0: 0x7003e3a8 long[]
  1: 0x700d51c8 Class: sun.nio.ch.PendingFuture
0x7003e3a8: long[] length:2
```

Reading the two little-endian 64-bit elements at file offset `0x3e3b8` gives `[0x40460b00, 0x2]` in T7d and `[0x40747b00, 0x2]` in the reproduction. This establishes **backtrace object data**, not a timestamp or path-string difference. A build-process address retained in a backtrace is a possible explanation; its exact origin and runtime harmlessness are **not established**. No binary normalization, patching, tool change or replacement was performed. R1 was stopped before the separately authorized follow-up.

`object-analysis.json` contains line-numbered excerpts and SHA-256 values of both full oatdump logs (about 156 MB each, retained only in the new remote run directory). `byte-differences.json` contains the exact byte range and adjacent bytes. `compiler.log` is the new reproduction log, never presented as the historical T7d build log.

## Initial R1 disposition

The strict 27/27 criterion failed. The production example bundle remains `fcd4c0d8…`, its paired provenance remains `unknown`, and rollout remains false. This is an experimentally verified **26/27 partial reproduction**, not a verified full reproduction. No board access, frozen-registry change or push. Stop here for outer review.

## Authorized R2/R3 follow-up (ACK95 06:50:10)

Two additional independent processes used the **unchanged R1 driver/config, same frozen tools, nine input hashes and exact embedded command**. Only their new output/temp directories differed. Both completed with compiler exit 0 and independently matched 26/27 original T7d files. Tool/input/original hashes remained unchanged in each receipt.

| Image | Backtrace method word | Dex PC | Within any image ArtMethod section? |
| --- | --- | ---: | --- |
| T7d | `0x40460b00` | 2 | No |
| R1 | `0x40747b00` | 2 | No |
| R2 | `0x40843b00` | 2 | No |
| R3 | `0x41585b00` | 2 | No |

All **six pairwise comparisons** (three reproduction pairs and three comparisons to T7d) differ only inside the same first 64-bit backtrace element. The observed differing byte union is `[0x3e3b9,0x3e3bc)`; the enclosing field is `[0x3e3b8,0x3e3c0)`. Every other byte of `boot.art`, all nine OATs, all nine VDEXes and the other eight ARTs match. Thus `R1=R2=R3 != T7d` is ruled out: the three reproduction values themselves differ. Under the approved experimental criterion this is **build nondeterminism**, and provenance is recorded **verified-with-exception**, not exact-byte reproduction.

`exception-proposal.json` contains **one proposed entry**, scoped to this object/field, exact frozen tools and nine inputs, with all three receipts and six comparisons. Approval is pending. It is not installed in any permanent gate registry and does not change the package's `rollout_ready=false` or deployer policy. Existing strict-result files remain as historical R1 evidence; `three-run-comparison.json` and `three-run-validation.json` record the new conclusion.

### Runtime-read question

**A stack decoder reads and dereferences this field if that exception is inspected; ordinary PendingFuture cancellation does not inspect this sentinel's stack.** The inspected AOSP14 source, with hashes and line numbers in `runtime-source-evidence.json`, distinguishes those two claims:

- The actual T7d oatdump binds `PendingFuture.CANCELLED` to the same `CancellationException` at `0x7003e360` (line 132757), establishing object ownership.
- `PendingFuture.java:38-39` constructs the static sentinel. `cancel()` assigns it (`236`), `isCancelled()` compares identity (`217`), `exception()` hides it by returning null (`208`), and both `get()` variants throw **new** `CancellationException` objects (`183-184`, `200-201`). These normal paths do not print or return the preallocated sentinel.
- If code obtains the sentinel and requests its stack, `Throwable.getOurStackTrace()` calls `nativeGetStackTrace(backtrace)` (`865-869`). JNI dispatches to `Thread::InternalStackTraceToStackTraceElementArray`, which loads the long-array element as `ArtMethod*` and calls `CreateStackTraceElement`; that function dereferences it. Native `Throwable::Dump()` likewise reads it and calls `GetLineNumFromDexPC` / `PrettyMethod` (`throwable.cc:103-126`). The saved empty-stack sentinel identity supports this lazy-decoding path.
- Parsing the nine image headers using the frozen build tree's `image.h` layout gives the complete ranges in `three-run-comparison.json`. **All four method words are outside every image ArtMethod section and outside every image's address range.** They are not valid image-relative method addresses. A stale build-process address is consistent with the data, but runtime relocation/repair and actual exposure on R155 were not tested.

Consequently this is a **provenance exception proposal, not a safety assertion**. It does not justify treating those values as image ArtMethod pointers, nor claim that ordinary app cancellation necessarily reads them or crashes. No board test, forced exception inspection, binary correction or frozen-tool change was performed.
