# Proposed observation 37: Android reference

The proposal adds one Android reference observation, not an API implementation or OH success. It records same APK bytes on Android 16, four actual content-motion samples from a different clip, the bounded 20-second Perfetto capture, and the verified private remote archive. Android audio remains unknown. Actual decoder/backend equivalence is unknown, trace events were not parsed, and the app logcat tail spans only about 2.15 seconds.

`proposal.json` has 17 exact main-tree references. Its source entries identify the collection contract and receipt checker, not Toutiao source code; build is empty because no runtime or APK was built. Actual capture and remote-upload provenance are evidence entries.

`check.py` pins canonical/history preimages, appends the proposal in a separate output directory and invokes an unchanged byte copy of the original renderer with main as the read-only source root. The actual result is 37 rows and 749 exact verified file references, with complete CSV field equality and 37 HTML cards. The old 36 objects, historical 315 data/views and canonical main files were unchanged before and after. `results.json` is the actual check output; raw command and generated-preview hashes are in `evidence-index.json`.

Only this proposal/check package is delivered. Generated candidate JSON/CSV/HTML remain private review artifacts, not canonical publication. The original renderer's generic remote-publication wording is unchanged; this row's archive claims refer specifically to the pinned T24 remote receipt. Outer promotion remains necessary and must recheck the preimage if canonical has advanced. No device action or new build occurred.

Run from this isolated tree with a fresh persistent output path:

```sh
python3 benchmark/2026-10-20-t24-api37-proposal/check.py --source-root "$WORKSPACES/westlake-harness" --out "$HOME/.local/share/westlake/t24-api37-proposal/renderer-review-new"
```
