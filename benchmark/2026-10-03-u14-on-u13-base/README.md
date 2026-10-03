# U14 on each planned U13 effective transaction baseline

## Selected armed-BASE replay after U13 promotion

Outer ACK(90) **2026-10-03T09:39:28+0800** confirms all three boards retained
U13. The selected fresh replay now uses actual armed common **`2abe4a49`** and
61b **`0a31ad35`**, with `--baseline-native` pointing to each armed package.
Only the BASE path/full-SHA parameters changed; no helper, gate, native artifact,
JAR, image, receipt or approval was changed. The U14 metadata bundle hashes are
now **`12d30eb0` / `b0f74132`**; native manifest/inputs remain `3460435a`/`11001e6e`.
The exact two metadata changes and complete unchanged artifact maps are recorded
in `armed-base-replay.json`. Previous unarmed public evidence is archived with
file hashes in `signed-unarmed-history.json`.

Both fresh executors still return **2**, solely for required G2 without an
executable oatdump. Static/G1 and independent native/RB/T4b/frozen checks pass;
outer will run Mac+VM with oatdump_remote. U14 stays disabled and has no window
authorization. `baseline_promotion_confirmed` refers to U13 only, never U14.
The remaining sections describe the earlier pre-promotion preparation; their
unarmed defaults are historical, not this selected transaction baseline.

## Correction and scope

A content comparison against U13 is not a transaction against T8, and U13's own
reference files describe T8 rather than the resulting U13 content. This packet
uses the complete planned U13 candidate identity, checks the per-board effective
payload and retains the two board-local installers without an installer action.
It does **not** claim that U13 has been promoted.

The previously reviewed U14 common/61b objects already have the correct planned
U13 bindings. They are copied to immutable diagnostic directories, not rebuilt
or rebaked. Their original reviewed byte hashes remain `9b42ddc6`/`f5898447`.
Both copies stay disabled; native manifest `3460435a` and inputs `11001e6e` stay
identical to the approved U14 objects. No registry or gate code is changed.

`final-composition.transaction_base` from the early T8 diagnostic is not selected;
the reviewed U13-based variants are used explicitly, with full per-board hashes.

| Variant | Explicit planned U13 BASE | U14 diagnostic content | Installer pair |
|---|---|---|---|
| 5ea/5cd common | `91272eaf` | `9b42ddc6` | `2c9a5294` twice, unchanged |
| 61b | `8861a11a` | `f5898447` | `51e1b525` twice, unchanged |

Full hashes and persistent paths are in each `composition.json`. The actual
`u7_executor --dry-run` uses that BASE's **native directory**, not T8 or the
other board's package. No `--apply`, serial, lock, device or remote oatdump is
used. The preparatory correspondence from cx-t0 is independently checked:
armed `2abe4a49`/`0a31ad35` differ from their signed unarmed counterparts only
in `rollout_ready` and `rollout_blocker`; all listed payload bytes match. This
permits later parameter substitution, **not a promotion claim**.
Outer independently confirmed that two-field correspondence at board ACK(90)
2026-10-03T09:26:08+0800. Actual per-board promotion/signoff is still separate;
this packet's selected dry-runs use the decided unarmed BASE hashes.

## Relative increments

`increments.csv` lists **7 native paths, 2 JARs and 19 changed image files per
variant** (28 changed effective paths). Native paths are bridge7daa, host341c,
Flutter libandroidfff9, Gecko native_abi f861, libicuuc9b36's two aliases, and
the added ICU compat4886. JARs are runtime0349 and stubs87cf.
The complete **27-image group** remains selected and paired: 19 changed and
8 byte-identical to U13, all shown in `image-group.json`. Unchanged media/zlib,
compat and policy objects do not become newly counted increments.

## Fresh Mac results and refusal

Both real executor attempts return **2**, not PASS: their signed static checks
pass and G1 passes, then required G2 refuses because no executable oatdump was
provided. The original stderr and JSON refusal are retained. No remote wrapper
is invoked from this lane and no historical G2 is borrowed.

Independent fresh static, candidate/baseline N1/N2 with the **active** registry,
RB, T4b and frozen checks return zero for both variants. The executor stops at
G2, so these separate native results are not claimed to have run inside that
failed executor attempt. `gate-exits.md` and `results.json` retain every exact
command exit, including raw strings review refusals. Supplemental ABI/calls and
219-consumer checks compare the unchanged approved native pairs; a new ICU target
has no invented old-version ABI PASS. Public evidence is cold-readable.

## Prepare again with explicit BASE parameters

```sh
python3 benchmark/2026-10-03-u14-on-u13-base/run.py

python3 benchmark/2026-10-03-u14-on-u13-base/run.py \
  --common-base "$WORKSPACES/westlake-inputs/generations/u13-stageA-91272eaf-20261003/armed-bundle" \
  --common-base-sha256 2abe4a4917e09d53f47edcfec0ec21b9e131fc72253b8f4aa3d47ff87e8d5aa0 \
  --61b-base "$WORKSPACES/westlake-inputs/generations/u13-stageA-61b-8861a11a-20261003/armed-bundle" \
  --61b-base-sha256 0a31ad3515c021ce22d00c3d2e2543e16f9164a1b7d2fc6d1d966f3f2fbba761
```

The second command is **prepared, not executed**. Wait for outer's acceptance
of cx-t0's actual promotion correspondence; only then switch BASE path/SHA
parameters. New immutable candidate copies change only BASE metadata; reviewed
native manifest/inputs, payloads, image references and approval files remain
unchanged. Different effective content, wrong variant or reused output refuses.

For a single metadata copy, `rebind.py` takes mandatory `--variant`, `--base`,
`--base-sha256` and fresh `--out` inside this packet's `.artifacts`.
For outer's later Mac/VM production replay, `replay-production.sh` requires
`U14_U13_PRODUCTION_REPLAY=outer-approved`, surface, matching BASE path/full SHA,
disabled candidate and trusted oatdump. Its default exits **78 before any probe**;
even the enabled wrapper invokes only `u7_executor --dry-run`, never deployment.

`landing-paths.txt` lists reports, tools, validators, specs and small evidence.
Persistent artifacts stay under this lane's `.artifacts`; original U13/U14
bundles and U15 work remain untouched. VM/image-production replay belongs to
outer. Transaction readiness, promotion and window authorization remain false.
