# 5EAB5 company-owned aperture fixture receipt

## Outcome

The disabled, company-owned AArch64 aperture fixture executed successfully on
D600-B `5eab586000000000000000001123012c` with SELinux Enforcing. Its internal
checks proved a non-zero OS-CSPRNG guard was written through the main ELF's
TLSLE-owned reservation, read back unchanged, had complete metadata staged,
and reached release-published READY exactly once.

This upgrades only the standalone mechanism fixture to
`device_verified_aperture_fixture=true`. It does not activate product code,
load an APK/Unity DSO, prove an issuer, or prove a first frame.

## Exact identities

- Boot ID before/after: `2e0a9ae4-6de5-439b-8d39-9c07d24b7cec`.
- SELinux before/after: `Enforcing`.
- Frozen project-local HDC SHA-256:
  `808b1606a4c28db9c378a88f12ebbf98d8d092d7ed6d105f019f589ac23b62ce`.
- Target Musl loader `/lib/ld-musl-aarch64.so.1` SHA-256:
  `316f70f2195b72aaf64e9f71e97d1d16cc25070f852f185994175893aeeeaa98`.
- Fixture backend SHA-256:
  `c0055d9e9be4559263279aaec5c8103b196f7e0541ea48423de5660837e55805`.
- Main owner fixture SHA-256:
  `d9559ae1c9e4497d427a247ea52cd13be05181281fa69bd0b7b72fd6c36d0144`.

Both sent files were SHA-verified on the target before execution. The exact
embedded interpreter is `/lib/ld-musl-aarch64.so.1`; the static verifier now
rejects any other interpreter.

## Proven

- Target execution returned `0`; HDC transport also returned `0`.
- The target main itself returns zero only when publication status/state are
  READY, the READY event count is one, guard is non-zero, readback equals the
  guard, and the offset/width are exactly `TP+0x28` / 8 bytes.
- The previously proven ELF contract remains: backend has no PT_TLS,
  constructor, TPIDR access, reservation symbol, global Musl stack guard or
  runtime dependency; the main addresses the reservation via TLSLE linker
  relocations rather than a literal TP offset.
- No CardWords, Unity or third-party DSO was mapped by the fixture.
- Boot ID and Enforcing state did not change. The cooperative lock and the
  fixture-owned `/data/local/tmp/westlake-wlaf-d9559ae1c9e4` directory were
  removed and independently checked absent after the run.
- `MANIFEST.sha256` verifies every captured input/result/raw evidence file.

## Failed history retained

The preceding run `20260712T220200Z` stopped before executing the target: it
found that the first fixture main embedded nonexistent
`/system/bin/ld-musl-aarch64.so.1`. That artifact was not accepted through an
explicit-loader workaround. The build was corrected to the same `/lib` Musl
identity used by the production generation, a verifier gate was added, the
fixture was rebuilt twice byte-identically, and only then was this run made.

The even earlier `20260712T215900Z` stopped before any device write because a
shortened serial literal did not match the exact 32-byte target identity. It is
also retained rather than rewritten.

## Not proven

- Real release certificate issuer, revocation and protected registry.
- Product appspawn call site and same-generation permit.
- Main, guest-created pthread, OH callback, pool, post-fork and signal entry
  coverage as one complete six-entry set.
- Complete initial/provider closure and zero TP unknowns.
- Stock OH sandbox/token/SELinux specialization, Unity load, Surface/EGL/RS
  present or a visible frame.

## Reproduce

```sh
RUN_ID=<new-immutable-id> \
  adapter/framework/native-compat/tests/aperture_writer_fixture/run_on_5eab5.sh
```

The runner defaults to the project-frozen HDC runtime, refuses a held target
lock, pins all three target ELF identities, and keeps all host evidence below
this project.
