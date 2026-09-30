# Why did two additional screenshots become lit?

## fd-reader: specific prior fatal wall removed; exact API checkpoint still unknown

U6 raw record `5ea-resume/u6-5ea-resume/5ea34a4500000000000000001123012c/fd-reader/record.json`, under the retained `westlake-harness-bms-deploy/benchmark/2026-10-01-u6-sweep/` root, is re-read through first_fatal. Its record/hilog hashes equal the published U6 evidence, not just a copied interpretation.

- PID 7311 / TID 7335, U6 main_threw **L65239**, causal exception **L65240**: `org.ccil.cowan.tagsoup.Parser` does not implement `org.xml.sax.XMLReader` when calling `XMLReader.setContentHandler(ContentHandler)`.
- Causal frames **L65241–65243**: `android.text.HtmlToSpannedConverter.convert(Html.java:749)` -> `Html.fromHtml(Html.java:246/200)`.
- T7d replaces the incomplete boot-classpath Parser with full AOSP TagSoup. Frozen `v1/evidence/component-priors.json` pins source `benchmark/2026-10-01-image-predeploy-gate/t7d-stub-spec/sources/tagsoup/Parser.java`, SHA `aa68cc4d04869aee423b799eb990237301cf40d2f59b77c47549a88e32b38425`: **L32 implements XMLReader**, **L423 setContentHandler**, **L439 parse(InputSource)** and **L453 parse(String)**. Actual accepted stubs SHA is `d8b2406e...`, bound in U7 expected-run.
- U7 PID 11994: package binding **L25324**, no terminal observed through t20, outer-signed Read You welcome/terms page. APK and external sidecars exactly match U6; J7b/native remain fixed, T7d boot/stubs differ.

This is a concrete, mechanism-matched explanation for removal of the U6 interface-dispatch fatal wall, not a new unidentified native fix. Attribution to TagSoup is strongly supported by the old fatal and actual class implementation change; cross-board results do not isolate one method experimentally. U7 does not log a positive `XMLReader.setContentHandler`/parse callback receipt. Consequently the **strict T7d-tagsoup-full checkpoint remains unknown**, even though a welcome page is signed lit. Frozen t20 prediction was unknown, so this is coverage gain, not a scored hit. No proof of a successful second Activity transition or usable feed is claimed.

## fd-organicmaps: unknown causal movement; only splash now visible

U6 raw record `5ea/u6-5ea-20261001T035212/5ea34a4500000000000000001123012c/fd-organicmaps/record.json` has no terminal-linked Java/native root. first_fatal reports process disappearance (PID 2581/2631, binding **L64208/L81956**) rather than a named missing T7d method. The original signed U6 t20 was white.

U7 still has **process-disappearance-cause-unknown**, PID 8986/9045, binding **L73730/L91205**. Other package-bound processes survive. PID-scoped U7 **L65362** creates `app.organicmaps.SplashActivity`, **L65583** resumes it and **L65699–65700** creates its window session. Outer signed only its logo/attribution splash, not the map. Thus there is **no demonstrated terminal-wall removal** to attribute to T7d; the observable change is white -> own splash under the same APK/native inventory. T7d class/method responsible: **unknown**. Timing, multi-process/lifecycle and scene attachment remain hypotheses, not conclusions from these logs.

Evidence: `gains-u6-evidence.json`, `5cd-prepared.json`, immutable U6 review, and frozen component source declarations. Do not claim all 34 lit screenshots reached functional main content. Organic Maps is the one known t20 forecast error (unlit predicted, own splash observed).
