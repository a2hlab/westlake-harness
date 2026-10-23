# T97D read-only environment diagnosis

The saved failure is in REA ownership_preparation, compiler rc1. It explicitly reports both a denied SwiftShims module-cache write under `$HOME/.cache/clang/ModuleCache` and SDK/compiler mismatch. Current selected developer root is CommandLineTools: compiler6.3.3, MacOSX26.5 SDK Swift interface built with6.3.2. These are two recorded blockers, not target-analysis results.

Installed REA selection is pinned in results: ProcessOwnershipObservation.js157–175 selects compiler/SDK and cache options; DarwinProcessRunTokenReader.js240–245 defaults to xcrun and empty cache option;294–327 handles compiler arguments and cache. The empty option uses Swift's default cache. Merely changing compiler selection would not establish that the separate cache denial is solved.

An existing Xcode26.4 Release Candidate bundle reports Swift6.3, with SDK26.4 interface also Swift6.3. It is only a compatibility candidate; no build was attempted. Existing Ghidra12.1.4 and Java paths were checked for existence, not launched. Actual Java selection in the failed request remains unproven.

Raw version-query argv/time/rc/output are private and indexed. No compilation, doctor, REA retry, cache creation, environment/permission/configuration change, download, device action or authorization change occurred. No retry command is prescribed.
