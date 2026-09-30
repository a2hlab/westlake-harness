# N7: explicit Flutter EGL owner routing, bionic additions and Realm zlib

N6 loaded an ABI provider but did not bind Flutter's EGL calls to it. N5/N6
LocalSend still called platform EGL with an Android window. Aegis U5 PID 22366
maps show platform EGL inode 4578, platform GLESv3 inode 4580, Android GLESv2
facade inode 98910 and Android HWUI inode 98782. There is **no independent
route-a libEGL wrapper**. The working conversion is in HWUI (and Java EGL JNI),
not in the platform driver's SONAME. The exact maps are archived in `evidence/`.

## Candidate

`<WORKSPACES>/westlake-generation-n7-fa9ec3c6`, manifest
`a77c7c6cfdc1c0f78a9f32dad2c184dabe049afedc9674774bd578fab1ab67ff`.
Eight payload paths differ from U5; `package.json` records every old/new SHA.

- Host `fa9ec3c6`: only the existing six-package Flutter branch removes platform
  EGL from inherited lookup, opens existing HWUI/platform EGL with NOLOAD, and
  binds a private EGL facade. No new HWUI or platform EGL may be loaded by this
  binding operation; missing owners fail closed. The native-cluster branch also
  inherits the existing sealed zlib owner for the Realm alias.
- ANL `5b21a875`, two aliases: N5 runtime visibility plus removal of the Flutter
  bridge's direct platform EGL inheritance. Non-Flutter bridge lists are retained.
- Private `libEGL.so` `6963d954`: all 20 direct EGL imports from all six engines
  are exported. Create/swap/damage call existing U5 HWUI function pointers;
  destroy and other EGL calls use platform EGL. `eglGetProcAddress` returns the
  facade for window functions (including damage EXT alias), forwarding other
  queries to the same platform owner. `-Bsymbolic-functions` keeps these returned
  addresses local. This is explicit routing, not a second copied ANW converter.
- `libbionic_compat.so` `99c51df8`, two aliases: exactly two new exports,
  `__gnu_strerror_r@@LIBC` and `android_dlopen_ext@@LIBC`; all 48 existing defined
  dynamic symbols remain. NEEDED order stays begetutil, libc++, libc. The accepted
  source files were copied unchanged into `bionic_compat/src/` and archived here.
- `libz.so` `50b9ab6a`, Android root and `westlake_native/`: original 1904-byte
  r109c alias, **SONAME libz.so, NEEDED libshared_libz.z.so**. LIBZ-PLAN's claim
  that the alias had no SONAME was incorrect. No OH file or SONAME is modified;
  existing route-a `libshared_libz.z.so` bytes remain unchanged.

GLESv3 continues to use the same inherited platform implementation as Aegis.
Flutter GLESv2 retains its existing empty SONAME facade with that GLESv3 NEEDED;
ordinary Android GLESv2 is an empty compatibility shell with only libc NEEDED,
so copying that file alone would remove Flutter's GL supply. There is no window
conversion to copy from either GLES2 facade. HWUI, runtime, ART, provider, bridge,
private ABI, JAR and boot images stay byte-identical to U5.

## Sources and build evidence

Searched local real-work/00.Workspace/Westlake, then the recorded VM Westlake tree,
then the two existing hw248 framework snapshots (read-only search receipt). No
verified Flutter-specific EGL facade was found. The existing boundary is
real-work `be16148da9ae7bb89c62e81e144ed0bceb5c4669`,
`src/adapter/aosp_patches/libs/hwui/hwui_oh_abi_patch.cpp` sections 4/5;
00.Workspace also has `code/adapter/westlake-piercing/ports/dayu600/gfx-smoke/egl_interposer.cpp`.
N7 calls the existing HWUI exports rather than recompiling either source. New
code is only the typed forwarding facade and its narrowly scoped owner binding.
Actual U5 exports are checked, including that eglDestroySurface is an UND import
in HWUI and must go to platform EGL.

The two bionic sources/test come from oc-t4
`westlake-harness-t4/benchmark/2026-10-01-native-symbol-clusters/bionic-compat-patch/`.
The actual build recipe is in `security_specialization/stock_child_plugin/`;
it lists seven existing compat translation units explicitly, not a wildcard.
`build-bionic.sh` copies that list and adds only the two accepted sources.
The alias recipe is copied from real-work `build_android_zlib_soname_alias()`.

Previously authorized direct VM builds use frozen OH clang `b107ce03`.
`build-inputs.json`, source snapshots, scripts and repeat logs preserve inputs.
Host, ANL, EGL and bionic repeat builds are byte-identical. Bionic disassembly
mnemonic comparison preserves 73 existing function/PLT sequences; only
`__emutls_unregister_key` differs (toolchain helper). This is not a full semantic
proof; raw disassemblies are archived. No BTI property is asserted without notes.

## Strict gates and one-time approval

N1 rejects 31, N2 rejects 154, with no invalid inputs. Against the same-checker U5
baseline, 126 findings are common and **59 new**: 3 existing-owner NOLOAD checks
whose owner reachability the static checker cannot prove, plus 56 cross-domain
NEEDED findings. `EXCEPTION-PROPOSAL.md` lists only new findings; JSON preserves
all original rows/IDs and both package/input bindings. No permanent registry is
changed. Source line-number shifts are normalized only for baseline comparison.

The raw dry-run refuses before board access. Outer ACK90 04:15 approved these
185 findings **once**, only this exact candidate, after U6 releases 5ea. Activation
requires a newly timed, board-bound receipt; this offline package does not grant
an unlimited deployment exception.

## Device acceptance still pending

Require actual N7 facade/HWUI entry in the Flutter raster path and movement of
its first wall, not just mapped exports. Require bionic/libz error disappearance
for Firefox/Fennec and McDonalds/Element. Initializer diagnostic noise does not
count as the first fatal exception. Compare five singleton-library inode counts
against same-board U5, retaining U5's known two-inode liblog baseline. Record
EGL/GLES and facade identities separately because the old short fingerprint
omits private directories. HW/ZZ/Aegis/Catima plus OONI/Auxio/Calendar/Markor are
controls; screenshots decide. Candidate must return to U5 runtime `73ecf422dba2`,
boot image `0876029078e2`, J6 `2488052f` and unlock within the scheduled window.

Host tests validate routing and 12 shim cases on Mac; they do not execute OH
musl namespace lookup or prove device rendering. Unknown-errno wording is libc
specific. Source and payload checks pass; runtime effects remain **unverified**.
