# appspawn-x final-ELF TLS ownership verifier

This is a host-only, fail-closed gate for the OpenHarmony musl AArch64
`TLS_ABOVE_TP` layout.  It never modifies an APK or device.

There are three different claims, and the tool keeps them separate:

1. The main ELF owns every byte of each admitted Bionic inline slot.
2. The four unchanged CardWords DSOs have a complete, zero-unknown TP-access
   inventory.  The historical report has three CFG unknowns and is red.
3. The final appspawn main, exact loader, and entire recursive initial
   `DT_NEEDED` closure have a separate zero-unknown TP scan proving that no code
   consumes slot 5 before explicit TLS preparation publishes its value.

A PT_TLS owner map proves claim 1 only.  It does not prove claim 2 or 3.

## Mechanical policy

The verifier:

- walks the initial `DT_NEEDED` graph in musl load order;
- applies the OH musl `TLS_ABOVE_TP` offset formula;
- reports SHA-256, Build-ID, PT_TLS and every admitted slot byte owner;
- rejects missing or ambiguous names, duplicate `DT_NEEDED`, wrong machine,
  `DT_RPATH`, `DT_RUNPATH`, `DT_TEXTREL`/`DF_TEXTREL`, preload/env search,
  unproven sidecars, and any new runtime PT_TLS object;
- accepts a stripped ELF sidecar only when Build-ID, machine, executable and
  writable load bytes, entry/type, PT_TLS, SONAME and `DT_NEEDED` match;
- requires every input, search directory, sidecar, config, scanner source and
  report output to resolve inside `/opt/21.Game/02.unity.cardwords`;
- treats external paths in a frozen manifest as inert origin labels only.  They
  are never opened by the verifier.

The current canonical inputs are frozen at:

```text
adapter/frozen/product_inputs/cardwords-current/
```

That root contains the exact APK, its four extracted ARM64 DSOs, the historical
red scanner report/tool, three musl source oracles, and an observed loader
oracle.  `FROZEN_INPUTS.json` records origin SHA -> local SHA.  It also lists the
artifacts still missing for a product certificate.

The musl source files explain the allocator, but no build provenance currently
connects those source bytes to loader SHA `316f...aa98`.  Therefore the current
profile says `musl_source_match=NOT_PROVEN`.  A product certificate must bind
either build provenance or an independent exact-loader byte/fixture oracle.

## Self-test

```sh
bash adapter/framework/appspawn-x/tests/tls_layout_verifier/run_tests.sh
```

The suite includes positive ownership plus exact `prev_current@TP+0x28`
collision, guest-report unknowns, low-slot host ownership, ambiguity, missing
dependency, wrong machine, RPATH/RUNPATH, TEXTREL, project symlink escape,
runtime PT_TLS invalidation, and good/bad sidecar controls.

## Replacing the red CardWords guest scan

Do not edit `tp_scan.canonical-unknown3.json` or its red profile.

1. Copy the new scanner source and new report into the generation directory
   under this project before verification.
2. The report must retain schema `unity-inline-tp-scan-v1`, bind APK SHA
   `435f0e...0626`, and bind the exact four frozen DSO SHA values.
3. Both `totals.inline_unknown_count` and
   `totals.cfg_inline_unknown_count` must be integer zero.  The verifier compares
   those measured values with `native_scan`; editing only the inventory cannot
   turn a red report green.
4. Add the report/tool as frozen inputs with their actual SHA values.  Point
   `subject.guest_scanner_*_artifact_id` to them.
5. Preserve only observed guest semantics.  Currently that is slot 5 at
   `TP+0x28`, 8-byte reads.  Slots 2/3/4/6/7 are reservation bytes, not invented
   Android semantics.

## Initial-closure scan (independent second gate)

Start from `profiles/initial_closure_tp_scan_report_template.json`.  The report
must enumerate the exact final main, exact loader, and every recursively loaded
initial DSO by module name and SHA.  It must show:

- `unknown_tp_accesses=0`;
- `pre_prepare_slot5_access_count=0`;
- `prepare_order_proven=true`, backed by a separately frozen phase/callgraph
  artifact that places explicit prepare before every admitted slot-5 consumer.

This is required because the main reservation initially zeroes slot 5.  A
post-specialization prepare is admissible only if the entire pre-prepare closure
is proven not to depend on the Bionic stack guard value.

## Product inventory and exact closure command

Copy `profiles/product_inventory_template.json` to the generation directory,
replace every placeholder, add every recursive initial/runtime closure ELF, and
keep all paths project-relative in `frozen_inputs`.

The command below is the single final product gate.  `GEN` itself is inside the
current project; no `/opt/10.Project`, sibling project, device, or `/tmp` path is
an input.

```sh
GEN=/opt/21.Game/02.unity.cardwords/adapter/frozen/product_generations/GENERATION_ID
CARD=/opt/21.Game/02.unity.cardwords/adapter/frozen/product_inputs/cardwords-current/canonical
python3 /opt/21.Game/02.unity.cardwords/adapter/framework/appspawn-x/tests/tls_layout_verifier/verify_tls_ownership.py \
  --require-product-certificate \
  --exe "$GEN/rootfs/system/bin/appspawn-x" \
  --loader "$GEN/rootfs/system/lib/ld-musl-aarch64.so.1" \
  --rootfs "$GEN/rootfs" \
  --cwd "$GEN/rootfs" \
  --system-dir "$GEN/rootfs/system/lib64" \
  --system-dir "$GEN/rootfs/system/lib64/chipset-sdk-sp" \
  --runtime-system-dir "$CARD/lib/arm64-v8a" \
  --runtime-system-dir "$GEN/rootfs/system/android/lib64" \
  --runtime-system-dir "$GEN/rootfs/system/lib64" \
  --runtime-system-dir "$GEN/rootfs/system/lib64/chipset-sdk-sp" \
  --inventory "$GEN/cardwords-slot5.product-inventory.json" \
  --symbol-sidecar "\$MAIN=$GEN/sidecars/appspawn-x.unstripped" \
  --symbol-sidecar "libselinux.z.so=$GEN/sidecars/libselinux.z.so.unstripped" \
  --runtime-dso "$CARD/lib/arm64-v8a/libmain.so" \
  --runtime-dso "$CARD/lib/arm64-v8a/libil2cpp.so" \
  --runtime-dso "$CARD/lib/arm64-v8a/libunity.so" \
  --runtime-dso "$CARD/lib/arm64-v8a/lib_burst_generated.so" \
  --report "$GEN/tls-ownership.product-report.json"
```

Every real production search directory must be listed in actual loader order.
Adding a broad fallback to make resolution succeed invalidates provenance.

## What PASS does not prove

Even a product PASS is static `build_pass` evidence.  It does not prove fork
sequencing, new-thread initialization, callbacks/signals, stock setcon success,
production init, SELinux Enforcing, ActivityThread, Unity native loading, or a
visible first frame.  Those remain separate true-device gates.
