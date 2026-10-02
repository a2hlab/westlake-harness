# T8 production executor and composition checks

The old production image gate used native underlay JARs as its reference and
declared only the stubs swap. That rejects a valid framework swap while missing
the separate question of whether rebuilt DEX retains the deployed APIs. The
rejected T8 donor demonstrates the distinction: real G1/G2 PASS (36/36 identical
String.hashCode instructions), but the effective-JAR frozen check rejects lost
SSLSockets and reshaped tagsoup Parser. No board was locked or accessed.

The original candidate `a2172f18` / bundle `3df46844` is byte-identical and remains
unarmed. It was not updated to make this test pass. The separate negative-control
bundle is also unarmed, has unknown paired build provenance, and is not a rollout
candidate.

## Production changes

- `generation_bundle.py` accepts the original 28-member boot group and a
  29-member group containing 27 images, stubs and oh-adapter-framework. A
  framework swap requires an explicit reference of 27 images and nine effective
  baseline JARs, each bound to the baseline BOOTIMAGE hash ledger.
- Candidate G1/G2 always use the newly supplied images and the effective
  post-transaction BCP. The reference uses the recorded effective baseline.
  Only genuinely changed stubs/framework segments are declared swaps. The
  trusted image checker and its rejection semantics remain unchanged.
- `u7_executor.py` stages and binds all declared images/JARs while the parent
  remains stopped, binds paired receipt inputs to the effective BCP, and restores
  the original U9 overlay stacks on failure. Hash-bound static policy, baseline
  bundle and tool identities enter the preflight binding.
- `generation_static_checks.py` calls `deployed_class_diff.py --frozen` for every
  changed JAR using an explicit effective baseline. Every changed native ELF is
  scanned on both sides by `open_site_scan.py`; sites are compared by function,
  callee, arguments and occurrence count, ignoring relinked PCs. Namespace API
  calls and potential shared-list literals are also listed. New or removed sites
  and namespace changes require exact review; scanner exit zero is not approval.
  ART images/OAT use G1/G2 rather than native namespace classification.
- `prepare_t8.py` creates a fresh unarmed composition from immutable donors,
  declares both JAR swaps, copies the effective baseline reference, and retains
  unknown provenance as unknown. It never arms a candidate or calls a board.

These paths follow the existing production transaction and trusted gate APIs;
the fixture model tests recovery, not OH kernel behavior.

## Verification

`tests.txt`: 14 new tests PASS, including exact restoration after failure before
and after every one of the 29 image/JAR binds (58 boundaries). These also cover
new images instead of old underlays, both effective JARs, receipt mismatch,
reference tampering/missing members, mandatory pre-device static checks, empty
DEX refusal, namespace changes and exact delta review.

`executor-regression.txt`: 37 existing executor/format tests PASS.
`harness-tests.txt`: 82 repository tests PASS, three expected skips.
Existing scanner and deployed-class suites: 7 and 4 tests PASS respectively.

`negative-image-gates.txt`: real old-T8/new-image G1/G2 PASS using the effective
U9 reference; both BCP swaps are declared. `negative-static.json` and
`negative-production.txt`: the same package is refused before device I/O by
the new production static checks. No native exception was invented for the
negative-control manifest.

The scan also exposes two internal U11i classes absent from deployed U9:
`J10eWebView$DelegateForward` and `J10eWebView$WlCookieManager`. They are separate
review items, not silently allowed because the earlier U10.1 sweep tied U9.
Host/compat open-site changes likewise remain explicit, hash-bound review items.

## Next composition

After cc-wiki delivers the corrected effective-f3bcc9d7 T8 images and paired
receipt, use a new output directory:

```sh
python3 benchmark/2026-10-02-t8-executor-support/prepare_t8.py \
  --base "$U9_BUNDLE" --donor "$SIGNED_U10_1_BUNDLE" \
  --t8 "$CORRECTED_T8_DONOR" --receipt "$T8_PAIRED_RECEIPT" \
  --out "$FRESH_UNARMED_BUNDLE"
```

Review the effective class/open-site deltas, bind approved findings to the final
manifest, rerun every final-byte gate, and submit SHA/fingerprints/three-board
promotion plans to the outer reviewer. This delivery does not authorize arming
or locking. Corrected T8 production dry-run and device activation are still
unverified pending that donor and review.

The separately approved N11h design-only handoff was landed via `land.py` as
master `475cb61692` (18 files); see `n11h-landing.txt`. No N11h binary was built.
