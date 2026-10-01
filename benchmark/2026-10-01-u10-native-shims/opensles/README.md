# OpenSLES forwarding admission: direct casts are rejected

The earlier assumption was that resolving `slCreateEngine` and an OH IID was
enough for an Android facade. The exact owner ELF disproves that assumption.
No always-failure engine stub or unsafe facade is delivered here.

## Pinned read-only artifacts

Outer pulled these from 5ea's signed U9 (`a8cb9a5a45a6`):

| File | SHA256 | Defined dynamic symbols |
| --- | --- | --- |
| OH `/system/lib64/libOpenSLES.so` | `05d8ac90dbced47c8b47275a5d978bc922d4d8f6f84cd3df1b456633ae6d1100` | 140: 122 global, 18 weak |
| Westlake `/system/android/lib64/libOpenSLES.so` | `5891f899c2b21dcb24fa2f4cb3db78fbb34597740600c096dd8f633b831c5347` | 4: two Android IIDs, `_init`, `_fini`; no engine |

The originals, dynsym/dynamic dumps and `SOURCE.txt` are retained at
`$WORKSPACES/westlake-inputs/oh-system-libs/opensles-5ea-u9/`.
`inspect_opensles.py` rejects any other owner SHA and derives all 140 rows.
The **46 public entries** are 45 `SL_IID_*` values plus `slCreateEngine`;
the other 94 are implementation/CFI/C++ ABI details, not additional OpenSL APIs.
An export count must not be confused with supported interface capabilities.

## Binary facts, not SDK guesses

- `SL_IID_ENGINE` points to 24 bytes at `0x5d60`:
  `60c2978d00000000d4dddb118f950002a5d5c51b00000000`.
  `time_low` occupies eight bytes; Android's GUID occupies sixteen overall.
- `slCreateEngine@0x14350` is `b 0x14118`, reaching a real constructor with
  `calloc`, `IObjectInit`, `IEngineInit` and a returned object. It ignores
  option/interface parameters in this owner; that does **not** prove the
  returned interface ABI compatible.
- Object initialization at `0x13a4c` installs the `0x15ab0` vtable.
  Its GetState entry reaches `0x13a7c`, and **`0x13a88: str x8,[x1]` writes
  eight bytes** to the caller. Android provides a four-byte `SLuint32` output.
  A direct cast can overwrite the adjacent caller bytes even without options.
- GetInterface compares owner IID **pointer identity** at `0x13ab0`, not GUID
  contents. Copying a GUID into a facade is insufficient; requests must rebind
  to the owner's actual IID pointer before invoking it.
- `SL_IID_OH_BUFFERQUEUE` and standard `SL_IID_BUFFERQUEUE` have equal 24-byte
  values. OH callbacks have a third buffer-size argument. Android simple-buffer
  queue callbacks require a typed wrapper, not a function-pointer cast.

The user-nominated frozen target headers agree:
`$WORKSPACES/westlake-harness-bms-deploy/bms/src/.work/b87-native/replay-inputs/frozen-sysroot/usr/include/SLES/OpenSLES_Platform.h:40`
defines `sl_uint32_t` as `unsigned long` (eight bytes on AArch64).
This corroborates the ELF; it is not substituted for the ELF evidence.

## Decision and unfinished work

Mindustry's relocation remains a genuine missing-entry wall. Moving it safely
requires an Android-width facade around the real owner: 32-to-64 input arrays,
engine options, PCM/locator structures, IID pointer rebinding, 64-to-32 output
temporaries with overflow checks, object/interface vtable wrappers, and queue
callback/lifetime conversion. The original Android configuration IID is not
an OH capability and cannot be advertised as implemented without evidence.

Outer is obtaining the matching OH 6.1.0.31 source. Until implementation and
host canary/real-owner dispatch tests are complete, `composition.json` marks
OpenSLES **held**, and the complete batch remains `rollout_ready=false`.
The ABI evidence test is not a facade acceptance test; dependent task t3's
engine-forwarding scenarios remain unfulfilled and are not run as accepted
selectors. Task t2 admits only the verified policy/visibility and layout evidence.
No board change was made.
