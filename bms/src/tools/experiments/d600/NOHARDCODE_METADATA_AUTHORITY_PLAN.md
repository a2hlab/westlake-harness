# No-Hardcode APK Metadata Authority Plan

## Goal

Prove hello2 and Calculator using a single metadata authority chain:

```text
APK bytes
  -> bm install
  -> BMS InnerBundleInfo / full bm dump
  -> BMS-registered launcher ability
  -> aa start
  -> AMS/appspawn-x fork
  -> ART ActivityThread lifecycle
  -> app-owned first frame
```

The test manifest YAML is only a fixture: APK path, expected package, and the
expected launcher selector. It is not product metadata.

## Historical Review Checkpoint

The five-APK historical install attempt is the negative control for this run.
It reported successful install receipts but exposed shared `Hello World`
launcher metadata and wrong public entries. That result was correctly stopped
before UI launch because command success, YAML targets, and static activity
launches cannot prove installed identity.

Carry this review after every few implementation or device steps:

- Do not accept `install bundle successfully.` as residency proof.
- Do not accept `aa start` arguments as metadata proof.
- Do not accept a screenshot if BMS did not first expose exact package,
  app-owned label/resource fields, and the public launcher.
- Do not let a missing BMS field be replaced by a runtime-built
  `/system/app/<pkg>` or `/data/data/<pkg>` fallback without recording it as
  unresolved design debt.

## Harness Contract

`run_apk_lifecycle.py` must:

1. Install the exact APK SHA.
2. Read `bm dump -n <package>`.
3. Parse the exact package JSON body.
4. Require `name` or `applicationInfo.bundleName` to match the package.
5. Require at least one enabled `hapModuleInfos[*].abilityInfos[*]` entry.
6. Require the manifest-selected activity to be an enabled BMS launcher.
7. Launch only the BMS-selected bundle/activity/module.
8. Derive process evidence from `pidof <package>` or
   `AppSpawnClientSendMsg result:0x0 pid:<n>` plus `ps`.

Fail closed before `aa start` if any metadata gate fails.

## Static Gates

Generic runtime/package-manager/appspawn code must not synthesize app identity
from package allowlists or HelloWorld/Calculator special cases. Fixtures,
specs, and evidence may name concrete APKs.

Known hidden fallback debt to audit separately:

- `PackageInfoBuilder.java`: generated `dataDir`, `sourceDir`,
  `nativeLibraryDir`, default ABI.
- `OhApplicationInfoConverter.java`: generated path/ABI fallbacks.
- `AppSchedulerBridge.java`: provider `ApplicationInfo` and runtime APK path
  probing.
- `PackageManagerAdapter.java`: provider `ApplicationInfo` path synthesis.
- `apk_manifest_jni.cpp`: `ResolveApkPath(packageName)` probes fixed paths.

These are not HelloWorld hardcodes, but they are still not BMS-authoritative
metadata. They must be resolved before claiming the runtime is fully
metadata-authoritative.

