# V2 byte recovery and source reproducibility audit

Restoring signed bytes was previously liable to be mistaken for rebuilding them from source. This audit keeps three claims separate: **byte recovery**, **deterministic patch replay**, and **source compilation**. It covers all 824 unique signed file targets (829 group assertions; 762 distinct contents), without attempting a new firmware build. The 130 signed application package identities remain separate; third-party APK source builds are not asserted.

[Results](release-audit/results.json), [all target rows](release-audit/artifact-inventory.json), [source profiles](release-audit/source-profiles.json), and [archive coverage](release-audit/archive-coverage.json) carry full SHA references to signed S `ad566cae…` and its actual seal. Every target has both statuses. **All 824 now have verified local bytes and archive membership. Whole-stack source reproducibility remains unestablished.**

The outer lane actually verified eight existing remote objects (`rc=0`, 29.1 seconds). This audit checked matching local archive bytes and relevant members, including all 6,347 declared runtime input objects. The later four-content supplement closes the remaining eight deployed paths: adapter8ab, JAR633, Unity1bea and IL2CPPf6b8. Its remote archive SHA is `c57a6b0406571d4680769bdd00085227cdb234abf77db0dd25c0244709e65ba6`; every local member was independently hashed here. This improves recovery coverage only.

| Artifact | Established | Remaining limit |
|---|---|---|
| f28 runtime | Existing cold source build, exact output, source/patch/compiler/container/scripts and original rc0 stdout+stderr; preserved source archive | No second f28 build executed by this audit; pinned author-path layout and external dependencies remain |
| Feed classifier0bf966 | Existing two equal source builds with original execution logs and compiler pins | Complete SDK redistribution is not implied by three tool/sysroot pins |
| ADC libandroid | Exact9cc parent and49-byte replay, real replay rc0/stdout/stderr, semantic four-function mapping, archived output | Parent9cc exact source/toolchain/original build logs remain unknown |
| Bridge8ab | Exact bytes recoverable; historical source investigation retained | Exact source/toolchain/producing logs unresolved; another output089 is not8ab |
| JAR633 | Exact bytes and historical C9/smali producer locator | Complete donors/tool jars/original producing streams not established here |
| Unity/IL2CPP/signal helper | Exact signed bytes; historical APK transformation/helper recipe locators | Not Unity source builds; original paired output-producing closure partial |

ADC changes are47 executable bytes across four geometry functions plus2 class-name bytes. The 0d7b runtime-build log does **not** produce ADC. Existing947/f28 runtime source builds are not verified replacements for its separately loaded libandroid caller; r3's geometry failure when ADC was omitted is retained evidence against that inference. No verified upstream alternative that replaces this exact caller was established from the audited local source/provenance chain. The deterministic49-byte replay must never be labelled an original source build.

426 target placements retain `UNKNOWN_EXACT_BUILD_CLOSURE`;382 are controls/data with no compiled-source claim. Counts are target placements, not distinct source projects. The original API capability grades and signed deployment verdicts are untouched.

Recheck the retained inventories locally (requires the referenced archives already restored):

```sh
python3 benchmark/2026-10-14-demo-reproducibility/audit.py --main "$MAIN" --out "$FRESH_AUDIT_OUT"
python3 benchmark/2026-10-14-demo-reproducibility/test_audit.py
```

`audit.py` reads and hashes only. `outer_remote_verify.py`/`remote_probe.py` document the read-only remote request already executed by root; no need to repeat it. The initial sandbox SSH rejection remains in raw history and is not reported as a successful probe. Original runtime logs stay in their pinned durable archives; no binaries or stderr streams are included in this landing. Machine tests validate claim boundaries; the spec's human review remains pending.
