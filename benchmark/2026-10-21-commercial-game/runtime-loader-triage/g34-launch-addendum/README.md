# G34 launch: signal11 after graphics progress; fault site unknown

The first confirmed terminal record is **hilog L3791, 23:22:11.437**: parent27555 reports child29761 exited with signal11. This is neither the prior relocation/Unity-nativeRestart exit1 chain nor proof that the last graphics warning caused the crash. The supplied 664,781-byte hilog SHA is `4ab5cf4964011c89cfb90e35065f6d28c362add3eee4de50cf2a15903fff1da2` (3,797 lines, collection rc0).

## What progressed, and what did not

- Prior `_ctype_`, strtoll_l/strtoull_l and atfork relocation errors, and `nativeRestart` text, have zero matches in this supplied child log. This is a scoped observation, not full compatibility or binding proof. Earlier caught background errors remain excluded from diagnosis.
- TID29854 logs the absolute `/system/lib64/libGLESv3.so` accessibility/header failure at L3627–3630, followed by66 wrapper errors. It then logs window-surface handling at L3704–3707, Mali `glLinkProgram` at L3727 and swap-wrapper activity at L3735–3737. Redacted pointers/return values do not establish a successful surface or swap.
- TID29858 continues Unity-tagged output through L3784; its message bodies are `<private>`. L3785 reports an absolute libc accessibility warning in `westlake.anl.app.29761.3`. Neither this warning nor temporal proximity identifies a crash caller/PC. The faulting thread is unknown.
- Both images were actually read: first is white content/system bars; later is the launcher. No game frame. The custom `record.json.captured` list contains2 entries. `facts.txt` preserves the generic tool's actual 0/0 output for this incompatible record schema; it is not rewritten into an alive count.

## Source-supported public clues, not a diagnosis

Existing public `egl_wrapper_entry.cpp:301–353` has `FindBuiltinWrapper`: on AArch64 it tries the absolute GLESv3 path, logs the exact warning and returns null on failure. `EglGetProcAddressImpl` then attempts `GetProcAddrFromDriver` and the dispatch-table fallback. Thus the warning does not by itself imply final null dispatch. This is a retained source implementation, **not newly established byte-for-byte identity with the current deployed EGL**.

Existing `flutter_egl.cpp:103–140` shows the public window wrapper resolving the real entry, optionally unwrapping ANW and logging the return. The current log reaches analogous messages, but its values are redacted. Boat's public Surface/ANW/JNI mechanism remains a comparison source requiring owner/ABI binding; Boat private C4/C7 changes and its successful scene/audio are not imported as Genshin evidence. Original source lines and hashes are in `public-source-clues.json`.

## Early maps and missing crash evidence

The stat bookends retain PID29761/PPID27555/birth2248607. Maps were collected at23:22:09.824, before the graphics events and terminal. They already contain platformsdk EGL/GLESv3 plus two ANL/nativeloader path regions, but no libyuanshen/native-ABI pathname at that moment. This does not mean those later loads failed; it cannot choose their final namespace winner. No mapped-file SHA/dev-inode-to-file binding accompanies this slice.

The later `temp` and `faultlogger` listings contain no29761/Yuanshen match. **The Dfx query did not produce an empty successful log**: its57-byte stdout says `Mutlti commands can't be used in combination [CODE: -31]`, despite outer rc0. Dfx coverage is therefore unavailable. Preserve the failed query.

The smallest next normal diagnostic evidence is an existing matching cppcrash/fault record containing fault TID, PC/backtrace and module identity. If normal archived diagnostics are queried again, the captured help supports a single bounded tail form, `hilog -z 2000 -T DfxFaultLogger` (omit `-x`; not executed here), and body-level errors must be checked. That query might still find nothing and does not substitute for a stack. No game rerun, signal handler, hook/injection, protection analysis, candidate change or implementation is proposed. Current first-fatal **cause remains UNKNOWN**.
