# T29 owner extraction correction

ACK: checkpoint02 extraction and nine actual positive/negative tests passed rc0.
The old checkpoint01 extraction and outer rc1 rejection are preserved. Current
tests bind a private template snapshot; all 47 checkpoint02 manifest files remain
unchanged. No compiler/device invocation. Joint production waits for the outer
final consumer snapshot and review pins. See owner-extract-02/results.json and
preparation-raw-index.json.
