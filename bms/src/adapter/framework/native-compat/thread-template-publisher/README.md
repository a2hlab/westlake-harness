# Main-ELF TLS thread-template publisher

This component locates the current executable's file-backed `PT_TLS` image and
publishes one already-prepared process guard into the future-thread template.
It does not create threads, generate entropy, modify Musl globals, or own WLTG
admission.

The commit-level replay is intentionally host-only:

```sh
adapter/framework/native-compat/thread-template-publisher/tests/run_host_tests.sh
```

It verifies template copy, concurrent exact-once publication, and four negative
controls. This proves only the portable component mechanism. AArch64/OH-loader,
appspawn product wiring, all thread-entry admissions, device startup, Unity load,
and first frame require later same-generation gates.

See `HOST_CORE_REPORT.md` for the evidence boundary.
