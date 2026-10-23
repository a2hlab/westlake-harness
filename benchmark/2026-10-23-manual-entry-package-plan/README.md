# T117 — existing manual-entry package applicability

**A parameterized wrapper exists, but serial/root/UID flags alone do not establish a valid 5cd package. No build or deployment was performed.** T116's current preimage is pending. This is an applicability plan, not a repaired or approved candidate.

## Original, verified chain

T34's original t08 ran the following historical command, with cwd `$T34_RETIRE_PRIVATE/old-suite-r3`:

```text
sh benchmark/2026-10-19-toutiao-icon-reentry/generator/derive-candidate.sh
  --out $T34_RETIRE_PRIVATE/r3-deploy-20261021-r3
  --root /data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261021-r3
  --enable --approved-by outer(codex)
```

Those flags document historical61b signoff. The user has already authorized necessary work on all three boards; the concrete 5cd candidate still needs technical review and current rollback binding. The original argv/stdout/stderr/rc were independently rehashed against CHAIN.json: t08 rc0; stdoutSHA203bfa8b…; argvSHA870d1869…; stderr empty. t01 and t04's eight raw files also match their indexed hashes. These are retained execution logs, not tests run by this card.

The main wrapper and the original t08 workspace wrapper are byte-identical, SHA `c2855d54eb7acea0502731a5be5c1310a6d9471048beae11df59d8186a3b0667`. Original t08 logs explicitly report the r3 watchdog input/outputSHA8bf74a08…; no watchdog or renamed implementation content was opened here. Historical output identities, all22 member hashes and12 raw pins are in results.json. Main's default implementation source was not inspected or assumed to be r3.

T34's final-signoff provides the later board approval/recovery reference. Its acceptance was warm ordinary return, with natural-exit reentry not observed in that window. T87 is separate successful ordinary-reopen evidence. Prior offline tests are recorded as71/0 retirement, parser21/reentry29/race116 and generator cascade; the original fixture limitations remain in results.

## Wrapper facts and concrete blockers

All line numbers below refer to `benchmark/2026-10-19-toutiao-icon-reentry/generator/derive-candidate.sh`.

| Binding | Wrapper behavior | Consequence for5cd |
|---|---|---|
| serial/root | lines18–20,35–36; root restricted to `recovery-attempts/icon-manual-*`; new output required | Existing supported flags; new root must still be selected and reviewed, not guessed or copied from61b |
| owner UID | lines30,37,74,223 only default/parse/log/generation metadata | `--owner-uid 20011300` does not rewrite or prove payload identity behavior; current UID awaits T116 |
| implementation | lines118–122 copy src/src-new verbatim | No fixed-r3 SHA enforcement in that branch; use approved immutable input staging, not an unchecked default source |
| startup | lines171–181 pin61b template; replace only approval/enabled/serial/members | JIT/request/start-parent/old-stop values stay61b-derived; no CLI for target-specific bindings |
| init cfg | lines149–154 rewrite service and ready property | CHAIN.json:122 explicitly prohibits installing generated recovery.cfg over live init; preserve current board init semantics |
| recorded command | lines238–240 omit serial/UID/service | Keep actual argv externally; build-command.txt alone cannot reproduce nondefault identity |

Historical5cd metadata differs from the wrapper template in four **unexposed** fields:

| Field | Template61b | Historical5cd |
|---|---|---|
| STARTUP_OLD_STOP_SHA | empty-fileSHAe3b0c442… | NONE |
| STARTUP_JIT_SHA | aa1234d2… | b42a28e7… |
| STARTUP_START_PARENT_SHA | f77f0f70… | fc0444a4… |
| STARTUP_REQUEST_SHA | f871e6a1… | 011a1625… |

Full hashes and source pins are in results. These historical differences are not claims about T116's current bytes. A startup template edit would also violate this wrapper's fixed template pin; this card does not edit it, substitute constants, or weaken verification. No supported complete5cd adaptation recipe has been established by the reviewed wrapper.

## Fixed versus derived bytes

Keep the approved r3 implementation identities from CHAIN unchanged, including watchdog8bf74a08, reentry-common43d7b073, seamsfebc7094, exit-verdictc0751340 and route-owner6bce7c3c. These hashes are metadata constraints, not new source inspection. The existing wrapper derives config-common(ROOT), entry's watchdog hash, members, startup and expected; those deployment outputs need fresh target-specific SHA receipts. New5cd output hashes are **unknown**, not copied from61b.

Results include an explicitly disabled, placeholder argv shape. It is not executable until exact r3 staging, target bindings and an applicable existing recipe are supplied. No `--enable` or approval identity is proposed for5cd.

## Preimage and rollback

T116 must supply same-boot5cd init/root/owner identity and current controls/member/boot-copy hash metadata. T52's accepted R4 baseline copy identities (watchdog2b635ef1, entry81dd0557, route-owner6bce7c3c) provide a historical recovery chain, not permission to replace a newer current preimage. Its execution review accepts restoration evidence and says the candidate was withdrawn; it is not full contract PASS.

Any later approved package/window must bind rollback to the exact current5cd preimage and original metadata. Do not substitute61b's cfg, serial, UID or startup values. No reboot/maintenance/runtime orchestration is authored here.

## Reproduce metadata review

```sh
python3 benchmark/2026-10-23-manual-entry-package-plan/check_metadata.py --main "$WORKSPACES/westlake-harness" > "$HOME/.local/share/westlake/t117-outer-review-20261023/replayed.json"
cmp "$HOME/.local/share/westlake/t117-outer-review-20261023/replayed.json" benchmark/2026-10-23-manual-entry-package-plan/results.json
```

`--private` accepts the retained original T34 receipt directory. Original local executions are in `.private/`. No builder/test suite execution, device/remote/REA calls, prohibited implementation reads or new approval. Shared Git refs remain previously denied; no repeated Git write attempt, author_commit=null, path-only handoff for outer landing.
