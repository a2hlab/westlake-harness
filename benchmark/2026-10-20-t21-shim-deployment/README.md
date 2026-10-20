# T21: sixth-artifact shim transaction, execution disabled

The T18 transaction does not restore or replace `webview-t-lib/libwebview_bionic_shim.so`. This mechanically derived executor adds that exact sixth path to the existing five-artifact set. Its baseline is `85c789f48b2bc0c31658c9dc591cd27784cc0ddfe559005e8d36d1d7d220476a`. **The shim candidate SHA is null and production references are empty: execute fails before Board construction. This delivery removes zero runtime failures.**

`derive.py` requires T18 executor `57affbe0…` and emits `executor.py`; `changes.diff` records the complete delta. Existing Board, file/CAS/swap helpers, WID normalization, 1800-second limit and 600-second recovery reserve are preserved. The new shim has physical/private hash, fresh mode/UID/GID/label and same-inode checks. Rollback binds the original apply plan, candidate declaration and before/after hashes; foreign bytes are refused. Physical-only recovery still requires a fresh boot and outer namespace/UI verification.

Before the first swap, all **six preimages** must be durable: five verified file backups and a sixth `ABSENT` marker for the originally absent OpenSLES compat file. The shim swaps first; run.sh remains last. Tests execute the actual generated transaction with real copy/hash/rename operations, interrupt after each of six swaps and restore the five originals while removing compat. Host seams cover only macOS stat formatting, ownership and SELinux utilities; they are not OH validation.

Reproduce locally from a checkout containing the pinned T18 donor:

```sh
python3 benchmark/2026-10-20-t21-shim-deployment/derive.py --repo .
python3 -B benchmark/2026-10-20-t21-shim-deployment/test_executor.py
python3 -B benchmark/2026-10-20-t21-shim-deployment/test_shim.py
python3 benchmark/2026-10-20-t21-shim-deployment/executor.py preflight
```

No device call is made by these commands. After production freeze, outer must populate `shim-candidate.json` with the actual SHA and repository-relative production receipt pins, update its parameter/admission pins, obtain fresh admission and independently review the resulting delta. The CLI retains T18's `preflight|apply|rollback`, explicit `--execute`, `--repo`, `--inputs`, `--admission`, boot/parent/birth/holder/start/out bindings. Inputs add the flat basename `libwebview_bionic_shim.so`; the target remains nested under `webview-t-lib`. Rollback additionally requires the exact original `--apply-plan`; `--recovery-no-parent` is rollback-only. No current holder, boot or candidate authorization is supplied here.

`shim-target-evidence.json` distinguishes historical snapshot label/maps evidence from the baseline file SHA source. Neither historical metadata nor old process identities authorize a future window. Raw host checks and source pins are recorded alongside this file; playback and recovery acceptance remain human review.
