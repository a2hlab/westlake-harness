# Frequent Habits ability-fallback capture

The prior desktop-only capture never launched this APK: twenty tile-bearing layouts contained no exact package/ability icon. This authorized capture keeps U10.1T8 unchanged and uses the pinned unique BMS launcher only after the same bounded exact-icon search fails. It is an explicit launch-method variable, not desktop evidence.

The first wrapper omitted the existing collector clock field (`click_monotonic`); `aa start` returned zero, but capture failed before any picture. Its complete raw record is retained. The repaired wrapper anchors capture to the successful ability-start return, records `clicked=false`, and obtained t20/t45/t90. Both executions finished within the original 15-minute allowance; each verified all 318 identities and restored the same runtime/boot fingerprints before unlocking.

See `evidence/facts.txt` verbatim and three JPEGs for outer visual judgment. The repaired launch returned `start ability successfully.`; `handleBindApplication returned OK` is present. No requested DfxFaultLogger/JniAbort/exit fatal line was observed during the complete 95-second capture. This does not prove no later failure or claim a lit UI.

`capture_batch.py` imports the master batch runner and replaces only its launch callback for one exact key/APK/package/ability. All install pinning, sandbox preparation, diagnostics, collection, cleanup and facts remain master code. No runtime/native/configuration/JIT member was replaced. Runtime d6848fa2c989 and boot e3806b65a079 remain unchanged.

Raw logs are preserved outside the public tree; `raw-inventory.json` pins every archived file. Public evidence copies replace local user paths, while screenshot bytes are unchanged.
