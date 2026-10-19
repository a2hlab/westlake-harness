# Historical factory logs: useful correlation, unresolved lifetime

The missing step was checking retained factory logs before requesting another device observation. Two historical child logs already correlate a factory output with player `init` by numeric pointer. However, the later R10 read of that same address does **not** have the expected wrapper head. These records do not close object lifetime, current lock argument, or namespace/winner identity.

This is read-only evidence reuse: **0 device commands, 0 new REA calls, 0 production changes**. Original inputs and command receipts are SHA/size indexed in [source-index.json](source-index.json); selected original log lines are in [positive-excerpts.txt](positive-excerpts.txt). Neither excerpts nor this report substitute for original logs.

| Historical case | Factory and player lines in `child-full.stderr` | Identity and timing | Counterevidence / limit |
|---|---|---|---|
| `video-r10-play1` | 67874: native object `0x7d65581c90`; 67875: output `0x7fa995fba0`, `prewrapped=0`; 67881: player init same pointer, width/height 0, format -1 | Boot `34309d1e-48b0-47c7-b8b1-732cdd7bce02`; parent 5160, child 7080, child birth 9491; factory lines before baseline 156109 | Later `video-r10-window-state/reads.json` reads address `0x7fa995fba0` as `0x7fa717dc14`, mapped in `libicuuc.so`, not expected wrapper magic. Same recorded boot/child/birth. No valid-wrapper continuity established. |
| `video-r9-retry-play1` | 104079: native object `0x7dc4b5a510`; 104081: output `0x7f0eb7e150`, `prewrapped=0`; 104085: player init same pointer, width/height 0, format -1 | Boot `b14884be-467f-4e6c-b140-03fd8e76a6db`; parent 5058, child 6951, child birth 9057; factory lines before baseline 240864 | Historical correlation only; no synchronous object inspection or current object evidence. |

For each case, `commands/command-00175.json` records successful `hdc -t 61b0657200000000000000000324012c file recv /proc/<parent>/root/data/service/el1/public/appspawnx/adapter_child_<child>.stderr child-full.stderr`. `child-before.stat` / `child-after.stat` and commands 00011/00163 preserve the same child birth. The R10 receive receipt finished at `1792438350.550619`; the later head read command 00055 finished at `1792438507.455435` (about 157 seconds later). The read receipt guards parent/child births and parent relationship; its original stdout contains `0000007fa717dc14`. This is not a contemporaneous factory/lock observation. Release, reuse, and any other explanation remain unproven; no crash/damage cause is diagnosed. `p=4` in `WL-TTLOG` is priority, not PID.

## Exact file instruction evidence

Input HWUI SHA256: `a11c9154ca16dd7acf5e3ea99727ae37c25b1b4494a9133816bc58c553c128e2`. All PCs here are **ELF virtual addresses**, without a Ghidra imagebase. Existing original LLVM is `$HOME/.local/share/westlake/toutiao-resume-20261020/r10-window-source-independent/hwui-anw.stdout`.

`ANativeWindow_fromSurface` starts at `0x807238`. At `0x80735c` it calls `oh_anw_get_oh@plt`; `0x807360/0x807364` convert the non-null result to the `prewrapped` flag in `w21`. For a null result, `0x8073cc` calls `oh_anw_wrap@plt`, and `0x8073d0` saves that return into `x20`. Output logging passes `x20` as pointer (`0x8073e8`) and `w21` as flag (`0x8073ec`) to `fprintf` at `0x8073fc`, using format at `0x28b91a`. Therefore **in this exact implementation, the logged non-null `prewrapped=0` output is the return value of the wrap call**. It does not prove the runtime PLT winner or object validity.

All 6 exact log formats, ELF offsets, original bytes and hashes including NUL are in [exact-log-formats.json](exact-log-formats.json). The native-object format is at `0x29fb65`, printed at `0x807464`. The counter comparison at `0x80725c` and branch at `0x807260` gate logging after count 15 (normally first 16 calls from zero); races and separate loaded copies are not excluded. Missing later messages do not prove missing execution.

## Search boundary and remaining evidence

The bounded R8/R9/R10 search selected 82 existing directories under BASE19 plus two specified R10 BASE20 directories, 18,073 text/stdout/stderr/log files totaling 316,619,427 bytes. `rg` returned rc 0 and 374 matching lines in 18 files. These include overlapping stderr snapshots and derived selections; **374 is not an event count**. Exact scope, argv, receipt and the full input SHA index remain under `$HOME/.local/share/westlake/player-factory-log-reuse-20261020/`.

Follow-up was restricted to the two tabled original `child-full.stderr` files: `[WESTLAKE-NATIVEWINDOW]` occurs **0 times in each**, hence no same-pointer `fromSurface`/`lock` line of that tag was found there. This is a scope-bound negative, not an execution verdict.

The positive records support historical factory execution and subsequent player-init numeric correlation. They have no caller PC or TID and cannot prove the same invocation/thread, a continuous live object, all writers, current draw/lock object, or actual namespace/dlsym winner. The useful next evidence, if needed, is **same-call live identity** linking player factory return, stored field, lock argument, and object bytes with precise library/callee mapping. Repeating the already evidenced historical factory existence would not close that gap. No playback acceptance is claimed.
