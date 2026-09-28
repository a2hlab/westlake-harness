# Prepass context contract (SPC-52)

The existing `test/test_prepass_context_wire.cpp` is compiled unchanged with
assertions enabled and run as a separate executable by `SPC_52_Contract.Valid`.
It establishes the five context digests and legacy validator/status names. The
missing header had no tracked blob in the current git history; this restoration
fixes ABI version 1, size 856 and alignment 4 explicitly. It does not assert
binary compatibility with an unidentified external prebuilt context. Consumers
must negotiate version and size before reading a full object.

The five context digests are contract, policy, tool, topology and runtime
 generation seal. The sixth binding is the verified APK SHA256, passed separately
(as in the existing `test_install_prepass_materializer.cpp` call and the real
`PrepassBinding`/codec). `ValidateForApk` checks all six shapes;
`MatchBoundInput` compares them with an independently supplied trusted envelope.
No extra fixed profile, user, ABI, device or path is invented.

`Validate` reads an immutable, aligned full C object. At unaligned or sized byte
boundaries, callers use `ValidateBytes`, which checks the exact available length
before copying. Fixed identity buffers require nonempty NUL-terminated strings
and zero unused tail bytes; all reserved bytes are explicit and checked. Digest
buffers require 64 lowercase hex bytes plus NUL, while the separate APK digest
has an explicit length of 64 and does not require byte 65 to exist.

`MatchPackageUser` retains the old package/user gate. `MatchBoundInput` additionally
checks request and generation and all digests against trusted owner inputs. A
valid-looking digest does not establish a profile's provenance. These functions
have no global mutable state, allocations, IO or installation side effects.
They do not authenticate the caller or replace the actual profile producer.

The C11 probe compiles the real header and links/calls the real C export; it fixes
size/alignment and each field offset. GTest invokes the original executable,
checks both shape and mismatched trusted input, unaligned copies, every shorter
byte length beside a real PROT_NONE guard page, and concurrent isolated requests.
No business decisions are copied into a test implementation.

The full context-to-prepass/legacy install assembly remains T-48's bound build
closure. This test runs the original context test, not the separate complete
materializer/host-install test. OH artifacts, CTS and ACTS are still external gates.
