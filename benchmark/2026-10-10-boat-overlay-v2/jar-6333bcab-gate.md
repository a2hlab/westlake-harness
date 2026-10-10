# jar `6333bcab` real-artifact gate (cc-t3 #91)

**Verdict: KEEP — no regression, 0 frozen-class conflicts.** The manifest's boat jar is a superset of the U13 base.

## Where it was found (search trail in `evidence/jar-6333bcab-search.log`)

The SHA literal `6333bcab…` is referenced in many manifests/receipts but is not a jar body in the first-swept
trees (`westlake-inputs`, `westlake-harness-bms-deploy`, `westlake-harness`, `vm-copies`,
`00.Workspace-games-ad1ab0a7`) — the boat-assembled dir ships a **different** jar (`56e4d473`). The receipts
(`artifact-receipt.json`, `demo-61b/inputs.json`) record the origin, and hashing that path confirms it:

```
westlake-harness-wiki/benchmark/2026-10-09-demo-boatattack/spare-5cd/overlay/oh-adapter-runtime.c9only.jar
sha256 = 6333bcab4ca2daad03965712deac6adf028a6ff0dfac04fc8ea91af177828852   (348 KiB, the "C9-only" touch jar)
```

Found at **source-lookup step 1 (local)** — `orb -m a2hlab` and hw248 were **not** needed. It is NOT a locked
artifact.

## The gate (`deployed_class_diff.py … --frozen`)

Candidate = the real `6333bcab`; deployed = the U13 board jar `bbc3f530`
(`u13-stageA-91272eaf-20261003/armed-bundle/framework/oh-adapter-runtime.jar`):

```
deployed  bbc3f530  216 classes
candidate 6333bcab  218 classes
ADDED  Ladapter/activity/InputEventDeviceProjection$1;
ADDED  Ladapter/activity/InputEventDeviceProjection;
0 dropped, 0 reshaped, 2 added (after allow lists), 0 frozen class(es) broken
```

- **0 dropped** — no deployed class is removed, so no non-Boat app loses a class it depends on.
- **0 frozen broken** — none of the `knowledge/frozen/frozen.json` classes (incl the FZ-007/FZ-008 TLS set:
  `WestlakeTlsInstall`, conscrypt `OpenSSLProvider`, `android.net.ssl.SSLSockets`, `NetworkInfo$State`) is affected.
- **+2 added** — `adapter/activity/InputEventDeviceProjection` (the C9 touch-input projection), additive only.

Evidence: `evidence/jar-6333bcab-classdiff.txt`.

## Correcting the earlier indicative red flag

The v1 writeup flagged the jar as a likely TLS/webview regressor from an **indicative** diff of the
boat-assembled twin `56e4d473` (186 dropped incl `WestlakeTlsInstall` / conscrypt / chromium). That twin is a
**different, stripped jar** that the manifest does not use. The manifest's actual jar (`6333bcab`) is clean. The
red flag is **withdrawn**.

## Result for Boat v2

Both shared files the v2 overlay keeps are now verified non-regressing:

- adapter `8ab85446`: superset of base (+2 exports, 0 removed).
- jar `6333bcab`: superset of base (+2 classes, 0 dropped, 0 frozen broken).

Only the **runtime** still needs the fix (keep `18763dd4`; port the render delta in — cx-bms spec). If Boat v2 were
to **omit** this jar, Boat itself would lose the two added `InputEventDeviceProjection` classes (the C9 touch-input
projection the route-2d combo relies on); non-Boat apps would be unaffected (the jar drops nothing). So the jar is
**kept** in v2 — it is additive and safe.
