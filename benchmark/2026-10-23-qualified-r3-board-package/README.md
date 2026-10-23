# T120: qualified, disabled 5cd r3 package

The old wrapper could change the board serial while retaining 61b configuration bindings. T118 introduced explicitly pinned configuration inputs; T119 then bound the four external dependencies to actual 5cd files. This build uses those receipts and the unchanged approved T34 r3 inputs.

The actual build returned rc0. Independent checks matched all **24 inputs, 22 payload files and 17 fixed r3 outputs**, the packaged parent-launcher SHA, startup checksum and current dependency receipts. The payload remains **disabled and not deployable**. File identity does not establish 5cd runtime compatibility or repair the white screen.

`assemble.py` is the build entry point. `input-manifest.json`, `output-manifest.json`, `external-bindings.json` and `results.json` provide exact identities and original execution-log hashes. Original build stdout/stderr/argv/rc are retained under the private build alias in results and independently archived at `$HOME/.local/share/westlake/outer-archive-qualified-r3-board-package-20261023/`. `outer-review.json` and `review/` record both independent reviews.

## Reproduce

Restore the approved T34 receipt/input archive described by `benchmark/2026-10-21-t34-demo61b-video/reentry-retirement-01/deploy-package-r3-root/CHAIN.json` to a durable directory containing `old-suite-r3`. The build verifies each fixed input SHA before copying it; a missing or different input must fail. From the repository root:

```sh
T120_OUTPUT="$HOME/.local/share/westlake/t120-rebuild-$(date +%Y%m%dT%H%M%S)"
python3 benchmark/2026-10-23-qualified-r3-board-package/assemble.py \
  --main "$PWD" --video "$PWD" --peer "$PWD" \
  --t34 "$HOME/.local/share/westlake/t34-reentry-retirement-20261021" \
  --out "$T120_OUTPUT"
```

The output must be a new directory. This reproduces the historical configuration candidate from pinned receipts; it does not perform a fresh device attestation or deploy it. No controller is executed.

## Installation boundary

The local copied members were mode0644; the approved member manifest requires0550 for executable members and0440 for data. T121 must set and verify actual modes, including screen-gate0550. Original T120 bytes remain untouched. The old 5cd ROOT is preserved; a later experiment may change only the init service's boot-entry argument, with the exact original init bytes as rollback. Never install generated `payload/recovery.cfg` over the live init.
