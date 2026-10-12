# Restore v6 exact frozen delta review

## Evidence and decision

**Exact offline delta accept, disabled and unsigned** freeze `fd8aed69fc070d9d143296b65c64259180fafb8f7646f04b090eb06e57968286`, listing `7fcc709375bf66c414be026ab9050c5cf60ae711de850f7d91318f6779d91133`. All 54 delivery paths exist and all 51 freeze SHA/size rows match. This is not derived equivalence, original61b-seal restoration, 5cd write authorization, UI acceptance, or sealing.

Compared directly with accepted v5: 487 unique target rows retain identical before/after metadata, sources, prerequisites, directories, UID and every non-content-SHA field. Exactly eight control target SHAs change: entry, three watchdog aliases, classifier, members, startup and startup expected hash. The 463 runtime/stage source SHA/size pins remain identical to v5; their prior acceptance is inherited, **not claimed as a new 769MB byte reread or behavior test**. The 24 control target-to-small-file links were checked physically, including aliases.

Final manifest is `f2d0ae4776be5d07f1145104908594eadce70c4b6aa93cbb21b302f187ddeaad`; plan is `35276f1ef9f4e19996e5312db9e1a5cd111e76ededa559aae1895a764e8a07d2`.

## Program and transaction boundaries

The imported programs are exactly reviewed watchdog `2b635ef1...` and classifier `0bf966d7...`, via T0 combination `c6c8f6145ae72da1331e5d461d4959532efeddd7`/composition `5a591c13...`. The new composition_update validates the pinned inventory, disabled24-target donor, scope, member content, unrelated guardian bytes and independent program pins; it imports only watchdog/classifier content, not donor before/after or authority.

Existing v5 function ASTs differ only in compile_package and main's self-test selector; composition_update is the one added function. Exact-seal, invoke, directory ownership, rollback and cleanup functions remain identical. Transaction executor remains exact `496fa979...`. Thus no old failure matrix is rerun or silently waived.

All thirteen boot members, entry watchdog/helper pins, decoder probe, startup member/decoder hash and startup expected hash close. The r3 helper/worker and strict final child_owned remain unchanged. The package still requires actual5cd UID20011300; startup is disabled/PENDING, with no authorization imported. Three stage evidence paths relocate from producer to main with unchanged SHA/target selector; no metadata or byte-equivalence exception is added.

## Sparse delivery and clean replay

The replay inventory's 31 small inputs are SHA/size-verified. Every v6 input appears in the54-file landing list; inherited v5 inputs already exist in main with their exact pins. Nineteen small controls are delivered; large runtime is deliberately omitted and regenerated from declared main/CAS/T0 inputs.

The delivered replay tool copies only that inventory into a fresh clean directory, prohibits original privateT4 open attempts and subprocess calls, and runs the eight changed-version tests, which rebuild runtime into a temporary directory and compare the frozen manifest. Its isolation is a Python audit, not an OS sandbox. Author clean replay reports 8/8, no failures/errors, no denied private reads, exact manifest f2d0ae47, and zero subprocess/device calls. We cite that receipt without duplicating it; outer is independently replaying the newly landed main tree. No transaction matrix or production-lock simulation is included.

Outer command, after landing, using a fresh output:

```sh
export WORKSPACES="$HOME/orca/workspaces"
python3 "$WORKSPACES/westlake-harness/benchmark/2026-10-12-v1-seal-assembly/restore-v6/replay_clean_landing.py" \
  --workspaces "$WORKSPACES" --out "$OUTER_FRESH_REPLAY_DIRECTORY"
```

This command is recorded only. User-derived realization acceptance remains pending; no device, VM, remote, signal, runtime change, original candidate edit, signature or push occurs in this review.
