# category-HOME, statically tested: refuted as the white discriminator (it is universal, from our projection)

#90, offline, no board. Follow-up to `u13-white-selfterminate`, which flagged a common signature for the alive-white
keys x + fd-saber: **category-HOME launch + `callerRecordList empty` + `verificationAllToken failed`**. This statically
tests the `category-HOME` part. **Result: category-HOME is refuted** — it is universal (our LAUNCHER→home projection,
shared by lit keys), so it cannot be the discriminator; the strip-HOME fix would move **0** keys. (`evidence/
category-home-refuted.txt` has the data.)

## ① Who has CATEGORY_HOME — split by lit / white / dead
Two different "category HOME" exist; both refute the hypothesis:

**(a) Launch-intent category** (what the launcher sends, `B47-SLA intent … categories={…}`): **HOME is in LIT keys too.**
| group | keys checked | launch category |
|---|---|---|
| **lit** | helloworld, wikipedia, fd-uhabits, markor | `MAIN categories={android.intent.category.HOME}` |
| **lit** (other path) | zigzag, fd-noice, newpipe | `action=null categories=null`, launchMode=2 |
| **white** | x, fd-saber | `MAIN categories={android.intent.category.HOME}` |

Lit **and** white both launch with CATEGORY_HOME → per the separation rule (a lit key has it ⇒ not the cause).

**(b) App manifest intent-filter**: **no app declares CATEGORY_HOME; all LAUNCHER.** Spot (apkanalyzer): saber (white),
wikipedia (lit, +`MULTIWINDOW_LAUNCHER` alias), uhabits (lit) all = `CATEGORY_LAUNCHER`, none HOME. **Fast corpus scan**
(unzip `AndroidManifest.xml` | `strings` | grep `category.HOME`) over `apks/{fdroid,fdroid100}`, `corpus-v2/apks`,
`apks-77/vm-copies`: **scanned 159 apks, manifest-declares-`category.HOME` = 0.** So there is no lit/white/dead split to
tally — HOME is not an app property.

## ② What our projection does with it (the source of the HOME)
`bms/src/adapter/framework/package-manager/jni/apk_bundle_parser.cpp:61`, `MapCategory`:
```cpp
if (androidCategory == CATEGORY_LAUNCHER)  return "entity.system.home";
```
At install, every Android launcher activity's `CATEGORY_LAUNCHER` is projected to the OH `module.json` skill **entity
`entity.system.home`** (`apk_bundle_parser.h`: *intent-filter.category → Skills.entities via MapCategory*). OH then
treats the ability as the home/launcher entity and SceneBoard launches it with `want.action=action.system.home`; the
Android intent round-trips to `action=MAIN + categories={HOME}` (the `B47-SLA` line). `entity.system.home` is in fact
OH's **standard launcher entity** (OH apps use it for the home-screen ability), so the forward mapping is intended; the
Android-side `CATEGORY_HOME` is a **reverse-mapping artifact** (it should map back to `CATEGORY_LAUNCHER`, not `HOME` — a
cosmetic mismatch). This applies to **all 159 apps** → universal → cannot discriminate lit from white.

**OH 6.1 AMS `verificationAllToken` / `callerRecordList`:** the OH AMS source
(`ability_manager_service.cpp` `StartAbilityInner`) is **not** in `westlake-inputs` (only the compiled
`activity__oh_ability_manager_client.o`); reading it needs hw248/a2hlab. Reasoned from behavior: `verificationAllToken`
checks the ability token against mission/caller records, and `callerRecordList is empty` = a launch with no caller — true
for **every** home-launched app (all of them, via the universal `entity.system.home`), yet only x/fd-saber **fail**
verification. So the empty `callerRecordList` is **necessary but not sufficient**; the failure fires on the
**terminate/re-start** path (x's trampoline finish; fd-saber's terminate before `performCreate`), not on the initial
launch — see `u13-white-selfterminate`.

## ③ Does the separation hold → the minimal fix / prediction
**The separation does not hold for category-HOME** (lit keys share it) → **the strip-HOME fix is refuted**:
- **Fix (a) strip CATEGORY_HOME in the projection** (map `CATEGORY_LAUNCHER` to a non-home entity, or fix the reverse
  mapping to `CATEGORY_LAUNCHER`): **predicted keys moved = 0.** Lit apps launch with HOME and render fine, so removing
  HOME would not make x/fd-saber render — their white is the terminate-path failure, not the HOME launch. Changing
  `entity.system.home` is also risky: it is OH's standard launcher entity, so remapping could break the launcher icon /
  launchability for **every** app. Not recommended as the white fix.
- **Fix (b) AMS-side caller record** (the real lever): give the home-launched ability a proper mission/caller record so
  `verificationAllToken` passes on the terminate/re-start path, and (x) carry the trampoline hand-off to the real
  activity. This is the `u13-white-selfterminate` fix target; it is independent of the HOME category. **Predicted keys
  moved:** the ones whose white is the terminate-path failure — x and fd-saber (and any future app that finishes/relaunches
  its launch ability); **not** a HOME-category set.
- **Optional correctness nit (not the white fix):** fix the reverse mapping so an OH `entity.system.home` launch converts
  back to Android `CATEGORY_LAUNCHER` (not `CATEGORY_HOME`), so apps that branch on `getCategories()` see LAUNCHER. Low
  priority; does not move the white keys.

No on-board experiment needed — the static separation (0/159 manifest HOME; lit keys share the launch HOME) is
conclusive that category-HOME is not the cause.

## This round's rule
Before promoting one leg of a "common signature" to a cause, run the separation on *that leg*: category-HOME looked
shared across x/fd-saber, but it is **universal** (our `CATEGORY_LAUNCHER → entity.system.home` projection, round-tripped
to `CATEGORY_HOME`), present in lit keys too — so it is a launch-path constant, not the discriminator. The discriminator
stays the terminate-path `verificationAllToken failed`, which HOME does not cause by itself.

## Files
- `evidence/category-home-refuted.txt` — lit-vs-white launch categories, the 0/159 manifest scan, the MapCategory source,
  the AMS behavioral reasoning.
- `results.json`, `documentation.json`, `landing-paths.txt`.

## Boundaries
Offline; no board; no push; static only (no on-board experiment — static is conclusive). OH AMS source not local (needs
hw248/a2hlab) — AMS behavior reasoned, not source-read. Sources read read-only: the corpus apks
(`westlake-inputs/apks`, `corpus-v2`, `apks-77/vm-copies`), the U13 hilogs (`westlake-harness-u7-executor`), the installer
projection source (`westlake-harness/bms`).
