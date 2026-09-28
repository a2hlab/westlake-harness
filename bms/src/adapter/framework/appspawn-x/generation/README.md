# Frozen AArch64 appspawn-x generation producer

Status: existing immutable generation is `build_pass` only; the live producer
has advanced and requires a new intentional refresh/rebuild. Neither state is
deployable or `device_verified`.

The live source now additionally freezes/emits the canonical ARM64
`appspawn_x.cfg`, uses real zlib `adler32_combine` semantics, and carries the
AOSP-layout abort-message implementation as a separate reviewed source. These
changes are host/target-fixture tested but are not part of the SHA identities
recorded in `BUILD_RESULT.md`; that report remains the truth for the older
immutable generation.

The live source has also advanced to a Route-A receipt-bound admitted prepare
skeleton for the Bionic slot-5 path:

- the stock Route-A runtime provider owns
  `westlake_native_compat_prepare_main_thread(identity)`;
- legacy security-owning `ChildMain::run` must remain fail-closed and must not
  synthesize a MAIN identity;
- the current-thread reservation base is resolved by main-ELF TLSLE
  relocations, not a literal `TP+0x28`;
- guard publication requires OS CSPRNG and has no fixed/zero fallback;
- compat remains forbidden from becoming a TP writer.

These source changes are likewise newer than the frozen SHA identities recorded
in `BUILD_RESULT.md`. Until the closure is refreshed and rebuilt, they are
source progress only, not frozen-generation evidence.

## Boundary and evidence target

This asset touches the `appspawn-x`, `Permission/Security`, and `Bionic/Musl`
boundaries. It preserves the stock OH
`HapContext::HapDomainSetcontext(HapDomainInfo&)` specialization behind a POD
pure-C ABI wrapper and reserves the main executable's positive Bionic TLS
aperture. It does not modify ART, Android framework/BCP, the APK, musl, or OH
SELinux internals.

The static gate proves:

- every source/header/sysroot/library/config/tool input is copied below the
  current project and individually hashed before compilation;
- the final build container sees only that frozen closure;
- wrapper SONAME is `libwestlake_hap_domain_wrapper.so`, Build-ID is sha1,
  there is no RPATH/RUNPATH/TEXTREL, and its implementation calls stock
  `HapContext::HapDomainSetcontext`;
- appspawn-x pins that exact wrapper Build-ID, has a 48-byte/16-aligned PT_TLS
  reservation, and its unstripped sidecar with the same Build-ID exposes the
  reservation symbol;
- real OH link libraries are used; evidence-only link-interface stubs are not;
- the compat producer is the explicit reviewed source-set producer and contains no
  `bionic_tls_abi`, `unity_pthread_box`, `unity_signal_box`, `pthread_create`,
  or TPIDR_EL0 access.

It explicitly does **not** prove:

- a Bionic slot-5 stack-guard semantic writer exists (it does not in this
  producer);
- production-init/SELinux-Enforcing child specialization succeeds;
- any APK, ActivityThread, Unity native runtime, Surface, or first frame works.

## Reproduction

The import phase is the only command allowed to read external, read-only
origins. It records origin SHA256 and copied SHA256 for every file:

```sh
adapter/framework/appspawn-x/generation/import_inputs.sh
```

When the wrapper source or link closure changes, first obtain its deterministic
sha1 Build-ID:

```sh
adapter/framework/appspawn-x/generation/build_generation.sh --wrapper-id-probe
```

Write that 40-hex value into `expected_wrapper_build_id.txt` and the
`kHapDomainWrapperPinnedBuildId` literal in `src/child_main.cpp`, refresh the
frozen closure intentionally, then run the final producer:

```sh
adapter/framework/appspawn-x/generation/import_inputs.sh --refresh
adapter/framework/appspawn-x/generation/build_generation.sh
```

All inputs, temporary files, command logs, outputs, hashes and evidence remain
under `.work/product-tls-generation/`. The final producer command contains no
external source, sysroot, library, or 16.12 path.

## Stub/bypass inventory

No new stub was added by this producer, but existing stub/default behavior does
participate in the six-source compat artifact: fdsan no-ops, selected
`android_mallopt` success-without-effect behavior, logd/event defaults, and the
fixed-canary fallback in `android_reset_stack_guards`. Their absence from the
first-frame call closure is `NOT_PROVEN`; this generation is therefore not
deployable under the rule that only proven-unused first-frame capabilities may
be stubbed. The legacy evidence-only import objects remain classified in
`NEVER_DEPLOY_LINK_INTERFACES.md`. The appspawn sandbox and token behaviors
elsewhere in the product also remain outside this build-only claim.
