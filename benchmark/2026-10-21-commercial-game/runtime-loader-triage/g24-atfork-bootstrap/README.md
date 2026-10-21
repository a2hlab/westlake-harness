# G24 pthread bootstrap: what the exact loader establishes

Adding a shared SONAME does not by itself put that object's unrelated exports
into the relocation scope of a game which does not depend on it. This is the
additional issue beyond the two pthread-bridge files having different exports.
No old G16 packet, runtime, game, protection mechanism, or deployment is changed.

## Exact path and flags

The actual candidate is `libnativeloader.so` **878c7019**, not baseline b8be.
Its existing G18 build receipt binds unchanged registry/system-loader objects,
changed policy-bearing native_loader object, and the final774000-byte DSO.
This slice independently hashes that candidate and disassembles it:

| Object / PC | Operation |
|---|---|
| loader878c `0x5b80` | Registry calls ANL_CreateDomain (baseline's0x5b60 is stale here) |
| loader878c `0x65a8` | Registry calls ANL_Dlopen |
| ANLeebd `0x35dc` | indirect create_configured_namespaces host callback |
| host2a87 `0xceac` | bridge dlns_create2 flags1 / CREATE_INHERIT_DEFAULT |
| host2a87 `0xcefc` | dlopen_ns(bridge, bootstrap SONAME, flags2 / NOW\|LOCAL) |
| host2a87 `0xcfec` | app dlns_create2 flags4 / LOCAL_NS_PREFERED |
| host2a87 `0xd0fc` | app inherits bridge's configured shared SONAME set |
| host2a87 `0xd130` | ordinary app inherits resident compat separately |
| host2a87 `0xd190` | conditional native/Flutter ABI publish, flags0x102 / NOW\|GLOBAL |
| host2a87 `0xd5bc` | ordinary app library open; caller GLOBAL mode rejected earlier |

Candidate header:14–58 sets bootstrap `libwestlake_bionic_pthread_bridge.so`,
bridge search/permitted paths `/system/android/lib64:/system/lib64/platformsdk`,
and includes that bridge among eight shared names. Registry:215–247 copies the
fields; ANL:395–427 passes them unchanged to the host and retains bootstrap_handle.
Host source:184–230 opens by **bare SONAME**, resolves `WLPB_InstallHostOps` on
that handle and calls it. App inherits this bridge at329–334. No explicit route
pathname occurs in that bootstrap open, and no atfork capability check occurs.
Both db31(system) and cce31(route) export the installer; only db31 exports atfork.
Installer success cannot distinguish these capabilities.

## What can and cannot select system versus route

The archived OH6.1 linker source `oh61-dynlink.c:1927–1949,2029–2050` checks an
already-loaded object in the namespace, then a shareable inherited owner, before
opening search-path files. Bridge creation inherits default and does **not** set
LOCAL_NS_PREFERED. Thus, if a shareable same-SONAME object is resident in default,
it can win before the system directory. If there is no eligible resident object,
the configured first disk root is system/android/lib64; there is no literal
route search root in this policy. Route presence in another namespace or maps
alone is insufficient. The initial loaded-object/owner state is not encoded in
878c, and this source snapshot is not proven byte-reproduced against G24's loader
libc. **Actual bootstrap winner remains UNKNOWN**, for a specific reason rather
than a generic request for more maps.

A second, independent issue remains even if the selected file is db31:
bootstrap open is LOCAL. Game's exact DT_NEEDED set does not include the bridge.
Archived linker:737–762 restricts relocation scope to global or accessible
current-dependency DSOs;3508–3535 temporarily adds dependencies then reverts
LOCAL additions. Therefore shared-name inheritance alone is not evidence that
atfork participates in game relocation. Another prior GLOBAL load could change
this state. Do not claim the LOCAL call is the uniquely proven runtime cause.

## Provider source and real build chain

`provider-build-chain.json` pins the actual local N4 original `native_abi.c`,
stdio TU, version script, `build-abi.sh`, original build log and output. The local
output independently hashes to **d2053066**. Source forwards three callbacks to
pthread_atfork, preserves its return, and drops the DSO handle. Version script
exports LIBC; exact ELF disassembly from the preceding immutable addendum agrees.
The original recipe uses its frozen clang-15/sysroot, O2/g, explicit two-TU compile,
version-script, SONAME, -zglobal, -zdefs and libc/pthread links.

Existing U14 reproduction records two554bf6bc builds with equal allocated/code
sections and path/debug differences versus d205; it is **not** byte-identical
reproduction. Those raw logs are referenced, not newly executed. Current full
compiler/sysroot hash closure was not revalidated. The db31 standalone bridge's
exact source-to-output recipe is not closed in this bounded local slice; the
current same-named bridge TU cannot substitute for it. None of these limitations
justifies an empty atfork stub or importing Boat C7/C4 behavior.

## Minimum candidate proposal (not implemented or approved for deployment)

Prefer a new **one-export LIBC atfork compatibility leaf** plus one explicit host
publication seam after app namespace creation/inheritance, rather than promotion
of all d205/native-cluster exports or the whole pthread bridge. Reuse the existing
three-callback forwarding implementation and version-script pattern, not its
stdio/property companions. Use a new SONAME, exact provider path, NOW|GLOBAL only
at the existing internal host seam analogous to0xd190, and an exact reviewed
capability predicate for this app domain; leave ANL's native-cluster selector,
bootstrap flags and all other domains unchanged. Do not relax the public
StockOpenNamespace prohibition on caller-requested GLOBAL.

This is a **conditional proposal**, not a ready binary: the existing forwarding
implementation drops DSO unregister ownership. A retained-callback lifetime
contract is required before reusing it; unload/fork-after-unload cannot be marked
supported. A broader faithful unregister implementation is outside this slice.
Also prove the platform's namespace/symbol-visibility behavior before claiming
GLOBAL publication is confined to the intended domain; a negative unrelated-domain
test that leaks the symbol rejects this proposal. Existing provider bytes alone
are not a substitute for those tests.

The proposed change set is a new `atfork_compat.c`/LIBC map, one derived host
publication seam, and its source/build pins. No game bytes, loader policy widening,
GLES rewrite or native-cluster membership change. Expected first-fatal mover is
**genshin: __register_atfork relocation** only; subsequent game behavior UNKNOWN.

If one normal-run observation is needed, record **the existing bootstrap handle's
WLPB_InstallHostOps resolved owner object** (path+SHA+dev/inode+namespace, same child
identity) from an already available normal loader receipt. It distinguishes the
opened object without treating maps as winner. This report supplies no hook,
injection, new device window or first-launch orchestration.

See `counterexamples.json` for the minimum future offline/runtime proof matrix.
No counterexample execution or candidate build is claimed here. New work used
local source and exact ELF only; no VM/remote operation, device, or fresh REA.

## Version-predicate correction (v2)

The v1 wrong-version case incorrectly grouped an unversioned provider with an
explicit non-LIBC version mismatch. **Candidate admission still requires an
explicit LIBC export**, but that is our candidate criterion, not proof that this
linker always rejects unversioned symbols. Archived `oh61-dynlink.c:474–479`
accepts missing versym/def when `verinfo.v` is empty;1066–1076 initializes that
string empty and does not populate it on the use_vna_hash path. The platform
negative case therefore uses an explicitly non-LIBC mismatched version.
Unversioned behavior on the deployed platform remains unverified; no new platform
experiment was run. See `version-correction.json` for the exact source hash and
excerpts. All other proposal cases and source/ELF conclusions remain unchanged.

The complete v1 packet remains in the outer-verified hw248 archive SHA256
`e5cd3558d168ea654011fcb90b6564120eda473453b5355ae20d606c2ae512d9`.
This correction does not rewrite that archive or the earlier atfork-addendum.
