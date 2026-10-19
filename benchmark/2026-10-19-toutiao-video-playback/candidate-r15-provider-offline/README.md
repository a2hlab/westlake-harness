# R15 typed provider adapter — offline only

`OFFLINE_ADAPTER_ONLY_NOT_DEPLOYABLE`. R14's callback ABI is not the OH provider ABI. This increment provides typed thunks, a bounded identity/risk ledger and executable host evidence without changing the accepted R14 implementation. No dynamic resolver, factory, production caller route, device command or shared library is supplied. Expected help is **toutiao, conditional**; provider-instance binding and playback are not tested.

**Actual results:** 44 host cases (7 pair, 16 layout, 13 failures, 8 concurrency), 9 receipt-rejection cases and 5 Rust selectors passed. Strict lifecycle reports **6 Passed / 1 PendingReview**, rc1 solely for the human scenario; quality score 1.0. The OH compiler emitted a 7648-byte ELF64 AArch64 ET_REL object, SHA `5a3ed9e2b604b288f8fa88c218fea35b88649424a88011f8cf8b3df506e27528`. No OH link/run or live ABI success is claimed. The earlier OH attempt failed because the SDK header needs `stdbool.h`; its complete raw logs remain in `.private/oh-01`.

## Interface and lifetime

`r15_create` receives immutable typed `r15_provider` functions, explicit trusted unwrap/fence capabilities, and returns ops for **one** R14 instance. The caller owns the selected provider instance and guarantees a stable valid 24-byte handle prefix for the field copy. The adapter cannot validate arbitrary addresses. Each signed32 field is copied separately; no usage, virAddr or tail is read. OH builds include the installed SDK headers and compile seven function-pointer compatibility assertions plus Rect/Region layout assertions. Host declarations are ABI projections only.

The region thunk rejects reversed, empty or beyond-INT32-sized extents before the provider; this is the validated R14 geometry domain. It converts LTRB to xywh using int64 arithmetic and passes one Region by value with fence -1. Source unit contracts are byte stride and byte capacity; R14 retains its numerical checks. The pair oracle uses width7/height3/pixel-stride11 and padded capacity, independently checking all seven Android formats and exact dirty/output fields. A protected page immediately follows each fake handle's 24 valid bytes.

Eight mutex-protected records associate window/buffer/native identities. No adapter mutex spans provider calls. Duplicate buffer/native identities poison both affected records; ambiguous identity lookup never picks the first. Failed/uncertain records remain occupied. Only successful ordinary Flush permits reuse. The caller must externally quiesce every call, prevent new calls, destroy the R14 instance first, then destroy the adapter. Destroy refuses occupied records; no force-reset or failed-ownership reclamation is supplied.

## Cleanup semantics

- Every attempted public operation records its original rc separately from synthetic adapter refusal and suppressed calls. Handle returns a pointer, not an rc; its `raw_valid` remains false.
- Map0/NULL follows R14's one Unmap and conditionally Abort path. Map0/all-ones preserves raw0 but exposes NULL, then suppresses lower Unmap with a synthetic error so R14 skips Abort. Map failure suppresses lower Abort; no mapping absence is inferred.
- Request failure/contradictory output suppresses lower Abort. Returned owned nonnegative fence handling remains in unchanged R14, including on Request failure.
- Unmap failure prohibits Flush/Abort. Public Abort0 never clears a record or proves lower Cancel success. Failed Flush never triggers Abort. A duplicate identity detected while a callback is in flight prevents later output publication/cleanup; it cannot retroactively undo a lower operation already started.
- The independent fake provider logs public and internal operations separately. It simulates two internal Maps per successful public Map and a lower Cancel failure masked by public Abort0. Tests inspect those external journals and retained behavior, not internal adapter structs alone.

## Reproduce without devices

From the repository root, choose a fresh persistent OUT each time:

```sh
B=benchmark/2026-10-19-toutiao-video-playback/candidate-r15-provider-offline
python3 "$B/build.py" --mode host --out "$B/.private/host-new"
python3 "$B/build.py" --mode oh --out "$B/.private/oh-new"
python3 "$B/verify.py" "$B/.private/host-new" "$B/.private/oh-new" --negative
cargo test --manifest-path tools/spec-checks/Cargo.toml --test toutiao_typed_provider_adapter -- --nocapture
```

`CC` selects a host compiler; `OH_SDK_NATIVE` selects the already-installed native SDK. OH clang/readelf SHA pins are enforced. `--source-repo` selects the repository for check_frozen; R14 is still the exact pinned sibling source, never a copied rewrite. Every build starts with check_frozen. Original argv/stdout/stderr/rc, tool and consumed-header pins remain in each fresh OUT, with before/after drift checks. No tool installation is attempted.

`evidence/*-receipt.json` are explicitly path-aliased projections of pinned originals. The four `*.journal.jsonl` files and `oh-readelf.txt` are exact small stdout copies. `evidence/private-raw-index.json` enumerates original persistent outputs (including all earlier attempts and selector runs) for outer archival; do not put raw stderr or personal build paths in git. Local artifact paths are `.private/host-final/test_adapter` and `.private/oh-final/provider_adapter.o`. `collect_evidence.py` records the accepted local runs; it is packaging, not a test or deployment admission. Original R14's 49-case evidence and signed manifest remain untouched.
