# G19 minimal mac/ORBENV environment addendum

**The evidenced problem was argument path translation, not proof that the VM-to-Mac bridge was down.** Outer has corrected the existing oatdump transport adapter and started original U7 preflight05. This addendum records the proven recipe only: no connection, preflight, SSH, HDC, VM restart, permission change, device action or new deployment tool was run.

## Proven correction

Outer preflight04 showed that passing `LAB_HOME=/home/...` as an argument to `mac env` rewrote the remote prefix into a Mac OrbStack filesystem path, causing the original oatdump lookup to fail. This finding is explicitly attributed to outer's original stderr. The old `hdc_mac.sh:99–104` comment about arguments *starting* with slash is not a complete description: path-valued assignments can also be translated. G19's earlier explanation was therefore too narrow.

The corrected existing adapter preserves an exported, provenance-derived LAB_HOME through ORBENV:

```sh
ORBENV="${ORBENV:+$ORBENV:}LAB_HOME" mac "$checker" "$@"
```

This is copied from the current outer-owned `gles-bounded-window/oatdump-via-mac.sh`; it is not a second implementation. Do not pass `LAB_HOME=...` as an argv element after mac, replace the original oatdump checker, or guess the remote prefix. OrbStack's [environment forwarding documentation](https://docs.orbstack.dev/machines/#environment-variables) defines the colon-separated ORBENV mechanism; the local outer receipt proves this particular value survives unchanged.

`outer-orbenv-probe-02/stdout.txt` contains the actual result: **rc0**, before/after SHA256 both `4e5277d9907dc562d2135c48e53fa1ed5764ab628dae1e8e397499e708a1c102`, empty inner stderr. The raw command record is `command.json` (this receipt has no result.json). Original and portable-copy hashes are retained in `source-index.json`. The remote LAB_HOME value itself is not reproduced in prose.

The separate original `orb -m a2hlab mac /usr/bin/true` result remains **rc1**, `posix_spawn: exec format error`. Path translation can select VM `/usr/bin/true` (ELF), whereas Mac `/usr/bin/true` is Mach-O. That command is not a valid basis for declaring the bridge unavailable. No replacement probe is needed now that outer's ORBENV round-trip succeeded. G19's earlier single OrbStack timeout remains untouched and has the same limited meaning.

## Minimal execution-environment recipe

- Keep G21's existing VM PATH additions for the installed Linux clang15/readelf/build-tools dependencies. This evidence does not identify them as the cause of the remote-prefix rewrite; changing PATH would not fix a transformed LAB_HOME assignment.
- Derive and export LAB_HOME using the existing G20 SOURCE.txt provenance logic; preserve it using the exact ORBENV adapter line above. WESTLAKE_HARNESS and OATDUMP_TRACE_ROOT remain explicit inputs consumed by that existing adapter. Its original stdout/stderr/rc capture stays enabled.
- Set **TMPDIR before starting the VM Python/U7 process** to an outer-selected persistent scratch directory visible from both Mac and VM at the shared path. G2's temporary image and reference files must be readable by the Mac-side checker while it runs. A VM-only `/tmp/...` is insufficient. Shared persistent scratch does not replace the separate original output/rc receipts or imply that temporary-directory cleanup is disabled.
- Use the already running preflight05 to obtain the original U7 result. Do not infer PASS from the value-preservation probe, launch another preflight, or treat a waiting mac/oatdump step as a dead bridge without its own rc/stderr.

## Existing HDC and path-source limits

The observed guest link is `$HOME/OrbStack/a2hlab/usr/local/bin/mac -> /opt/orbstack-guest/bin/mac`. The target is not exposed through that Mac filesystem view; no bridge-binary replacement or repair follows from that visibility limit. Current VM command lookup was not re-probed. The previously recorded outer readiness establishes mac availability in its session.

The original `hdc_mac.sh` already shields cwd, the Mac HDC executable and remote device arguments inside one NUL/base64 payload before `mac bash -c` decodes them on Mac. Preserve that existing protection; do not turn its absolute device operands into direct mac arguments. This is a source observation, not a new HDC execution result. The oatdump adapter's LAB_HOME assignment was a separate unshielded argument, now handled by the original ORBENV facility. No claim is made about hidden environment variables or undocumented PATH inheritance.

Original G19 packages, env-check e98e1b5a85 and earlier timeout remain unchanged. `landing-paths.txt` contains only this addendum. `results.json` separates the measured probe02 result from outer-reported preflight04/TMPDIR findings and the still-running preflight05. No deployment approval is issued.
