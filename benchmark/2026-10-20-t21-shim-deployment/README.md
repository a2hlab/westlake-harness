# T21: sixth-artifact shim transaction, candidate pinned; admission disabled

The T18 transaction does not restore or replace `webview-t-lib/libwebview_bionic_shim.so`. This mechanically derived executor adds that exact sixth path to the existing five-artifact set. Its baseline is `85c789f48b2bc0c31658c9dc591cd27784cc0ddfe559005e8d36d1d7d220476a`. The original disabled delivery remains at commit `16189607d80ba92e44bf17dbefc3bdda8bc21ec1`. Revision R2 pins the 70,184-byte shim `5cc23582d8cd8f28b24f89dc9bcf439de2177c0be33bb4783dd1baad3ab32eca` and seven source/build receipt references from production freeze `f1b8e20cfa65aa85bb87fbdd6127e0f6ed54e1b1`. **The admission template remains unapproved with no current identities or fresh metadata. This delivery removes zero runtime failures.**

`derive.py` requires T18 executor `57affbe0…` and emits `executor.py`; `changes.diff` records the complete delta. Existing Board, file/CAS/swap helpers, WID normalization, 1800-second limit and 600-second recovery reserve are preserved. The new shim has physical/private hash, fresh mode/UID/GID/label and same-inode checks. Rollback binds the original apply plan, candidate declaration and before/after hashes; foreign bytes are refused. Physical-only recovery still requires a fresh boot and outer namespace/UI verification.

Before the first swap, all **six preimages** must be durable: five verified file backups and a sixth `ABSENT` marker for the originally absent OpenSLES compat file. The shim swaps first; run.sh remains last. Tests execute the actual generated transaction with real copy/hash/rename operations, interrupt after each of six swaps and restore the five originals while removing compat. Host seams cover only macOS stat formatting, ownership and SELinux utilities; they are not OH validation.

Reproduce locally from a checkout containing the pinned T18 donor:

```sh
python3 benchmark/2026-10-20-t21-shim-deployment/derive.py --repo .
python3 -B benchmark/2026-10-20-t21-shim-deployment/test_executor.py
python3 -B benchmark/2026-10-20-t21-shim-deployment/test_shim.py
python3 benchmark/2026-10-20-t21-shim-deployment/executor.py preflight
```

No device call is made by these commands. Production pins are now frozen in `shim-candidate.json`; `freeze-r2.json` records the exact delta and checks. Outer must first land those referenced production files, obtain fresh admission and independently review the resulting delta. The CLI retains T18's `preflight|apply|rollback`, explicit `--execute`, `--repo`, `--inputs`, `--admission`, boot/parent/birth/holder/start/out bindings. Inputs add the flat basename `libwebview_bionic_shim.so`; the target remains nested under `webview-t-lib`. Rollback additionally requires the exact original `--apply-plan`; `--recovery-no-parent` is rollback-only. No current holder, boot or candidate authorization is supplied here.

`shim-target-evidence.json` distinguishes historical snapshot label/maps evidence from the baseline file SHA source. Neither historical metadata nor old process identities authorize a future window. Raw host checks and source pins are recorded alongside this file; playback and recovery acceptance remain human review.
