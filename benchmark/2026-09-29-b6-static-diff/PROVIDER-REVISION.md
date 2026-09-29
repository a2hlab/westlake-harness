# Corrected provider comparison: 80c9aee0 → 8d109259

Task 56 supersedes every provider restoration judgment based on 977fb347. Full paths/SHA-256 are in `results.json:1`; both child manifests now match the compared providers (`provider-baseline-caveat.json:1`). Host and child evidence remains byte-identical (`host-child-preserved.json:1`). No device or external source changes.

## Required corrections

| Question | Correct sealed R155 evidence | Judgment |
|---|---|---|
| Must +112/+120 be zero? | **No.** R155 loads each field and branches to failure on zero. Old routine starts `evidence/runtime-provider/r155/disassembly.txt:7435`; NEW `evidence/runtime-provider/new/disassembly.txt:9344`. 93 normalized instructions match. | Preserve both mandatory nonzero fields, also +104 sealed-open. Withdraw prior inversion/zeroing advice. |
| Does R155 call WLNL_InstallSealedOpenV1? | Yes, installer at old `disassembly.txt:5879`, with service field +104. Success precedes release publication of READY. NEW calls it in Constructors at new `disassembly.txt:8161`. | Restore installer timing, failure propagation and one owner. The import/call was moved, not globally removed. |
| Namespace getter signature? | Old getter at old `disassembly.txt:7952` has two outputs, NEW at new `disassembly.txt:9854` has three. | Restore signature/callers with install timing. Internal registry offsets differ from public service table offsets. |
| Non-zygote, Typeface and deferred adapter init new? | All already present in 80c9. Old CreateChildVm passes w1=0 (`disassembly.txt:7332`). ChildMain differs only in one relocated reference to the same nativeWarmUpCache string (`provider-focused-evidence.json:1`). | Keep these R155 behaviors. No zygote/postFork restoration. |
| Actual VM initialization differences? | Old verified bridge → register natives → cache refs in startVm at old `disassembly.txt:1261`, `:1264`, `:1267`; NEW moves latter calls to preload and adds javacore bootstrap/abort option. | Restore phase/order with dependencies; retain verification, avoid double registration. |
| Environment/resource setup? | Old constructor at old `disassembly.txt:6918` contains DEX2OAT/I18N/TZDATA/ICU setup and RLIMIT_STACK; 16 MiB soft/hard constant at VA 0x5da0 (`provider-focused-evidence.json:1`). | Restore setup before construction/VM; candidate RLIMIT_CORE infinity is not equivalent. |

The abbreviated `old/new disassembly.txt` cells above mean `evidence/runtime-provider/{r155,new}/disassembly.txt`. Complete source edits and group dependencies are in `RESTORE-PLAN.md:1`.

## Dynamic metadata, ABI and strings

- NEEDED adds `libwestlake_art_abort_bridge.so`, `libbase.so`; removes **libopenjdkjvm.so**. R155 order is preserved verbatim in `evidence/runtime-provider/r155/dynamic.txt:3`; NEW in `evidence/runtime-provider/new/dynamic.txt:3`. Restore with VM/protocol changes. SONAME, absent RUNPATH, BIND_NOW/NOW flags unchanged.
- Imports add `__cxa_atexit`, `abort`, `bcmp`, `clock_gettime`, `westlake_art_copy_fault_message_for_abort_logging`; remove `access`, `getgid`, `getppid`, `getrlimit`, `stat`. Export adds `WLAR_PrepareA02PrerequisiteBundleV2`, no export removed. Restore imports/exports with their owning protocol, stack/environment, diagnostics and abort changes; never edit a symbol list independently. `evidence/runtime-provider/metadata-diff.json:1`, `versioned-symbols-diff.json:1`.
- RELATIVE relocations **7→8**; GLOB_DAT **10→10**; ABS64 **1→1**; JUMP_SLOT **69→69**. Equal counts do not imply equal targets. No PT_TLS. The V2 global Context constructor is added to init_array; fini targets preserve order. `evidence/runtime-provider/{r155,new}/inventory.json:1`, `relocations.txt:1`.
- Printable-run deltas **614 added / 409 removed**, of which allocated **47 / 59**; every run has a bounded disposition in `evidence/runtime-provider/strings-diff.json:1`. Many are non-allocated compiler/symbol/debug names, others are protocol/environment/diagnostic strings. They are not all configuration keys.

## Every function covered

R155 **86** defined function records, NEW **99**: **53 normalized equal, 14 changed, 32 added, 19 removed = 65 differing records**. PLT/init/fini linker blocks are supplemental, not included in the 65. All executable bytes decode; no uncovered instructions. `results.json:1`, `evidence/runtime-provider/{r155,new}/coverage.json:1`.

`ALL-FUNCTIONS.md:1` and `function-assessments.json:1` provide each differing function's raw line references and disposition. Unchanged records remain in `evidence/runtime-provider/functions.json:1`. V2 helpers/lifetime callbacks revert with the owning G1/G2 protocol; JNI/startup changes with G3. Verified-open/build-ID handling is retained as a deliberate verification change; address/constant relocation and removed local template throw helper do not independently justify rollback. Static code equality alone does not prove data/binding/runtime equality.

R2: identities/inventories/observed instructions **verified**; inferred source restoration **partially**; device result/root cause **unverified**.
