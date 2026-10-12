# Final seal operation card

The immutable candidate contains 806 files. The final inventory contains 811
unique files: runtime 124, boot 36, installation 164, overlays 487. The five extra
objects are the actual U13 v3 boot cfg/script, selinux-mode, and TSV/JSON tables.
They must be retained by the real seal and final selfcheck, with full SHA checks.

`OPERATIONS.zh-CN.md` gives the exact outer-owned sequence: receipt-backed
collection, same-boot independent source WID evidence, original build_seal,
source-seal realization, immutable candidate-to-seal appendix, and activation-
bound target selfcheck. Commands here were **not executed on any device**.
No source seal, user acceptance or successful transaction is fabricated.

The 3791 source/proof compiler stays frozen. Its disabled-proof selfcheck is not
sufficient for the activated backup. The separate r3 selfcheck must bind the
admitted enabled package and every successful placement receipt before comparing
startup.env and startup.expected.sha256. The r2 wrapper route uses 2700 seconds;
only that explicitly superseded wrapper item replaces the original 3791 route.

Source inventory and tool SHA pins are in `sources.json`; outstanding generated
inputs are enumerated in `required-inputs.json`. The full 128-app manifest is
required for collection/build; the 20-key regression subset is not a replacement.
Ten-game screenshot acceptance remains a separate human evidence/signoff input.
