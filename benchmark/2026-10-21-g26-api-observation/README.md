# G29 — append the G26 native-route candidate as observation 61 (offline; not deployed)

One row is appended to `../2026-10-19-api-progress-update/`. The 60-row prefix is unchanged: it is
byte-identical to master `83d1a6e07` (`original-60.json`, pinned in `input-pins.json`). The historical
315 atlas, the renderer `render.py` (`0276c50e…`), the earlier G15/G17/G25 results and all prior README
lines are also unchanged; README gains one appended paragraph.

Row `OBS-20261021-G26-NATIVE-ROUTE-CANDIDATE` ([added-row.json](added-row.json)) records what the G26
receipts say:

- **Change.** Three copied source files change: exact Genshin package membership in host and ANL, plus
  `libmediandk.so` in the Genshin native domain's app-to-bridge shared list. No leaf library, owner,
  open-site, runtime/audio publication or game patch is added.
- **Build.** Both baselines were reproduced: host `2a87118e…`, ANL `eebd62f2…`. Candidates are host
  `ee5649f2…` and ANL `640b3c87…`. All 8 compile/link commands returned 0:
  - host: DevEco clang `6a5ec844…`, ld.lld `489c6d66…`;
  - ANL: clang-15 `b107ce03…`, ld.lld `8583bdc8…`.

  The host build reuses stock objects, so it is **incremental and reproducible, not a full-source clean
  rebuild**.
- **Regression.** The actual production functions were exercised per version: 37 ANL domains and 50
  host routes, using **fake OH callbacks**, so this is not runtime provider binding. Exports and NEEDED
  entries are unchanged.
- **ABI.** The exact game imports `__register_atfork`, `__FD_SET_chk` and `__FD_ISSET_chk`, all covered
  by the unchanged private ABI `d2053066…`. Its atfork DSO-unload limitation remains.
- **Status.** `candidate_currently_deployed=false`, not frozen, not a game change. The OH provider
  winner, frames, audio/video and playability are unverified, and G24's failure stays as recorded.
- **Build archive.** G26's README said its raw logs were local-only at delivery time; that README and its
  manifest are not altered. The outer loop later remote-SHA-verified the build archive `e58740f5…`
  (`native-route-build-archive`).
- **References.** 10 source, 10 build and 15 evidence files, all with exact SHA, limited to
  `native-route-candidate` and `native-route-build-archive`.

## Checks (offline; `check.stdout.txt`, rc 0)

`python3 -B check_observation.py [--source-root <repo>]` (or `cargo test --test commercial_game_g26_observation`):

- **Strict prefixes.** It reuses G25's checker, which in turn runs the G17 and G15 checks. G15's 58-row,
  G17's 59-row and G25's 60-row prefixes are strict, and G25 now allows a later append.
- **Renderer byte equality.** A byte-identical copy of the original renderer, run on the checked JSON,
  must reproduce `index.html`, `observations.csv` and `results.json` exactly (61 rows, 1423 references).
- **G29 row.** Exactly 61 rows are required. Row 61 must equal `added-row.json`, under independent
  semantic guards, and is cross-checked against the G26 results and the archive receipt.
- **Fourteen negatives are refused:**
  - history drift, G24 row changed;
  - HTML-only success forgery, CSV-only edit;
  - truncation to 60, a 62nd row, a row-61 edit;
  - dropped evidence;
  - claims of freeze, current deployment, game playable or clean rebuild;
  - missing reference, SHA drift.

G25 checker change: it now accepts `>= 60` rows while keeping the strict prefix. Its two old
61-row negatives become "later append allowed" (positive) and "appended row with an unverified missing
reference" (refused by the original renderer). All its G24 failure-semantics negatives are kept. G25's
historical outputs and other SHA256SUMS lines are unchanged; only its `check_observation.py` line is
updated.

No device, REA, runtime build, G14 or T38 content was run. Not pushed.
