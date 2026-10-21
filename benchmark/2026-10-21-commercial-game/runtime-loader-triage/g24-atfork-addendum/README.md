# G24: the observed atfork relocation failure

The new evidence is a **versioned relocation failure**, not proof that no public
implementation exists. No game, protection mechanism, runtime, or device was
modified by this analysis. Earlier G16 verdicts remain unchanged.

## Observed evidence

`log-excerpt.txt` retains original line numbers from the private full log:
- L3135–3162: MHYComboCrypto `__errno` failure is caught and execution continues.
- L3276, 20:35:55.798, PID31523: `libyuanshen.so` cannot resolve
  `__register_atfork` (`use_vna_hash=1`, `van_hash=50d63`).
- L3277–3280: Unity cannot load yuanshen, then libmain lookup fails in
  `westlake.anl.app.31523.2`. This namespace is explicit for **libmain**;
  the preceding yuanshen relocation line itself does not print a namespace.
- L3682 and L3733: Unity JNI remains unbound, followed by exit1 at20:35:56.182.
  The nearby EGL layer warnings are not established causes of this exit.

The exact official APK SHA and its extracted member were independently hashed.
`libyuanshen.so` is SHA3dd8a20da6c1f11b966ae2b260cf1dd09b6667609f435a5b1bc05887c46b2a29,
361798968 bytes. Dynsym index3 is GLOBAL FUNC UND `__register_atfork@LIBC`;
version needs index2 is LIBC from libc.so. It directly needs libc.so, not either
Westlake provider. Reused G04 Unity loadLibraryStatic Evidence establishes
catch/false and fallback behavior, not successful native loading.

## Existing providers, not a new implementation

| Local exact object matched to this apply plan | Dynamic symbol | Meaning |
|---|---|---|
| native_abi d2053066 | `__register_atfork@@LIBC`, VA0x2454 | logs then tail-calls pthread_atfork at0x24a8 |
| system pthread bridge db31d6d8 | same version, VA0x2db8 | one tail branch to pthread_atfork@plt |
| route pthread bridge cce31e65 | no atfork import/export | same SONAME is not same capability |
| bionic_compat b8a87f6f | no atfork import/export | adding an unversioned assertion about this object is unsupported |

These are archived ELF bytes matching the current transaction's expected hashes,
not a new read of PID31523's mapped objects. `apply.json` verifies a different
control child30231. `game-observe/identities.json` is empty. No game-child maps,
bootstrap-handle identity or symbol-resolution record is available in the supplied
slice. **The selected pthread bridge/namespace instance remains UNKNOWN.**

Candidate loader policy includes pthread bridge and GLESv2 in the shared names;
source-index records its exact header. Archived `n4-host.c:184–230` opens the
bridge by SONAME and installs WLPB host ops; that does not prove the object also
exports atfork. `n4-host.c:263–291,345–358` publishes native_abi only in selected
private native/Flutter paths. ANL source `app_native_loader.c:60–76,447–475`
selects exact package components, not all Unity games. These source references
explain the scope distinction; they are not a new reproducible build or a live
winner measurement. Prior call-chain evidence still applies.

## Boat/public reuse and semantic limits

Reuse the prior 11-row Boat/public matrix. The public Unity libc source
`unity_libc_stubs.c:84–97` and native_abi source:10–17 forward three callbacks to
pthread_atfork and return its real result; this is not a success-only stub.
The exact two ELF functions agree with that forwarding mechanism. The fourth
DSO handle is discarded. The recorded U15 semantics review:92–105 explains that
this omits per-DSO unregister-on-dlclose; callback lifetime must remain valid.
No evidence here establishes Genshin's future unload/fork behavior or a Boat
atfork-specific runtime acceptance. Boat's graphics/audio successes and private
C7/C4 patches do not supply that evidence and are not transferred.

## Smallest next question

The observed first fatal key is **genshin**, now at LIBC atfork resolution. The
minimum next static/public-provider work is to reconcile bridge bootstrap owner,
its versioned exports, and the app namespace inheritance edge. An already saved
PID31523 provider map/proc-root hash or bootstrap-owner receipt would distinguish
route cce31 from system db31; maps alone still would not establish the resolution
winner. Do not replace either alias or add Genshin to the broad native cluster on
this report alone. A scoped compatible provider could move this one relocation
failure; next failures, game rendering, gameplay and audio remain UNKNOWN.

Local sources and exact artifacts were sufficient; no VM/remote search, fresh
REA, hook, injection, production build or device call was needed. Five prior method Evidence
hashes were checked. Original G16 lint is100%; warnings are preserved. This is a
static addendum, not a completed runtime acceptance.
