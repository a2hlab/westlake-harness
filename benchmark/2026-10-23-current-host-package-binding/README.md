# T78 current host package binding

**Current binding is unknown: the first device read failed at the HDC transport.** A local exit code of zero must not be interpreted as a successful remote command.

The lock check (`board_note.sh held` for the exact 61b serial) returned rc=1 with empty stdout/stderr, indicating no live recorded holder. The next and only device command attempted `cat /proc/sys/kernel/random/boot_id`. HDC returned rc=0, empty stdout, and the original stderr `Connect server failed`. No boot ID or confirmed remote execution was obtained. Exact argv, UTC start/end, rc, stdout and stderr are in `raw/`; `results.json` indexes the two commands.

Stopped at this failure. No `bm` query, installed-HAP hash, package transfer, REA call, device write, app start, restart, permission/configuration change, or T71/T74 diagnostic continuation followed. No git commands, commit or push were performed. Existing dirty files were preserved.

T70 previously recorded `/data/app/el1/bundle/public/org.westlake.imehost/entry.hap` with SHA `b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0`. That is a historical reference only. This attempt cannot establish current boot, BM-declared package path, SHA equality, bundle/ability metadata or desktop-to-package entry matching. The prior successful REA lifecycle was not repeated or promoted to current-device evidence.

The contract's parse2/lint100 result was supplied by outer. This receipt is pending human review and makes no lifecycle PASS, startup-success or white-screen-fix claim. The permitted failure branch is handed back with the unmodified error; no transport workaround was attempted.

Local environment-only follow-up: `CODEX_SANDBOX_NETWORK_DISABLED` is present with value `1`; `HDC_SERVER_PORT` is absent; `HDC_SERVER_IP` is absent. No values for the latter two were emitted. This records inherited environment, not a proven transport-failure cause. No network/device call or workaround occurred. The raw receipt is `raw/03-client-environment.json`.

## Outer-supplied evidence appendix

The preceding failure and environment observations remain the original inner-session result. Outer independently executed three successful read-only commands at 2026-10-23 07:51:58–07:52:19 UTC; this inner session only read their saved files. All three receipts have rc=0, empty stderr and meaningful stdout. Their private paths and byte hashes are pinned in `outer-evidence-appendix.json`.

Outer observed boot `e9d0a715-26cb-4f0c-aceb-078373b90771` and device date `Fri Oct 23 07:51:58 UTC 2026`. BM declares `org.westlake.imehost`, module `entry`, `EntryAbility`, and `/data/app/el1/bundle/public/org.westlake.imehost/entry.hap`. The separate SHA receipt for that exact path is `b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0`, identical to the locally rehashed sample and T70 historical production binding. This supports installed-package identity at the outer receipt window, not successful inner HDC access.

Offline `module.json` comparison matches bundle, module, main entry, ability, source entry, versionCode=2 and desktop `action.system.home` / `entity.system.home`. Its hash `0dbaacbe6b17eadecda308d65e77483bf87fe2971695fecac1a5b55a5d137b51` matches the existing T55 member pin. The exact local manifest is retained as `outer-supplied.module.json`; it was read locally, not extracted by a new REA call. BM's `uiSyntax=hml` and empty `virtualMachine` differ from the manifest's `ets` / `ark24.0.0.0`; these representation differences do not establish a runtime cause.

The prior successful REA inventory is reused because the hashes match. Zero additional device or REA calls were made by inner. These three outer receipts include one boot sample before the package/hash reads, not a second boot sample afterward; same-boot context is supplied by outer. Actual desktop click resolution, application launch success and white-screen cause remain unverified. Review remains with outer.

The extracted `outer-supplied.module.json` preserves the original package bytes and SHA, including eight trailing-whitespace lines. These evidence-only lines are the known `git diff --check` exception; the bytes were not reformatted.
