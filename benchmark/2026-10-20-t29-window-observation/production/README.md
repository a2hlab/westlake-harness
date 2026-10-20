# T29 bridge-first production preparation

Status: recipe prepared, no joint production run yet. The accepted checkpoint02
runtime sources are unchanged. Missing final consumer pins are a hard stop before
output creation or compilation.

`build.py` takes existing T18/T28 build directories, their original inputs,
the existing OH SDK, a frozen consumer snapshot and its review pin. Paths are
arguments; optional `--path-map OLD=NEW` remaps recorded historical paths without
changing recorded expected SHA values. The consumer manifest has:

```json
{
  "status": "CONSUMER_FINAL_REVIEWED",
  "sources": {
    "derived/oh_surface_texture_jni.cpp": "<final SHA>",
    "derived/oh_texture_view_jni.cpp": "<final SHA>",
    "logger/observe29c.c": "<final SHA>",
    "logger/observe29c.h": "<final SHA>"
  },
  "review": {"path": "<receipt within frozen consumer snapshot>", "sha256": "<SHA>"}
}
```

The integrator may create this snapshot after receiving CC's final pins and
review receipt. A live author directory is not implicitly final. An unknown or
missing receipt must not be filled with a fabricated PASS.

```sh
python3 production/build.py \
  --repo "$MAIN" --sdk "$OH_NATIVE" --bridge-inputs "$BRIDGE_INPUTS" \
  --bridge-base "$T18_BUILD" --shim-base "$T28_BUILD" \
  --consumer "$CONSUMER_SNAPSHOT" --consumer-pins "$CONSUMER_PINS" \
  --out "$NEW_T29_OUT" --execute
```

The order is fixed:

1. Verify T18's720 input pins, T28 receipt inputs/outputs, tool bytes and current
   frozen registry. Relink exact dca bridge and89b9 shim baselines.
2. Compile the two original consumer sources for comparison, then the two final
   observed sources and hidden logger. Reuse every other bridge object, including
   T18's candidate audio object. A non-identical original consumer object is
   explicitly marked for semantic review; it is not called historical byte
   reproduction.
3. Require nonempty equal bridge export/version tuples and DT_NEEDED. Decode the
   actual12 SurfaceTexture and4 TextureView JNI table entries from ELF RELATIVE
   relocations, require unchanged names/signatures/function identities, and retain
   the new addresses.
4. Extract three owner function addresses and two reference GOT locations from
   the **new** bridge. Validate executable/readable PT_LOAD ranges. Generate
   pair/geometry copies under the new output directory, replacing only those
   five constants; same-provider predicates and checkpoint02 originals remain
   unchanged.
5. Compile four changed shim units plus the hidden logger; reuse all other T28
   objects. Require all78 versioned shim exports and dependency tuples unchanged.
   Publish actual lock/unlock/geometry offsets and both ELF SHAs.

Each command stores its original argv/stdout/stderr/rc as it executes. Header
dependencies and actual input bytes are pinned and rechecked. Failed attempts
retain an INCOMPLETE receipt. The final state is at most
`OFFLINE_OBSERVATION_CANDIDATE_NOT_DEPLOY_AUTHORIZED`; runtime namespace/caller
binding remains unknown.

Preparation evidence: the independent owner extractor matched all five known
dca locations and left both template files byte-identical;9 positive/negative
checks passed. Exact baseline JNI decoding read12+4 entries. These checks do not
substitute for extracting or validating the future bridge.

## Current checkpoint02 extraction

`owner-extract-02/results.json` selects the current preparation evidence. The
original extraction used checkpoint01 templates; replay against mutable
`shim/derived` correctly rejected their changed SHA. All original commands and
the outer rc1 failure are retained in the private raw index. Prior public
metadata is preserved under `history/preparation-01/`.

The new extraction and nine tests use `.private/owner-extract-02/templates`, a
byte-exact snapshot of checkpoint02, rather than a mutable working directory.
Both commands returned rc0. The unchanged baseline bridge gives unchanged five
locations; this does not predict locations in the future consumer bridge.
Replay the exact argv arrays in `.private/owner-extract-02/{extract,tests}.argv.json`
from the repository root (extraction requires a fresh output path).

## Explicit external-input check entrypoints

The current scripts are `check_prepare_owner.py` and `check_preparation.py`.
They require real ELF inputs and are not zero-argument test discovery entries.
Only filenames changed; both source SHA values are identical to the old scripts.
New actual argv/stdout/stderr/rc are under `.private/check-entrypoints-01/`: owner
9/9 and preparation 8/8 passed. `entrypoint-rename-01/replay-argv.json` supplies
portable argv; use a fresh output for the preparation check. Previous argv and
history keep their original names and are evidence, not current commands.
