# Launcher trampoline scan: 66 exact U7 APKs

## What the first assumption got wrong

Global `startActivity` searches report callbacks and unrelated Activities as startup jumps; literal-only searches miss Wikipedia's ActivityResult route. Conversely **ActivityResult.launch is not always an Activity jump**: Reader, Droid-ify and Loop pass `android.permission.POST_NOTIFICATIONS`. The operand-context pass excludes these three from app-to-app routing candidates.

All **66 APK SHA-256 values match frozen U7 inputs**, across **214 DEX**. Results: **23 conditional candidates** (22 keys with literal starts, plus Wikipedia's Intent-valued ActivityResult call), **34 no match in the bounded Java lifecycle graph**, **9 unknown**. These are predictions, not execution proof or diagnoses of second-window scene attachment.

## Evidence and rules

`results.json` is the full 66-row machine table; `TABLE.md` is its compact view. `evidence/index.json` pins input/tool/signed-score and evidence hashes. Each `.json.gz.b64` is a text-packaged deterministic gzip of JSON containing the original aapt2 manifest dump, parsed manifest, APK/DEX hashes, dexdump line/offset/invoke instructions, retained call graph and analysis. These are disassembly metadata, not APKs or binary patches. `evidence/focused-bytecode.json` retains actual nearby instructions for **all modern sites**. Decode a bundle with `python3 benchmark/2026-10-01-trampoline-scan/report.py --key wikipedia`.

1. Select manifest MAIN+LAUNCHER within the **same intent filter**, resolve aliases, exclude literal disabled launchers and inspect inherited onCreate(Bundle), onCreate(Bundle,PersistableBundle), onResume. Enabled resource references remain potentially enabled; no resource-value evaluation is claimed. Runner overrides are reported separately.
2. Match invoke opcodes with Intent signatures, not strings. Follow same-hierarchy synchronous helpers up to three helper edges; superclass lifecycle delegation is free. Conditional paths are possible, not guaranteed immediate execution. Callbacks, cross-class helpers, reflection and native code are outside scope.
3. Recognize ActivityResultLauncher subclasses separately. The nearest captured argument assignment distinguishes permission strings (excluded), Intent objects (modern candidate), and unresolved Objects (untyped candidate). This local operand evidence is **not full control-flow/dataflow proof**.
4. Record finish independently. Arbitrary finish presence in the graph does not prove the same branch as start. Class constants are destination candidates unless captured constructor/register operands bind them.
5. Missing/native/depth-limited code stays unknown. A Java scoped non-match does not mean the app never launches another Activity.

The source spelling is dexdump Dalvik assembly (`Lowner;.method:(...)V`), equivalent to smali invoke targets (`Lowner;->method(...)V`). APK/DEX hashes support independent baksmali verification; this is not a class-name heuristic.

## Priority intersections

| Key | Signed U7 | Source witness (DEX dump line) | Interpretation |
|---|---|---|---|
| wikipedia | white | DefaultIcon alias -> MainActivity.onCreate: L4442215 new Intent(v10), L4442216 InitialOnboardingActivity, L4442217 constructor, L4442219 launch(v10) | Conditional **Main -> InitialOnboarding**, not the reverse. Window attachment requires separate runtime evidence. |
| fd-AppManager | white | SplashActivity.onCreate: L726863 MainActivity, L726865 startActivity, L726866 finish | Direct splash route; modern authentication/permission sites also retained. |
| fd-shatteredpixeldungeon | white | AndroidLauncher.onCreate: L427333 AndroidMissingNativesHandler, L427335 startActivity, L427336 finish | Conditional missing-native fallback, not normal successful game startup; native helper gap remains. |
| fd-noice | own UI | MainActivity.onCreate: L2210099 AppIntroActivity, L2210101 startActivity | Historical white key is now lit; routing does not imply white. |
| noice | own UI | MainActivity.onCreate: L2185789 AppIntroActivity, L2185791 startActivity | Independently pinned APK, also lit. |
| fd-organicmaps | own splash | SplashActivity.onCreate: L704008 MapPlaceholderActivity, L704010 startActivity, L704011 finish; modern onResume also retained | Candidate splash route. U6/U7 raw termination still disappearance-cause-unknown; no T7d causal claim. |
| fd-reader | own welcome | MainActivity: L3442275 RequestPermission, L3442289 POST_NOTIFICATIONS(v1), L3442290 launch(v1) | **Permission-only, not app-to-app trampoline**. Nearby CursorWindow constant is not an Activity destination. |
| fd-app | white | No route found; helper-depth limit at AndroidApplication.getApplicationLogger | Unknown, not negative. |
| fd-mobile / termux / x | black / white / white | No matching invoke in bounded launcher lifecycle graph | Scoped non-matches, not proof against all possible runtime routes. |

JSON preserves the requested historical eight-key symptom set and first-screen pair separately. Current signed U7 white/black has **seven** keys: AppManager/app/SPD/termux/wikipedia/x plus mobile. Noice's two keys are now lit. **Three of seven** have candidates (AppManager, SPD, Wikipedia), one is unknown, three have no scoped match. Of the first-screen pair, Organic Maps has a route; Reader has only a permission request.

## Controls

- **ooniprobe**: one declared Activity, signed own UI, no lifecycle start or bounded-code gap: Java-scope negative.
- **fd-stk**: one declared Activity, signed own splash, no Java lifecycle start, but nativePause/nativeResume/onNativeDropFile/onNativeOrientationChanged lack Java bytecode: **unknown/non-alert**, not a second strict negative. Outer explicitly accepted at ACK(95) **07:00:35**.
- **fd-fitness**: nine declared Activities, signed own UI, no bounded lifecycle start or gap: additional Java-scope negative. Activity count alone is not the test.
- Reader/Droid-ify/Loop permission calls are adversarial non-trampoline controls; Wikipedia's Intent call is the modern positive. Lit Noice routing shows that a candidate is not a rendering-failure prediction.

## Replay

```sh
python3 benchmark/2026-10-01-trampoline-scan/test_scan.py
python3 benchmark/2026-10-01-trampoline-scan/report.py > /tmp/trampoline-replay.json
cmp /tmp/trampoline-replay.json benchmark/2026-10-01-trampoline-scan/results.json
python3 benchmark/2026-10-01-trampoline-scan/collect.py \
  --input-root "$INPUT_ROOT" --vm-mount "$VM_MOUNT" > /tmp/trampoline-intake.json
python3 benchmark/2026-10-01-trampoline-scan/collect_focus.py /tmp/trampoline-intake.json \
  --input-root "$INPUT_ROOT" --vm-mount "$VM_MOUNT" > /tmp/trampoline-focused.json
```

Use the actual Mac-mounted `app-inputs-u6` root and VM mount base. Absolute VM symlinks are translated under that base. Tools default to Android SDK build-tools 37.0.0; exact hashes are pinned, and `--aapt2`/`--dexdump` select another installation. Native sidecar changes do not change APK routing, but APK drift is a hard refusal. No device commands or input mutations.

Delivery: `landing-paths.txt`; combined exact list and gate receipts: `../2026-10-01-u7-scoring/followup-landing-paths.txt` and `followup-validation.json`. Root README/DIGEST changes are scoped lines, not wholesale replacements.
