# ART Palette boundary for OpenHarmony

This module replaces AOSP's host-only `palette_fake.cc` in WestLake target
provider generations. It preserves the Android managed-priority mapping and
performs real `setpriority`/`getpriority` operations for ART threads.

The remaining methods are explicit capability boundaries:

- tracing and report-enable queries are disabled diagnostics;
- crash stacks are sent through the existing Android-log to OH-hilog path;
- zygote ashmem, odrefresh, dex2oat reporting, JNI reporting, lock-contention
  reporting and task profiles return `NOT_SUPPORTED` when invoked rather than
  claiming a successful platform operation.

The current non-Bionic ART build compiles the memfd JIT path, so the palette
ashmem path is outside its first-frame code path. The final release certificate
must still retain every unsupported capability in its stub ledger.

Replay with `tests/run_all.sh`. The host test kills a fake-success scheduling
mutant; the target test produces the AArch64 DSO twice and requires the exact
`setpriority`/`getpriority` imports and only `libc.so`/`liblog.so` dependencies.
