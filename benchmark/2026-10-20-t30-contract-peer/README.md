# T30 resource-free Request failure contract

T29's `window_module.c:112` routes every failed lock through `complete(...,0)`, setting `retained=1`; `r26_finish(...,retained)` then preserves FAILED, and the paired entry does not release its extra owner reference. This explains the persistent rejection after the observed Request failure, not the cause of that first provider error.

The new contract permits recovery only for a proven resource-free Request failure. The first scope requires nonzero Request, NULL buffer/native, no mapping, fd=-1 and no later provider phase. Returned buffers, any other fd and cleanup ambiguity retain the old conservative protection. Cross-layer completion must release only this reservation and its extra reference while preserving cached geometry ownership and the original error.

`specs/toutiao-t30-request-recovery/t1-recovery.spec.md` parses and lints at 98%. Six scenarios bind future real implementation fault-injection tests and a human-reviewed runtime sequence. No implementation tests, build or device operations ran. The real CC design was not yet present in its tree at this review; review of that actual design remains pending. Runtime needs moving video content before and after a switch; a run without the targeted error cannot prove its recovery branch.
