# M04 first-round source reachability gate

This directory is a host-only, source-level checkpoint for the M04
Bionic/Musl boundary. It answers one narrow question: which M04 source files
are executable members of the ARM64 producer recipe, and does that recipe make
an explicitly quarantined legacy shim/runtime-stub source reachable?

It does not build a product DSO, classify the complete Unity crossing set,
validate an ABI translation, approve a provider graph, issue the offline-only
`NativeGenerationReceiptV1`, or issue the attach prerequisite
`ChildRuntimeReadyReceiptV1`.

Run the causal controls:

```sh
adapter/framework/native-compat/m04-first-round/tests/run_host_tests.sh
```

Audit the current ARM64 producer (non-zero is the preserved current result):

```sh
/usr/bin/python3 \
  adapter/framework/native-compat/m04-first-round/tools/verify_source_reachability.py \
  --project-root . \
  --recipe adapter/build/inner/cross_compile_arm64.sh
```

Exit status `0` means exactly one `bld bionic_compat` command contains the five
non-quarantined system-side sources once each, with no denylisted, backup, or
unclassified source. This is source membership, not semantic approval. Exit
status `3` is a policy failure. Exit status `2`
means the oracle input was invalid or escaped the project root.

The complete first-round evidence boundary and ledgers are in
`FIRST_ROUND_REPORT.md`.
