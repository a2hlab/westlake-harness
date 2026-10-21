# G30 locale ABI offline candidate

G28's observed first terminal relocation error was `_ctype_@LIBC` in libyuanshen, followed by Unity main-load failure, unbound JNI and exit 1. Earlier MHY `__assert2` did not terminate that sequence. This candidate addresses the existing locale ABI cluster in the already selected native ABI owner. It does not change G26 host/ANL, selectors, namespaces, runtime/audio publication, game code or protection. Expected first-fatal key: **genshin**, a prediction pending normal runtime verification.

## Actual outputs

| Object | SHA256 | Bytes |
|---|---|---:|
| Exact original baseline | d20530661a30b8af7bbfb30a6b7138d0b6a6bb5d82e6cb8d733a41ae23886c65 | 39520 |
| Candidate (two identical builds) | 4296f8052b6ccc130df83366717903695eba38fcde19c462ee64521414696f0b | 41984 |

Baseline and both candidate executions were performed by outer after an explicit VM execution handoff. The first inner entry timed out with rc124 and no compilation evidence; it is preserved and is not a compiler failure. The accepted baseline rebuilt both source objects and linked to the complete original SHA. No archived object was substituted. Candidate recompiles those two objects, requires identical hashes, then compiles the exact existing locale TU and links it as a third object. Baseline/current recipe and raw command hashes are in the public receipts and `raw-index.json`; original dual streams and rc remain private. No further build is required for this delivery.

Only the version script adds `_ctype_`, `strtoll_l`, `strtoull_l` under `LIBC`. `bionic_locale_compat.c` is byte-identical to the local historical module (SHA21e52d1e…), not copied with unrelated Unity stubs. Its upstream attribution remains a source comment, not independently verified AOSP bytes. Existing pthread-provider/bionic-provider disk exports were reuse evidence, not proof of the G28 winning namespace instance.

## Validation and limits

- 44 existing named dynamic-symbol tuples (type/binding/visibility/size/version/definedness) preserved. Exactly three exports added: 8-byte OBJECT `_ctype_@@LIBC`, and the two versioned integer functions. Only `strtoll`/`strtoull` imports added; NEEDED remains `libc.so`; NOW/GLOBAL/SONAME retained; no TEXTREL.
- Both original object hashes are identical. Constructor sequence remains `__do_init`, `westlake_map_simple_buffer_queue`; destructor sequence remains `__on_dlclose_late`, `__do_fini`. `.init/.fini` bytes are equal. This is static preservation, not a claim that OH callbacks were executed in this task.
- Real production locale TU, host-renamed solely to avoid libc collisions: all 257 table entries and 90 signed/unsigned cases pass, covering C/POSIX/ignored-null locale, bases, endptr, boundaries, overflow and no conversion. ELF also verifies the actual pointer relocation targets a 257-byte table with the same classifications.
- Real unchanged native TU with host dependency seams runs for baseline and candidate: constructor absent/null/present IID, atfork callback forwarding/return, FD set/is/clear, errno pointers. The production files are untouched. Stdio is preserved by exact source/object identity, not claimed as a new device-level test.
- Nine ABI guard cases include actual accepted symbols, wrong pointer size, array-vs-pointer/function, wrong/missing LIBC candidate version, unauthorized assert2 and old ABI drift. The candidate policy rejecting unversioned exports is not a claim that OH rejects every unversioned provider.

Host01 failed because the test expected errno unchanged for no conversion. Darwin's underlying conversions set EINVAL, and the wrapper did too. Host02 checks direct forwarding against the underlying function and passes; overflow still explicitly requires ERANGE. The production source did not change, and the failed test source and logs remain in the private index. Host execution does not substitute for OH runtime evidence.

Candidate01 recorded 55 inputs, some only after compilation. Candidate02 hashed all 55 before and after the same recipe, reproduced the identical candidate, and matched both input sets exactly. `input-closure.json` points to persistent copies of all 55 declared inputs, including original compiler/linker, actual headers, linker inputs and sources. **This is not a complete Linux OS image or host dynamic-library closure**; the configured tc/runtime directory did not exist. This limitation is retained, not hidden by the successful exact replay.

## Reproduce / review

Use `build_baseline.py --workspaces "$WORKSPACES" --out NEW_BASELINE` under the original Linux environment, then `build_candidate.py --baseline NEW_BASELINE --out NEW_CANDIDATE`. Output directories must be new. Original source/recipe/artifact pins and full SHA gates refuse drift. These commands are documentation, not permission to execute another build concurrently.

For public clean-checkout verification: `python3 benchmark/2026-10-21-commercial-game/locale-abi-candidate/check_delivery.py --host`, or Rust selector `commercial_game_locale_abi_candidate`. Host replay logs go to a new persistent `.private/replays/` directory, overridable by `G30_HOST_OUT`. These checks never call VM/device commands.

Status: **OFFLINE_CANDIDATE_VERIFIED_NOT_DEPLOYED**. Actual Genshin relocation winner, subsequent blockers and game frame remain UNKNOWN. No deployment permission, API freeze or game success is asserted. __assert2 stays excluded. First-slice source/owner reports and the rc124 checkpoint remain historical, unchanged.
