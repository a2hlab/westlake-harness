# T2 Input/stage exact source and compile bindings

Use the actual T29 linked objects, not uniformly older base sources. WMC is already handled by outer's exact baseline reproduction and is not rebuilt or re-audited here. This packet adds the two source/compile closures needed beside it; no compiler/linker/VM/device command ran and the existing staging is unchanged.

| Unit | Exact source SHA256 | Exact T29 object SHA256 | Original compile / link position |
|---|---|---|---|
| Ability38 `oh_input_bridge.cpp` | `54057ec99dc53c6085cdfa6e9394bd3e9d7bdca0012b9597896418ba14221136` | `5777e4302752f419a7f4a9d6da3e5676a89e5a6bbe4a8d1be81fcdc9c6b85f89` | native-stack artifacts,387 argv tokens,rc0; T29 argv[51] |
| touch21 `session_stage_adapter.cpp` | `54660865d7bffef81f4a2af57707df8b141b817c4544f7d590ccda6b50f9c1ae` | `7501dad3afadca9d8e98fe924de7d919cdf3f1923af65e294ac040eb82fd7c4d` | bridge15 artifacts,385 tokens; T29 argv[55] |

Positions are zero-based argv indexes, not symbol offsets. Actual archive source bytes equal the MAIN snapshots identified in `units.json`; archive object hashes equal both original artifact records and T29 final receipt pins. Each object occurs exactly once in the final link. Touch21 additionally retains the per-source warning log and aggregate `NATIVE_SOURCE_OBJECTS 50 FAILED 0` / build PASS record; its JSON has no per-TU numeric rc field, which is left null rather than invented.

## Immediate files for the build owner

- `$DELIVERY/.private/input.original.argv.json`
- `$DELIVERY/.private/stage.original.argv.json`
- `$DELIVERY/.private/source-closure/ORB_WS/` —452 unique exact files from117 Input and414 stage dependency entries.
- `$DELIVERY/.private/originals/ORB_WS/` — original artifact JSON, source/object/dep/log bytes.
- `file-closure.json` — fullSHA/size and exact archive-origin→destination for every file. Two Input headers use explicitly recorded Ability38 snapshot members; no guessed old-base replacement.
- `input.compile.argv.json` and `stage.compile.argv.json` — complete public aliases of original argv. `$ORIGINAL_ROOT_0/1` map exactly as the prior WMC staging; the raw original strings remain private. Reuse outer's fixed SDK and the792 libcxx system headers already restored to the existing `-isystem` location. Do not add an audit prerequisite before the controlled compile attempt.

Archive source remains the local fixed `source-closure/.private/archive-02/window.tar.gz`, SHA `922e0291a10cc73a1cb6833c19c92c7baab163a7b1a23d92023657b1c40e8fa2`. The original final link argv is the previously pinned T29 `13-bridge-candidate.argv.json`, SHA `e960b1d1c12776cf6deceac1792abb0a60f3fb43d1de74eb935b88bd14d619cb`. Full original-record and private-file hashes are included, not new execution claims.

## Minimal build delta

1. **Input:** use the original Ability38 native-stack command. Relative to WMC its only non-I/O additions are the two leading eventhandler include directories: `android-source/oh-eventhandler/interfaces/inner_api` and `android-source/oh-eventhandler/frameworks/eventhandler/include`. Preserve their precedence. Use source under `westlake-ability38`, not `westlake-touch21`.
2. **Stage:** use the original touch21 command. Its project include roots are touch21, not Ability38; retain that ordering. `compile-delta.json` records every exact token difference from original WMC. Both commands retain `-include sys/types.h`, `-MMD`, original defines and prefix-map structure.
3. Compile original Input/stage into new output objects first and compare the full object hashes above. For the eventual reviewed candidate, change source/output/dep paths and explicitly declared new headers only. The smallest planned modified-TU set is WMC + Input + stage; no new library or wholesale bridge rebuild follows from this analysis.
4. Reuse the final T29 link line, replace only the corresponding reviewed objects, keep all T29 consumer/logger/audio objects and ordering. Source/header candidate differences are not yet reviewed here. Any shared class-layout/inline change requires the actual affected consumers to be rebuilt, not an assumption that the existing ABI survives.

## Production call sites / source selection

- Ability38 `oh_input_bridge.cpp:4955–4970` and `4974–4984`: both MMI event paths read `GetAgentWindowId()` and test `isKnownSession(sid)` before passing that ID into existing handling. These are the exact source positions for t2's actual→logical ID translation. Updating `activeSessionId_` at5464 alone does not replace these lookups.
- touch21 `session_stage_adapter.cpp:110,121,132,143`: active/foreground/background/destroy callbacks reach the Java bridge; this is the existing native stage TU to derive, not the Java BCP class. Runtime invocation is not asserted.
- Existing `input_event_bridge.cpp` in the linked object is Focus34; its source SHA3132fc… happens to equal the old base copy, but object selection still comes from Focus34. Its registration path calls `OHInputBridge::registerInputChannel(sessionId,dupFd)` at103. No change is required solely to add translation inside the actual event consumer. Keep linked Focus34 manager/event-channel objects unchanged unless the final patch actually affects their dependencies.
- `session_stage_adapter.h` snapshot bytes are identical for touch21 and Ability38: `54301267b82b9d6a9f9df239e86eacfceabd4058e398c1cd179cbab10bf7c7b8`. In contrast, current Ability38/Focus34 `oh_input_bridge.h` is `64e6885f7bc1e08ef9eeeee460cabbc278af5447906ba87f72cbe5012de855ff`; old base header is different (`7b017d55…`) and must not be substituted.

The t2 MAIN candidate directory was not present at inspection; these are exact baseline identities and contract-driven minimal build inputs, not approval of an unseen patch. No new runtime behavior, callback occurrence, input recovery or feed success is claimed.
