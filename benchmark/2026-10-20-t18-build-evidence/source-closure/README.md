# T18 independent historical source-closure supplement

The first T18 archive preserves the 720-input incremental relink and new production executions. This separate supplement adds original sources, headers, object dependencies, original recipes and existing historical records. It does not modify that archive or turn missing historical logs into newly invented evidence.

The supplement was read back member-by-member: **1,545 files, 84,089,815 bytes**, SHA256 `922e0291a10cc73a1cb6833c19c92c7baab163a7b1a23d92023657b1c40e8fa2`.

Its contents include:

- All 50 base sources and 900 headers from the exact touch21 artifacts.json, individually matched to recorded SHA. `westlake/` maps to the existing `westlake-touch21/` source; `compat/` maps to the original bridge15 compat tree. Both transformed adapter source and original source/transform records are retained.
- The complete touch21 object/compat directories and original build-fd script/log and bridge15 log.
- The focus34 build.json, build-history.jsonl, all existing log files and all **12 object/.d/.key triples**. The 9 final objects' bytes and stored key values match evolution's original-command/dependency-key recomputation report; the other 3 retained triples are not promoted into that final set. Actual dependency files—including westlake-focus34 source/headers and `native/input_transport_boundary.h`—are physically included. This archive lane did not rerun a build or reattribute historical executions.
- Both ability38 policy and stack artifacts, objects and compile/link logs. Each stage's 52 reused objects were checked against its record; all **109 explicit file arguments** of each link command were collected. Original source SHA checks are retained.
- Existing mc46 relink/repro/patched outputs, recorded dependencies, actual MediaCodec/AudioTrack source and LICENSE, plus the original sibling `build_bridge_mc.py` bytes.
- The original clang-15/lld tool bytes pinned by the MAIN closure index.
- The 138-entry small source/license/recipe snapshot and its exact snapshot.json as observed at packaging. Its base-source accounting remains 13 already in MAIN and 37 supplied by that snapshot. The private archive includes original author paths in records; public indexes expose only portable aliases. Source delivery/merge is owned by evolution, not performed by this archive lane.

The archive uses relative `ORB_WS/`, `TRIAGE46/`, `source-snapshot/` and `archive-review/` roots. Original records keep their original bytes and path spellings. Lexical `../` segments are normalized only in safe archive member paths; original source references remain in the index. The first packaging attempt rejected an unsafe member name before creating a tar. Its source and failure record remain private; `packaging-attempts.json` records the correction without altering input bytes.

The **original final mc46 full stdout/stderr/rc is still UNKNOWN_NOT_FOUND**. Existing partial logs, build history, recipes and artifacts are preserved as such. New T18 baseline reproduction is in the first archive and is not called a historical build. No claim of full source rebuild, runtime registration, audio or video acceptance follows from this supplement.

`packet-final/archive-receipt.json` is the stable supplement receipt for final recipe references; `packet-final/bundle-links.json` connects it to the first archive. Remote verification remains pending until outer executes `.private/archive-02/remote-commands.private.json`. Do not change the prior pending receipts; append an outer-success sidecar. `packet-final/results.json` records selection checks before tar creation; the archive receipt supplies the subsequent completed local verification.

No HDC, build, push or network command was executed. `package.py` requires explicit `--write` and a fresh output directory. The complete member index and large bytes stay private; public landing files are limited to small verification indexes and explanations.
