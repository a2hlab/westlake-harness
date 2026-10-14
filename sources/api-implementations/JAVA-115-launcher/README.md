# JAVA-115: launch activity qualification

The previously delivered manifest commit 5057daae passed a relative Activity name through unchanged. The actual later launcher is delivered here from upstream manifest commit `4b5c01f1904df1ef75a486f76ce32afdffeb42bf`. In `tools/probe_source_app.py:235–243`, an explicit Emacs comment explains the failure, a leading-dot name is prefixed by its package, and a bare class is prefixed by package plus dot. The qualified result is passed to `ASX_LAUNCH_ACTIVITY` at line 732. This is the real Python launch path, not a similarly named Java fallback or a claim that ComponentName.createRelative was called.

The exact original launcher, its imported digest helper and its two directly loaded repository locks are here on the same tree. `source.lock.json` pins original Git blobs and SHA values. The launcher is interpreted Python; there is no C/Java compile product for this normalization. Inspect its actual command interface without contacting a device:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 sources/api-implementations/JAVA-115-launcher/tools/probe_source_app.py --help
```

An actual launch separately requires the original CLI's verified framework/runtime/app-input reports, APKs, host, HDC transport and board authorization. Those runtime inputs are not a new build or deployment claim. The imported bootstrap helper is included for `digest`; running its separate SDK-installation main is outside this launcher delivery. External runtime/platform dependencies remain explicit in the CLI and locks.

Independent offline checks executed the two actual normalization/validation AST statements for relative, bare, qualified and invalid names; all four passed. The original CLI `--help` returned zero with zero device calls. No live launch or historical r87 artifact/commit equivalence was established. The r87 report supplies the historical behavior claim; this newer exact source proves an implementation of that behavior. The upstream manifest tree has no root LICENSE and the original files have no explicit license header; no license has been invented.
