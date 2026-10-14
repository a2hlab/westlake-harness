# Native source closeout checkpoint

**SOURCE-CLOSEOUT — offline source delivery, not a new device acceptance.**

Earlier neighbouring logs were not the signed objects: `089bebe7` is not
bridge8ab, and `0d7b9712` is not libandroid9cc/ADC. The exact ADC49-byte replay
is already preserved; it must not be reported as original C++ production.
This checkpoint delivers concrete implementation code, recipes and dependency
acquisition, while keeping the original source-to-output binding gaps visible.

## Actual delivery

`sources/api-implementations/shared-native-production/` contains 247 preserved
implementation/evidence source members: 155 frozen FZ001–003 members and 92
related historical-family C/C++/recipe witnesses. The latter are not certified
producing inputs for bridge8ab/9cc. All readable source hashes and their original
hashes are recorded. Eleven files were CRLF-normalized by the patch transport;
their exact raw bytes are separately tracked and restored by `materialize.py`.
The new byte-materialization test compares every installer-source output with
the original hash; no function or frozen source is silently changed.

Four external archives are locked separately: final FZ001 source, original OH
kit, FZ002 generation and external OH link inputs. `acquire.py` checks full SHA,
supports explicitly configured retrieval, rejects substitutions and retains
partial failures. `build_provider.py`, `build_installer.py`, the original asset-fd
recipe and `execute-hw248.sh` are actual executable entries, not inventory-only
claims. Compiler/linker/libc pins and partial-compilation refusal remain strict.

The original generation archive's child source is `0bb00135...`, not the frozen
BIGSTACK implementation `3fc2060e...`. The provider entry overlays only that
exact source into its **fresh private restored generation**, then uses the
original compiler/link flags. No historical source directory is edited.

## Fresh executions and limitations

- Known answers: **9 tests PASS**, actual stdout/stderr/rc in `evidence/`.
- Mac actual provider CLI: **rc2**, after compiler/linker/libc pins matched;
  Linux clang returned `Exec format error`. Raw files remain in the worktree's
  `.artifacts/local-producer-attempt/`; this is not compiler or link success.
- Outer first hw248 attempt: both dependency archive SHAs passed, restore
  **rc2**, **compiler not launched**. The undeclared auxiliary header root was
  identified from the actual archive rather than treated as a compile failure.
- Revised layout: the complete original archive has 80478 members; exactly
  33 outside-generation header members now have explicit suffix/SHA mappings.
  Unknown roots, changed auxiliary bytes, traversal and undeclared links still
  reject. Two unused B67 test-source links remain explicitly unprovided, not
  substituted with B68 files or claimed as complete whole-generation closure.
- Outer second fresh hw248 attempt: generation restored 80477 members, then
  external merge **rc2** on duplicate `platform-link/lib2d_graphics.z.so`;
  **compiler not launched**. Both failures are preserved, not compile failures.
  Cross-archive duplicates will be independently audited and fixed in a later
  narrow revision; this source checkpoint remains fail-closed. A producer rc0
  with a differing output is not historical exact production.

Root raw read and build evidence is retained at
`$WORKSPACES/_verified-source-closeout-20261014/verified-source-closeout-root-reads/`
and `$WORKSPACES/_verified-source-closeout-20261014/root-hw-native/`.
The first remote build root is
`$HW248_HOME/verified-source-closeout-native-20261014/root-20261014T094727Z`.
The second original request/log prefix is `20261014T095804Z-*`. Do not reuse the
first failure as a successful build. No useful result is only in `/tmp`.

## Honest remaining production gaps

1. Bridge8ab: signed bytes and related implementation are available, but the
   original exact source manifest/compile/link argv/rc0 production binding has
   not been recovered. The old recover-old-bridge log builds another object.
2. libandroid9cc/ADC: original producing C++ snapshot/build remains unbound.
   The separately durable exact replay archive SHA2824b050 is replay evidence,
   not source-build closure. No repeated ADC experiment is requested.
3. FZ003: actual ParcelFileDescriptor TU, original recipe and 59 object pins are
   delivered; complete original asset-fd generation acquisition is unresolved.
   U13/f28 is not rebuilt or substituted as its historical producer.

`atlas-amendments.json` is the machine-consumable source/build-only delta.
Historical API results, freezes, signed SHA gates and predictions are unchanged;
new first-fatal keys moved is **0**. `source-landing-paths.txt` and `freeze.json`
pin the independently reviewable code checkpoint before the pending build
receipt. No board, VM build, push, branch switch or main-tree modification.
