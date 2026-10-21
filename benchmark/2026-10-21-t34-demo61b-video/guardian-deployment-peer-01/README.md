# Independent review: guardian-only deployment

The original deployment tool targeted sealed r1 and checked only the holder actor token. This derived tool binds the actual r2 before entry, full CC holder/start, plan and source pins. The original cfg transaction function is byte-identical; placement still requires fresh signed admission and does not prove runtime activation.

**Offline tool scope accepted:** 8 independent actual `Device` transport cases pass; the author's 22 validation and generated-shell transaction tests were independently replayed in a copied snapshot with rc 0. They include real local cp/mv/hash, failure resealing, and rollback to the actual r2 before entry. Device commands were never executed. Mount/label operations were external host seams.

The first replay exposed an eager `T34_MAIN` fallback evaluation in the test fixture. The original failed receipt is retained locally and indexed in results; the author fixed the test only. The second snapshot replays all 22 cases successfully. This does not replace or erase the first failure.

`replay_transport.py` independently exercises holder/boot drift, local transport failure, timeout with non-UTF8 partial output, remote rc failure, duplicate frame, exhausted budget, and successful frame. Unknown writes are not retried. `snapshot-02` records the actual accepted deploy/prepare/test source. Source SHA was checked after replay.

## Replay without devices

```sh
python3 replay_transport.py --source snapshot-02/deploy.py --out NEW-transport-output
T34_MAIN="$MAIN" python3 snapshot-02/test_deploy.py
```

`MAIN` must point to a checkout containing the pinned r2 payload and board-note source. The fixtures create temporary local files only. Required actual fresh identity, full generated r3 payload/plan and signed session are deliberately not manufactured here. New-boot guardian/runtime/UI verification, final power/debug restoration and retain or rollback are separate real operation steps.

The public raw successful author receipt and independent transport receipt accompany this report. The first failed stderr contains original local paths and stays in the private peer working directory; its SHA is recorded rather than publishing those paths.
