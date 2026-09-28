# Thread guard integration architecture

## Frozen Android semantic

```text
post-fork process epoch
  -> Bionic CSPRNG generates one canonical __stack_chk_guard
  -> main TCB slot 5 receives that value
  -> each later pthread TCB slot 5 receives the same value
```

This is source-proven by the frozen AOSP Bionic implementation and its
`same_guard_per_thread` test. Per-thread re-randomization is not Android
behavior and is killed by the host mutation gate.

## Three admitted paths

```text
fork child
  -> reset inherited registry
  -> stock OH DAC/sandbox/SELinux setcon
  -> verify binding + generate canonical process guard once
  -> issue MAIN ticket
  -> copy guard to current reservation / readback / READY
  -> ZygoteHooks.postForkChild + postForkCommon

APK namespace pthread_create bridge
  -> issue NAMESPACE_PTHREAD_CREATE ticket on creator
  -> real Musl pthread_create(adapter trampoline)
  -> new Musl thread resolves its MAIN-ELF reservation
  -> copy same process guard / readback / READY
  -> invoke original guest start routine
  -> retire only after guest frames and destructors are complete

OH-owned callback thread
  -> if already READY, verify receipt
  -> otherwise issue same-thread ADAPTER_JNI_ATTACH ticket
  -> copy same process guard / readback / READY
  -> JavaVM::AttachCurrentThread
```

## Ownership split

| Owner | Owns | Must not own |
|---|---|---|
| Musl | Real pthread, TCB, thread creation/destruction | Bionic semantic decisions |
| appspawn-x MAIN ELF | `[TP+0x10, TP+0x40)` address reservation and TLS relocation accessor | Entropy fallback or guest policy |
| process issuer | Verified OS-CSPRNG callback and sealed process/generation identity | Slot address guessing or Musl-global mutation |
| thread guard registry control plane | Fork reset, canonical process guard, tickets, process/thread states, receipts, revoke | TP register, pthread creation, signal chain, loader namespace |
| registry publisher backend | One validated slot write plus readback | Owner resolution, hard-coded TP offsets, alternate guard generation |
| APK namespace pthread bridge | Bionic pthread ABI translation and real Musl trampoline order | Global symbol interposition |
| app native loader | Guest namespace and READY gate before `dlopen_ns` | Thread creation or TLS layout |

The MAIN reservation is memory ownership, not semantics. The registry is the
semantic owner and includes the narrow write backend, but it may publish only
to an address resolved by the MAIN-ELF owner for the current thread and bound
to the verified generation/epochs.

## Fail-closed invariants

- No fork reset, verified binding, exact-quality OS-CSPRNG process sample,
  current thread ID, owner, exact offset/width, readback, or accepted receipt
  means no READY.
- The CSPRNG callback is called exactly once per armed process epoch. Ticket
  issuance and thread preparation do not generate guard entropy.
- Every READY thread must contain the same canonical non-zero process guard.
  A value differing from the registry's canonical guard rejects the process.
- MAIN and JNI-attach tickets are same-thread; namespace pthread tickets must be
  consumed by a different newly created thread.
- Tickets are one-shot. Cancel is permitted only to the issuer while ISSUED.
- A thread cannot hold two active receipts.
- READY is published after all receipt fields; acquire readers recheck state.
- Capacity is explicit and bounded; exhaustion denies guest execution.
- Retirement never overwrites slot 5 and is legal only after guest teardown.
- A process guard must never be changed from a stack-protected frame that will
  return. Frozen AOSP states this restriction explicitly.

## Product activation blockers

The standalone mechanism is ready, but the current product still has competing
legacy guard owners. `misc_compat.cpp` and `bionic_tls_abi.c` write the Musl
global guard, contain fixed fallback behavior, and the latter uses a constructor
and direct TP write. They cannot be part of the activated architecture.

The current Route-A source publishes a separately generated slot-5 value before
`ZygoteHooks.postForkChild`. Frozen AOSP proves that this Java/ART hook itself
does not call `android_reset_stack_guards`; the reset exists in the AOSP
native-fork child branch that WestLake's external appspawn route bypasses.
Therefore the immediate risk is not a second reset in that hook, but multiple
independent guard owners and failure to prove Bionic-global/slot equality. The
Route-A source also clears the guard's low byte, while this frozen Bionic version
fills all bytes from `arc4random_buf` or kernel `AT_RANDOM`; that drift must be
removed.

Activation also remains blocked until the APK namespace pthread bridge, central
JNI attach owner, and pre-guest-loader READY gate are in the same generation and
their binary call order is proven.
