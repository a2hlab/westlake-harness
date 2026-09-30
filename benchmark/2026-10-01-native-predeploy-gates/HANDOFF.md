# cx-t0 integration handoff: N1 / N2

## Ownership and insertion points

cx-bms delivers the offline checker/API, source and real-package replay corpus,
tests and empty exception registry. **No deploy_generation or native-builder
file was changed by this lane.** cx-t0 owns the integration and device-facing
tests; no statement here says those hooks are already installed.

Observed target: `scripts/lab/deploy_generation.py` in the deployment lane,
`main`: after `m = load_package(a.package)` and `check_frozen_package(a.package)`,
but **before the dry-run success branch, Darwin/orb forwarding, package-tool
imports, or `Deployment(...)`**. The latter constructs a Board and calls ready;
checking only inside `deploy()` is too late for the requested no-device preflight.

Preserve the existing SHA, frozen API, single-ART and maps checks; N1/N2 are
additional checks. Apply to full deploy, upgrade, replace and add. A one-file
candidate still needs a sealed post-operation effective package/domain view, not
just that file's own SHA. Do not pretend a one-file fragment is the whole closure.

Rollback needs its own explicit prior-target policy: check the intended restored
package/recorded approved receipt, not the rejected new candidate. Do not
accidentally disable the existing recovery path by gating the wrong package, and
do not add a general native-gate bypass flag. Missing legacy provenance requires
an outer-reviewed recovery decision, not a fabricated source binding.

## Native build producer

1. Finish native compilation, linking and package assembly; seal package.json.
2. Emit `PACKAGE/native-checks/native-gates.json` and referenced source/DEX/domain
   snapshots from the **actual** build inputs. This sidecar is not mounted and
   must not create a package.json self-hash cycle. Include the final package SHA.
3. Run the repository checker with `--gate N1`; nonzero stops publication of the
   candidate as eligible for deployment. Keep the JSON with the build receipt.
4. Produce effective namespace profiles for N2. Unknown expressions and missing
   profiles stay rejecting; do not replace them with permissive path guesses.
5. Before deployment, re-run `--gate all` on the same sealed package and sidecar.
   Pin both identities in the deployment receipt and ensure they remain unchanged
   across forwarding. A cached PASS from a different package is not sufficient.

## Repository-controlled hook sketch

This is a handoff sketch, not an applied patch:

```python
from native_predeploy import check_package

report = check_package(
    a.package,
    a.package / "native-checks/native-gates.json",
    gate="all",
    readelf=resolved_readelf,
)
print(json.dumps(report), file=sys.stderr)
if report["exit_code"]:
    raise SystemExit(report["exit_code"])
if report["package_manifest_sha256"] != sha(a.package / "package.json"):
    raise RuntimeError("native package changed after preflight")
```

`resolved_readelf` must be a configured host-capable reader, not a binary from
the candidate package. Resolve the checker and default exception registry from
the trusted repository as the frozen-API gate already does. If the deployment
script is invoked from a copied package tools directory, locate the repository
explicitly; never import a package-supplied checker. Missing sidecar or tool is
exit 3 and must not fall through. The API returns JSON instead of throwing for
ordinary invalid inputs; the caller must examine `exit_code`.

Run N1 after native package construction even if the eventual deployment path
also runs it. Build rejection prevents a misleading ready-to-deploy artifact;
predeploy rechecking prevents stale receipts or partial copy drift.

## Checks for the wiring owner

- A rejecting N1, rejecting N2, or missing sidecar/tool stops before Board/hdc/orb.
- `--dry-run` must not print passed=true when the native gate rejects.
- Mutating a package file or input sidecar after an earlier PASS cannot reuse it.
- Replace/add use the effective post-operation namespace/filesystem, with the
  actual base generation identity; inherited/global SONAMEs do not close NEEDED.
- N4 `1617080a` rejects the JNI-order wall; current N4-order rejects the Flutter
  `libandroid.so -> liboh_android_runtime.so` edge plus disclosed unknowns.
- There are **no native waivers** in this delivery. Current strict REJECT is an
  intended result, not permission to skip the checker to restore rollout.

Full input format, limitation boundaries and commands are in `README.md`.
