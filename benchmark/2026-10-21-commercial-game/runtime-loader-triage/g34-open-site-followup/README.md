# G34 libc open-site follow-up: one exact candidate, no crash attribution

The complete ordinary buffer is32,974,064 bytes/254,480 lines, SHA
`a5335168b89e8d5e8faec0a0fe6086e466e8b6b1dc5e2eb54d51cc9f891954e6`.
Line139118 at23:22:11.338 reports `/system/lib64/libc.so` inaccessible in
`westlake.anl.app.29761.3`, PID29761/TID29858. Parent27555 reports signal11 at
line139393,23:22:11.437. Neither record contains the caller/fault PC or a stack.
The99 ms proximity is not a causal link.

## Exact artifact observations

The361,798,968-byte libyuanshen.so was independently rehashed to
`3dd8a20da6c1f11b966ae2b260cf1dd09b6667609f435a5b1bc05887c46b2a29`.
Its exact `/system/lib64/libc.so` literal occurs once, at file offset/VA0x59e2c1.
A bounded ADRP+ADD reference scan found three candidates, then local LLVM objdump
checked only the associated small instruction ranges and normal API thunks/PLT:

| Reference / call PC | What is actually proved | Return handling |
|---|---|---|
| 0x6a114c8 / 0x6a114d4 | path in x0,mode1 in w1; thunk0x7a6ab3c tail-jumps to dlopen@plt0x14064520 | returned x0 is saved and passed unchanged to dlsym at0x6a114e8; no intervening NULL branch |
| 0x6a114e8 | thunk0x7a6ab54 → dlsym@plt0x14064530; symbol literal is `syscall` | result saved at0x6a114f0; later NULL check at0x6a116ec, then non-NULL storage at0x160b3358; eventual use unknown |
| 0x6b8da64 / 0x6b8da6c | thunk0x7a925d4 → realpath@plt0x14065020, with output buffer | a path API, not a library open at this site |
| 0x6b97928 | literal is stored into table entries | consumer and any later open remain unknown |

This is one **static candidate**, not an observed caller. Other computed/indirect
references are outside this bounded coverage. Nearest-symbol labels printed by
objdump are not accepted as recovered function names. No unrelated game logic
was pursued beyond the normal library/API boundary.

## Public compatibility chain

G26 candidate ANL source retains explicit NULL/error propagation: domain/mode/
readiness checks return NULL; the selected namespace open returns its handle,
and a NULL handle records dlerror before returning NULL. The exact fixed G34
rollout ANL ELF640b3c87 was hashed and its exported ANL_Dlopen disassembled:
indirect open at0x4230, handle saved at0x4234, NULL branch at0x4238, dlerror at0x4250.
This public wrapper does not establish that libyuanshen's internal plain dlopen
passes through ANL_Dlopen. Its PLT ultimately follows the bound provider, which
has not been observed at this call site.

The retained OH dynlink source selects an implicit namespace from the caller
address, checks absolute-path visibility, and has a separate default-handle
symbol lookup path. It is a historical source snapshot: its exact diagnostic
text differs from the current warning and its deployed binary identity is not
proven here. Thus even if the candidate dlopen returned NULL, passing that handle
to dlsym does **not itself prove a crash**; provider/default-handle semantics,
lookup result and subsequent use must be established separately. No claim is
made that the observed warning proves the final dlopen return was NULL.

Existing Boat-derived public native-cluster/Flutter search and namespace code is
reused as source context, not as Genshin success evidence. The five existing Java
REA method Evidence records were located and their original raw SHAs verified;
they cover startup methods, not this native PC. No whole-APK analysis was repeated.

## REA status and remaining decision

The current REA binary_session request was rejected before execution:
`MCP tool call requires approval, but approval policy is never`.
The raw refusal is retained. No provider switch, CLI retry, configuration change
or new REA analysis followed. LLVM static reads are the separately authorized
fallback; all11 objdump calls returned rc0 and retain argv/stdout/stderr privately.

Unknowns: actual warning caller PC, bound dlopen/dlsym provider, handles/results,
final result use, exact current OH loader source, faulting TID/PC/stack. Expected
**proven** first-fatal removals:0. No patch, path widening or game rerun is justified.

A next minimal experiment could be useful only as a separate public compatibility
fixture, after exact provider/namespace binding: compare the absolute libc path
and ordinary SONAME, recording normal dlopen/dlerror/dlsym results and provider
identity without invoking any resolved function. It would test compatibility
semantics, not identify this crash. It is a proposal only; no execution or new
window is requested by this package. Existing ordinary crash evidence remains
the best way to bind a runtime PC to a candidate.

All conclusions are scoped in `results.json` and `open-sites.json`.
Raw33MB buffer and361MB ELF are referenced by SHA, not duplicated into the public
package. No device/VM/game execution, runtime build or patch occurred.

Readiness token: **G34-OPEN-SITE-FOLLOWUP-READY**.

## Narrow NULL-handle follow-up

The actual retained OH libc input fd3c4701 has an explicit zero-handle default
lookup branch at0x89d9c, consistent with OH dlfcn.h:19 (`RTLD_DEFAULT=((void*)0)`).
This is binary evidence for that input, not yet proof of the crash-time provider.
The game result has a later NULL check at0x6a116ec; the non-NULL branch stores it
atglobal0x160b3358. No call through that stored pointer was established. The NULL
branch destination and later consumers remain unknown and were not expanded.
The new faultdirs-04 listings contain no29761 entry; their absence supplies no PC.
A game rerun/patch experiment is not justified by this warning. Ordinary crash
PC/stack plus exact provider binding take priority over another semantic guess.
