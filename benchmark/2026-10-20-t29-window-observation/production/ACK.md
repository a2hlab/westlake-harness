# T29 owner extraction correction

ACK: checkpoint02 extraction and nine actual positive/negative tests passed rc0.
The old checkpoint01 extraction and outer rc1 rejection are preserved. Current
tests bind a private template snapshot; all 47 checkpoint02 manifest files remain
unchanged. No compiler/device invocation. Joint production waits for the outer
final consumer snapshot and review pins. See owner-extract-02/results.json and
preparation-raw-index.json.

Entry rename complete: `check_prepare_owner.py` (9/9) and
`check_preparation.py` (8/8) both actually reran rc0. Source bytes unchanged.
Current raw commands: `.private/check-entrypoints-01/{owner,abi}.argv.json`.
No executable `test_*.py` is included in the current landing list.
