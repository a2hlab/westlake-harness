# T34 W04 driver adversarial peer review

The original recovery driver did not compare private-file hashes before unlock. The first replacement draft also used an unsafe `set -e` AND-list: an existing compat file could still produce `PRIVATE_COMPAT_ABSENT` with exit 0. A real local shell reproduced this counterexample. The revised generator uses independent checks with explicit exit 81; all eight generated existence/symlink checks reject their corresponding present-file or dangling-symlink fixtures.

The reviewed revision has no remaining blocker within this narrow host-side review. This is not device authorization or runtime acceptance. `results.json` pins the four reviewed files and records 32 actual-function/local-shell cases. Source hashes were unchanged before and after replay, and the helper pins match main.

The replay calls the production restoration parser, restoration orchestration, holder/deadline checks, remote-frame parser and timeout recorder. A local subprocess verifies timeout preservation of partial stdout/stderr. The generated final restoration shell passes `sh -n`; the actual inherited process guard accepts its local process fixture and rejects changed birth. Ten physical/private hash mutations, cfg/HAP/control drift, wrong power/debug, missing identity/absence evidence and malformed remote results are rejected. A mocked transport records the actual restoration call order: normal icon, original power, final verification, unlock, held-after observation. No HDC or other device command is executed by this replay.

`generated-final-restore.sh` is a captured host-test artifact, **not an execution card**. Its process fields are fixture inputs. `source-index.json` pins persistent private raw outputs without publishing private host paths. The old failure remains recorded as `preserved_old_AND_list_counterexample`.

Offline replay, supplying the reviewed source tree and existing W04 input directory, writes only a new local output directory:

```sh
python3 benchmark/2026-10-21-t34-demo61b-video/window-driver-peer-01/replay.py \
  --source "$REVIEW_SOURCE/window-driver-01" --repo "$MAIN_REPO" \
  --window "$HOME/.local/share/westlake/t34-demo61b-video-20261021/W-04" \
  --out "$HOME/.local/share/westlake/t34-window-driver-peer-new"
```

The drivers retain the original holder/start and bounded window. Recovery does not depend on an optional child staying alive. A failed or incomplete recovery check stops with the lock retained; outer recovery is still required. Neither a completed UI command nor a restoration receipt claims feed/video success.
