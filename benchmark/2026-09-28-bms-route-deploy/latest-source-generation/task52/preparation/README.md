# Grouped-restoration preparation (not deployed)

The accepted task53 host/child assessment is copied with its original diff and
disassembly references. Provider changes await task56 because live B5 loads
80c9aee0, not the system alias used by task53. No entire old source snapshot is
assumed to match R155 simply from a directory name. In particular, the r148
copy contains InvokeProviderChildEntryWithResolver only in its test-only branch;
that match alone is not a usable production V1 restoration.

Prepared host broker patch removes the compile input, link input and LIBC export
block as one unit in both canonical and retained-provider recipes. Dry-run applies
cleanly to the pinned source hashes. It remains unapplied until the grouped plan
is available. AppSpawnDump should consequently use imported vfprintf/fflush;
strict-link and resolved-instruction readback are still required.

Host InstallPluginHostServices and child loader/namespace callbacks must follow
the same request, host-service and manifest ABI. Do not delete the inheritance
export independently or suppress admission checks. Keep verified-file/build-ID
and ancillary-message bounds checks unless a reviewed equivalent is supplied.
Identity manifests and host pins will be regenerated from actual output hashes.

Counts below include differing defined functions, excluding PLT/linker blocks.
A `retain-*` disposition is separate from proven harmless. This is an inherited
assessment, not a claim that the changes have already been restored.

```json
{
  "host": {
    "harmless-layout": 16,
    "harmless": 1,
    "retain-diagnostics": 2,
    "harmless-diagnostic": 10,
    "restore": 9,
    "retain-hardening": 9,
    "harmless-constant-relocation": 6,
    "restore-hardening": 1
  },
  "child": {
    "restore-with-protocol": 62,
    "harmless-rename": 20,
    "retain-diagnostics": 3,
    "restore": 5,
    "retain-hardening": 8,
    "harmless-constant-relocation": 5,
    "harmless-layout": 1
  }
}
```
