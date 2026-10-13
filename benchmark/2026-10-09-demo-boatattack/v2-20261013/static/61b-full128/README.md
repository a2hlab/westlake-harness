# 61b V2 incremental file observer

## Evidence and boundary

Reuses the landed R6 128-row index/comparison and existing first_fatal.py; no device transport, new scanner, runtime edit, installation or automated verdict. reference-index.json pins 128 original signed-batch final images plus keyed R4/R6 references and original 61b V1 final seal/signoff. V1 was Plan2 current20 plus historical128, not a fresh current61b128 run.

Snotz/Toodoo's prior content differences were adjudicated as scoped startup nonregression (root acceptance269eb013 and resolution84b9e9dd), not pending user authorization. Do not rewrite old evidence. New content differences still require original signed image, R4, R6 and actual61b comparison; equal controls do not prove retained list contents.

## First usable command

Set PLAN and RUNNER to the actual T4-produced full128 window files, not postinstall940 or smoke. The sole device writer is T4/root's designated writer; this adapter only reads local files.

```sh
WORKSPACES=${WORKSPACES:-$HOME/orca/workspaces}
OBSERVER="$WORKSPACES/westlake-harness-bms/benchmark/2026-10-09-demo-boatattack/v2-20261013/static/61b-full128"
PLAN="<actual-full128-window-plan.json>"
RUNNER="<actual-full128-window-runner-directory>"
WORKSPACES="$WORKSPACES" python3 "$OBSERVER/collect_window.py" \
  --plan "$PLAN" --runner "$RUNNER" --out "$OBSERVER/.artifacts/packets/window-01"
```

Run once per newly completed window, or while records arrive. Each finished canonical plan-shard record produces a separately pinned JSON packet; repeat identical packets are idempotent, differing old packets refuse overwrite. Unknown keys/duplicate shard keys/wrong serial/package/APK/image path or SHA reject. Unfinished records and non-shard smoke are excluded. Failed app records and missing frames remain evidence, never automated lit.

Consume actual_images, facts_verbatim and first_fatal, then personally view signed.image, R4 frame via r6_compare_index and r4_comparison, and r6_images. Output visual_verdict stays PENDING_IMAGE_REVIEW; NOT_LIT/loading/empty/foreground_unconfirmed remain distinct. Store each reviewed window in this directory, with its actual boot and source SHA; do not wait for the full round to report concrete regressions. Current actual run root and boot intentionally remain null until T4 supplies the real files.

Validation is file-only; --help and wrong-board rejection do not imply a current61b run or UI PASS.
