# Round 1: merged cluster plan

The old r17p list mixed wrapper crashes, later null state and already repaired walls. This plan preserves every source membership, prefers the newer r17r first-failure chain, and separates **passing an API wall** from **lighting an app**. It makes no new board claim.

**30 entries / 49 affected or diagnostic keys; all 72 memberships from 25 old clusters and 18 newer families mapped; 66 per-key forecasts.** Read [plan.csv](freeze-v1/plan.csv) for cluster → layer → lane → app → checkpoint/prediction, [plan.json](freeze-v1/plan.json) for reasoning/evidence, and [predictions.csv](freeze-v1/predictions.csv) for the consolidated forecast.

| Lane | Entries | Round-one scope |
|---|---:|---|
| J1 / cc-t3, r17u | 9 | Own-service discovery; themes/ConstraintLayout; RestrictionsManager; haptic arrays; audio fallback; Sentry projection; Gallery workaround; two retention entries |
| N1 / cx-t0 | 11 | Session/surface rebuild; Flutter inheritance; app namespace dependencies; Bionic imports; JNA; SoundPool; GLImpl; WebView/bitmap candidates; two retention entries |
| boot / oc-t4 | 3 | TagSoup method, MediaStore field, NetworkCapabilities method; separate delivery, **not included in U1** |
| App boundary / diagnosis | 7 | Six unassigned evidence/input buckets; AppManager to cc-wiki; no invented framework fix |

Layer confidence is explicit. JNA’s missing native resource is not a boot-class absence. Generic app NPEs remain unlocalized; Reader’s stack instead reaches SystemVibrator. Gallery/x/LibreTube resolve the missing field/method in `adapter-mainline-stubs.jar`; a runtime JAR cannot simply replace that selected boot definition. Immich retains its earlier verifier failure even if Flutter loading advances. Theme/native faults discovered later are not silently substituted for earlier bind failures.

| 66-key forecast | Lit | Pass wall | Unchanged | Unknown |
|---|---:|---:|---:|---:|
| J1 on U0 | 23 | 9 | 19 | 15 |
| N1 on U0 | 24 | 19 | 11 | 12 |
| U1 = U0 + J1 + N1 | 27 | 23 | 4 | 12 |

The U1 lit set retains 21 outer-signed r17r keys, adds the already exposed asset53 NewPipe result, and predicts API, Wikipedia, both Noice keys and uhabits. These are **key counts, not distinct APK counts or 27 new successes**. r17t, asset53 and reported 32df/Wikipedia results were already known; future full J1/N1/U1 outcomes were not read.

U0 is v3c 668e4f7c + runtime 53f00423 + r17r dd4f0eae + installer 6aadb8b4/7048c7c5. FZ-001/002/003 remain protected. This is a feature-plan freeze; exact J1/N1 release hashes are pending and must be bound separately. Drift or pre-freeze clicks cannot enter exact-profile prospective scoring. A wall passes only after its stage is reached and positive progress is evidenced; disappearance behind an earlier failure is unknown. Lighting requires outer-signed t20 own-content screenshots.

cx-bms owns J1/N1 scoring and U1 facts aggregation. [handoff.json](handoff.json) lists pending inputs: three explicit shard paths, release manifests, per-app logs and image signatures. Preserve each shard’s original facts; recount captures/process tables, reject duplicate keys or mixed fingerprints, report missing keys as unknown. No counts are filled from this plan.

Rebuild to a **fresh** directory with `python3 build_plan.py --out NEW_DIR`; frozen outputs are never overwritten. Machine join/identity/hash checks are recorded in [validation.json](validation.json). No board operation; commit remains for the outer lane.

Freeze SHA-256: `240f0f852e95e8e57d18a75e53e53dc4d4d77a987e0a0bc086f628bd99615cf1` (2026-09-30T02:28:18.739252+00:00).
