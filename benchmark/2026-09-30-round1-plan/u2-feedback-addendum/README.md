# U2 handoff correction after migration thaw

The original U2 receipt was already delivered in board ACK(90 done) at 13:58 and committed in the cx-bms freeze `8ff5a3f47`. The 17:51 dispatch incorrectly described it as unfinished. Its hashes and validation still pass. This additive receipt republishes the complete 42-key table and J4/N3 lists, incorporating cx-t0's two later corrections; it leaves that historical receipt and all frozen predictions unchanged.

**Use [J4.json](J4.json), [N3.json](N3.json), [unlit-42.csv](unlit-42.csv) and [next-clusters.json](next-clusters.json) for the current handoff.** Ranking and primary ownership remain J4 19 / N3 20 / input 3. Native dependency visibility is first for 7 apps (plus 3 separately observed secondary cases); boot classpath API closure is first for 5. Noice MediaRouter and fd-noice SSLSockets remain J4. Unknown mechanisms remain investigation items, not claimed repairs.

## Corrected evidence

| App | U0 original log | U2 original log | Correction |
|---|---|---|---|
| Fennec | 31019: libjnidispatch relocation lacks `__errno` | 31386: relocation lacks `__sF`; resource fallback at 31401 | The same final JNA message masked native progression. N3 stdio ABI closure, not a proven APK resource omission. |
| Firefox | 32491: relocation lacks `__errno` | 32577: relocation lacks `__sF`; resource fallback at 32592 | Same correction. |
| VLC | Previous U2 report inferred resource projection work from the active theme failure | Original APK SHA matches the run; read-only `aapt2` reconstruction exactly matches cx-t0's theme graph | Transparent/Empty parent chains lack `background_default` (0x7f040072); Onboarding's chain contains it. Investigate **why that context was selected**. No OH parser defect or native color fallback is established. GLESv2 visibility remains a separate observed dependency wall. |

`corrections.json` holds full log paths, SHA-256, attributed PIDs and numbered excerpts. `vlc-theme-audit.json` records the independent rerun against the exact APK and the reused recipe from cx-t0's `2026-09-30-n3-native/audit_resources.py` (N3 delivery commit `9b6d6df02`). JNA diagnostic ordering is checked against both U0 and U2 raw logs, not inferred from the later Java exception.

Corrected causal-checkpoint comparison: **15 hits / 21 changed or missed / 6 unknown** (42 total), instead of the historical symptom-level 17/19/6. Two additional misses are the `__errno` → `__sF` progression. VLC remains one known secondary wall among the 21 changed first checkpoints; first-or-known-secondary coverage is therefore 16/42. This is descriptive cross-profile transfer, not prospective accuracy. Lighting remains the outer's **24**, with literal frozen U1 light labels 22 hits / 5 false alerts / 2 missed lights. No screenshots were re-adjudicated.

J3 raw runs exist but have no screenshot-signature report in that directory at this receipt. They are not merged into U2 counts. This task remains offline, with no board actions or runtime modifications.

```sh
python3 benchmark/2026-09-30-round1-plan/u2-feedback/validate.py
python3 benchmark/2026-09-30-round1-plan/u2-feedback-addendum/build.py
(cd benchmark/2026-09-30-round1-plan/u2-feedback-addendum && shasum -a 256 -c SHA256SUMS)
```
