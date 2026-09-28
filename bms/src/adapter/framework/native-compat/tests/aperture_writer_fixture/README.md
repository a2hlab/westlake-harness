# Disabled AArch64 aperture-writer fixture

This directory is the PR-08A **company-owned fixture**, not a product
activation path.  It turns the existing appspawn-x main-ELF TLS reservation
into a narrowly testable writer contract while the product audit core remains
incapable of issuing a load or aperture permit.

## Ownership boundary

- The main ELF remains the only address owner.  Its
  `WLAF_MainReservationBase` callback addresses
  `westlake_bionic_tls_slots_2_7_reservation` through AArch64 linker TLS
  relocations.  It does not contain a literal `TP+0x28` address.
- The fixture backend cannot see the reservation TLS symbol and contains no
  TPIDR_EL0 access.  It receives only the region returned by the owner
  callback and computes slot 5 as `0x28 - 0x10` within that exact 48-byte
  region.
- The backend accepts only `WlafFixturePermitV1`: fixture-only type,
  mechanism, non-zero one-shot nonce, target digest, generation, process
  epoch, policy epoch, offset `0x28`, width 8, and an externally verified
  signature field.  `WlncLoadPermit` from the audit core has a different ABI
  and cannot activate it.
- The guard value is absent from the permit.  It must come from the owner
  platform's OS-CSPRNG callback.  Callback failure, wrong quality/epoch, or a
  zero sample makes the consumed publication terminal; there is no fallback.
- The backend performs one AArch64 store and immediate readback, stages all
  receipt metadata, then release-publishes READY.  A second use of the same
  owner publication is rejected as replay.

The target fixture's `test_fixture_signing.c` is a typed test seal and embedded
test trust root.  It exists only to exercise the signature-verifier boundary;
it is not a production cryptographic signature, issuer, certificate, or
revocation implementation.  The ELF gate proves that neither this key nor any
`WLAF_*` fixture symbol/dependency enters `libwestlake_native_compat.so` or the
product appspawn generation graph.

## Target artifact policy

The fixture backend must have:

- AArch64 DSO shape and deterministic Build-ID;
- no `PT_TLS`, `.tdata`, `.tbss`, constructor/init array, runtime dependency,
  RPATH/RUNPATH/TEXTREL, TLS relocation, TP system-register instruction,
  reservation-symbol reference, or `__stack_chk_guard` reference;
- exactly one hidden slot primitive: `str x1,[x0]`, followed by
  `ldr x0,[x0]` readback;
- only two versioned public fixture symbols.

The main fixture must have the existing 48-byte/align-16 reservation and the
owner object must contain exactly the two linker relocations
`R_AARCH64_TLSLE_ADD_TPREL_{HI12,LO12_NC}` against the reservation symbol.
If that relation cannot be produced, the build fails; the fallback is never a
literal TP offset.

Three target mutants are required to fail: backend `PT_TLS`, backend
constructor, and a literal `TP+0x28` owner.  Four host semantic mutants are
also required to fail: READY-before-metadata, signature bypass, fixed guard
fallback, and owner-bounds bypass.

## Reproduce

From the project root:

```sh
adapter/framework/native-compat/tests/aperture_writer_fixture/run_all.sh
```

The host model, sanitizers, locked network-disabled AArch64 build, structural
gate, mutants, logs and SHA receipts stay below this directory's `out/`.
Passing this command is `build_pass/disabled_target_fixture`; it is never
`device_verified`, product load authority, or evidence that Unity can start.

After the exact device is reserved, the same company-owned fixture can be
executed without mapping any APK/Unity DSO:

```sh
adapter/framework/native-compat/tests/aperture_writer_fixture/run_on_5eab5.sh
```

That runner uses the project-frozen HDC client, pins the target Musl loader and
both fixture hashes, requires SELinux Enforcing and an unchanged boot ID, takes
an exclusive cooperative lock, and removes only its own `/data/local/tmp`
directory. A zero exit upgrades only the standalone aperture fixture to target
execution evidence; `product_activation=false` and `device_verified_product=false`
remain invariant.

## Five-stage acceptance position

| Stage | Fixture evidence | Product status |
|---|---|---|
| S1 admission | typed/signature callback and exact identity fields are negative-tested | real issuer/sealed certificate not integrated |
| S2 appspawn/main | generation/epochs, one-time state and value/metadata-before-READY model pass | no appspawn call site |
| S3 pthread | owner API is per-current-thread capable | namespace pthread bridge and thread matrix not implemented |
| S4 callback | same owner/epoch contract can be called at a boundary | callback inventory and six entry classes not implemented |
| S5 inline | one AArch64 slot store/readback and ELF/instruction gates pass | target execution, non-overlap and Unity are not proven |

The backend therefore remains unreachable from products until a later,
separately reviewed product permit issuer and all PR-00..07 entry gates exist.
