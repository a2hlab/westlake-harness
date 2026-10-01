# U10 J-layer boot-assessment — can each fixplan J entry be done in the adapter layer (no BOOT touch)?

Source: `benchmark/2026-10-01-u8-death-clusters/no-fatal-fixplan.json` (master `66e913de6`), the three
`layer: J` rows. All three land on classes that resolve against the **boot classpath**, so the question
per entry is: can the adapter layer (the PathClassLoader `oh-adapter-runtime.jar`, or the BCP
`adapter-mainline-stubs.jar`) intercept it, or does it need a boot-image rebuild?

## Grounding facts (evidence)
- `oh-adapter-runtime.jar` is **not** on the BCP and **not** in the boot image; it is loaded by a
  PathClassLoader. It can subclass non-final framework classes and reflect-swap registries, but it
  **cannot shadow a method of a boot class that the app calls directly** (DIGEST 2026-09-29 #80, line 413;
  `benchmark/2026-09-29-wikipedia-line/`).
- `adapter-mainline-stubs.jar` **is** a BCP jar **compiled into the boot image**. ART validates the
  on-board jar's dex checksum against the one recorded in the boot image's vdex; a changed BCP jar whose
  image was not rebuilt → image rejected → `CheckSystemClass` FATAL, every app (incl. controls) white
  (DIGEST T7c, line 427; the G1/G2 predeploy gate, line 435). So **image + BCP jar must change together**
  via the `art-r155` dex2oat toolchain (line 440; `benchmark/2026-10-01-image-predeploy-gate/`).
- **`dex2oat` is not on this Mac** (checked: absent from the Android SDK; it is a Linux ART tool). The
  boot-image rebuild chain runs in cc-wiki's `art-r155` build environment, not here.
- Class locations (dexdump, this assessment): the U8 `adapter-mainline-stubs-t7e.jar` (206 classes) holds
  `android/graphics/ColorMatrix` (T7e added it) but **not** `com.android.internal.util.Predicate`,
  `android.graphics.Bitmap`, `android.graphics.ColorSpace`, or `java.util.Locale`. So Bitmap/ColorSpace/
  Locale are in the **stock boot dex** (framework.jar / core-oj), which the lab's stubs jar does not carry.

## Per-entry assessment

| entry | class / change | where it lives | adapter-interceptable? | route | Mac-reproducible? |
|---|---|---|---|---|---|
| **packlist** | ADD `com.android.internal.util.Predicate<T>` (new interface) | missing from BCP; **app-referenced** (packlist `IOUtils$1 implements` it) | **Maybe — via the runtime jar** | add to `oh-adapter-runtime.jar` (U10) ; fallback = stubs jar + image rebuild | **Yes** (runtime-jar attempt) |
| **musicplayer** | GUARD `android.graphics.Bitmap.createBitmap(source,…)` color-space (method-body change) | `framework.jar` boot dex (app calls `Bitmap.createBitmap` directly) | **No** | patch framework boot dex + dex2oat image rebuild (image+jar together); secondary = native libhwui | **No** (needs art-r155 dex2oat) |
| **libresudoku** | FALLBACK in `java.util.Locale.getDisplayCountry` (method-body change) | `core-oj` / apex boot dex (deepest) | **No** | patch core-oj boot dex + dex2oat image rebuild; secondary = native LocaleNative/ICU | **No** (needs art-r155 dex2oat) |

### packlist — Predicate (try the runtime jar first)
`com.android.internal.util.Predicate` is a pre-API-28 hidden interface the app's `IOUtils$1` implements;
AOSP 14 removed it, so route-A's class-linker hard-resolves it → `NoClassDefFoundError`. Unlike a class
*referenced by a boot class* (which the runtime jar cannot shadow — DIGEST 413 tagsoup example), this one
is referenced by **app code**, and the boot classpath does not define it. So the app's own class loader
(whose hierarchy includes `oh-adapter-runtime.jar`) may resolve it from the runtime jar if we add it there.
The fixplan hedges ("adding only J10g runtime jar is not proven sufficient"), so this is a **low-cost
on-board test, not a certainty**: add the committed draft `com.android.internal.util.Predicate` (boolean
apply(T) / erased apply(Object)Z, from `benchmark/2026-10-01-j10-prep/src/Predicate.java`) to the U10 jar
via `build_j10g.py --extra-sources`, open a window, and read whether `ACRA.init`/`IOUtils$1` links. If it
still `NoClassDefFound`s, fall back to the BCP route (stubs jar + image rebuild), which is **not**
Mac-reproducible. **Recommend: carry Predicate in U10 (runtime jar), gated by the window.**

### musicplayer — Bitmap color-space guard (boot image / native)
`Bitmap.createBitmap` is a method the app calls on the boot `android.graphics.Bitmap`; the runtime jar
cannot shadow it. The Java guard must be patched into `framework.jar` and the boot image rebuilt
(dex2oat, image+jar together). Not Mac-reproducible. The fixplan also names a **native** root
(`libhwui` `Bitmap.nativeComputeColorSpace` discarding color metadata) — the Java guard is a workaround;
the durable fix is native. **Recommend: hand to the image/native lane (cc-wiki art-r155), not this JAR lane.**

### libresudoku — Locale.getDisplayCountry fallback (boot image / native)
`java.util.Locale` is a core-library class in the deepest boot dex (core-oj / apex). Not interceptable by
any adapter jar. Needs a core-oj boot-dex patch + dex2oat rebuild; secondary native root is
`LocaleNative`/ICU metadata. Not Mac-reproducible. **Recommend: hand to the image/native lane.**

## Bottom line for the U10 JAR (this Mac lane)
- **U10 JAR can carry exactly one of the three: `Predicate` (runtime-jar attempt)** — fold into the
  U10 base (`11974b7b`) via `build_j10g.py --extra-sources <Predicate.java>`, verify on-board.
- **Bitmap + Locale are boot-image (and ultimately native) work**, requiring the `art-r155` dex2oat
  toolchain + the image+BCP-jar-together discipline (G1/G2 predeploy gates). They are **not** reproducible
  on this Mac and do **not** belong in the adapter JAR. Route them to cc-wiki / the image-native lane.

Outer loop decides scope; this lane is ready to build U10 = split base + Predicate the moment that is approved.
