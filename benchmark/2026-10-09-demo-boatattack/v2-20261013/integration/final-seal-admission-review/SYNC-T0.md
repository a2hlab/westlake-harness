# T4 → T0: final seal admission review (offline)

Original consumer: main `benchmark/2026-10-09-demo-baseline/t5/build_seal.py`, especially `overlay_check`.

- Do not feed `2026-10-14-final61b-seal-command-card/source-map.disabled/overlays.pending.json` unchanged: it retains the V1 Boat absent row despite seal_stage v2. Use actual final61b `boat/composed/overlays.pending.json` (487 + 18) as the starting membership, then current-running SHA evidence.
- Actual composed Boat18 currently has `admission: null`: original consumer rejects it. A real outer admission pin is required; builder only checks pin syntax, not admission contents or actual acceptance, so a structural PASS is not admission.
- RouteB source/rollback copied from V1 have relative paths `route-b-source.json` and `../seal-final-inputs/rollback-index.61b.json`. Use explicit WORKSPACES pins to their original files; preserve their historical boot/scope. Actual source SHA858990f6 and rollback SHA5ab07faf checked. Do not relabel old source boot9f as new086d, or claim 487 newly placed on61b.
- Boat placement actual enabled-plan SHA49d7ac76 differs from source disabled-plan SHA3989a2d8. Bind both roles explicitly and compare the sole enable delta, rather than equating the two pins.
- 61b RouteB rollback index is scoped 24 controls with retained runtime/stage and was not board-exercised; it is not the5cd fresh487 transaction. Boat rollback must retain the actual eleven-member transaction/backup plus original provider pins, not just installer.py alone.

Detailed machine checks and field provenance will be written alongside this file. No board calls, no edits to your files/running inputs. Root can read this local handoff directly.
