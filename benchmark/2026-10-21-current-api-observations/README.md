# G15 — accepted installation in the additive API observations

The old50-row view omitted the accepted G13 install, while G11 still described an earlier offline window. This update adds8 observations (58 total, 1339 exact reference occurrences) without changing any of the first50 row objects or the315 historical grades. An installer or app-specific guardian is not a newly verified Android public API.

Sources are the main checkout identified in `input-pins.json`, the preserved G11 draft, and the accepted G13 package landed as21190811f5. All five permitted existing output files were clean before copying their main preimages; unrelated G10/G12/G13 lane work was preserved. `original-50.json` is byte-identical to the pinned original observations file. The renderer remains byte-identical, SHA0276c50ee6ae53a6af5e45651a7c727c4cfe8fc4d30b9bb15208d67c780fc147.

| Added observation | Evidence boundary |
|---|---|
| G08 / JAVA-042 | Existing host Open and malformed-boundary evidence; unchanged APK |
| G09 / JAVA-042 | Native03 has13 actual rc0 stages, full baseline object/library SHA equality; source, pinned toolchain inputs, recipe, original log index and remote archive receipt linked |
| G13 / JAVA-042 | Installation accepted, UID20011077 retained, candidate actually loaded; original loader failure preserved; original51e1 aliases restored |
| T35 | White screen observed; cause inferred, live parent environment not observed |
| T36 | r4c offline candidate, not deployed or visually accepted |
| T37 | Existing18/18 function and165/165 assembly review; no new device acceptance |
| T38 | Safety-stop document only; unvalidated work and missing original logs remain so |
| G14 | Safety-stop document only; no disabled launch argv or launch produced |

**Genshin was not started: zero game screenshots, liveness unknown, no first-frame or playable claim.** Historical7c24 candidate loading is distinct from current restored51e1 files; a mapped restored library was not observed after demand-idle exit. T38/G14 rejected work was not rerun or regenerated. No device, REA or build command was executed by G15.

## Offline verification

After landing with the reference evidence present:

```sh
python3 benchmark/2026-10-21-current-api-observations/check_observations.py --self-test --render
```

In an isolated lane add `--source-root "$WORKSPACES/westlake-harness"`. The checker validates before calling the existing renderer, fails with the concrete missing/drifted path, and exercises three refusal controls: an altered original row, a missing reference and a wrong reference SHA. It checks all1339 references and both historical atlas files. `results.json` records the actual Python checks. The Rust selector delegates to this checker; it was supplied but not compiled or executed, respecting the no-build instruction.

`landing-paths.txt` is the fixed path-only list. `SHA256SUMS` pins every delivered file except itself. Shared Git/board writes were already denied, so neither was retried; this is an offline landing handoff, not a commit, push or remote-publication claim. The API renderer result likewise records `remote_publication_verified=false`.
