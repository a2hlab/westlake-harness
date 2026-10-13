# Popup geometry regression: independent file-only review

## Evidence first

The earlier `lit` pre-review for Seal meant identifiable app content, not preserved controls. It was too coarse. StudyTracker and Seal now have **visible first-screen control loss** compared with their exact t3 reference images; neither may be signed as no-regression merely because its process survives.

- StudyTracker: current t5 and t10 are byte-identical (`dc0f6dca...`); only the enlarged/cropped project heading remains. Reference `capture-03/019/20261009T230926-9967cf4a` t10 (`f54568c3...`) shows the project-name input and Cancel/Create buttons.
- Seal: current t5 and t10 are byte-identical (`87e1fc19...`); guide text is enlarged/cropped and the reference Close/Open Settings controls are absent. Reference `capture-02-resume/010/20261009T224717-b747d783` t10 is `ce52a7cb...`.
- APK identities match within each pair. Own-PID first_fatal reports no observed termination for current StudyTracker PID5233 and Seal PID11625. This is a visual/function-control regression, not an inferred crash.

Full paths, image/hilog SHA256 and numbered own-PID excerpts are in `popup-geometry-review.json`; the initial image comparison is in `popup-layout-contrast.json`. All screenshots were personally viewed, including current t5/t10. Outer human signoff remains separate.

## The bounded mechanism

Java popup bounds and logged density are unchanged between reference61b and current5ea: StudyTracker requests720x513, Seal720x1153, both density360/screenDp533x795. The concrete downstream delta is the buffer geometry applied at BBQ update:

| App | Reference own hilog | Current own hilog |
| --- | --- | --- |
| StudyTracker | 44564: fixed1200x1920, while BBQ reports864x657 | 50300: applies864x657 |
| Seal | 38251: fixed1200x1920, while BBQ reports864x1297 | 56429: applies864x1297 |

The reviewed947 runtime source patch changes global `BBQ_nativeUpdate` to apply `b->width/b->height`; it is not restricted to Boat. The adc `ANativeWindow_fromSurface` patch removes the inlined geometry call, but retains the old `SET_BUFFER_GEOMETRY 1200x1920` log and a stale pointer-derived rc. That line therefore does **not** prove a subsequent reset to panel geometry. See the existing port-spec semantic table and disassembly; no new binary modification is proposed here.

These facts strongly support a popup buffer/consumer geometry mismatch as the next target, rather than a logged density change or a transient loading frame. They do not yet prove the exact downstream hwui/compositor consumer or isolated A/B causation. Preserve the running full128 evidence; do not modify its driver or blindly restore global fixed geometry, which would risk the now-working Boat layout.

## Other grades and scope

- dddmodel2 current gray screen is **not a new lit regression**: its exact t3 reference is `not_lit`, also blank; see `dddmodel2-contrast.json`.
- ClipboardEditor also appears vertically stretched, but its observed controls remain visible; do not equate shape change alone with the two confirmed control losses.
- ItsDicey has a historical signed `lit` grade, but its exact old/current images both show a red Activity title and black content. Preserve that historical grade separately; do not claim working dice/gameplay.
- Only canonical window `plan.shards` runner records enter `fresh128-observer.json`; smoke, installs and prior t2b evidence are excluded. Observation does not authorize deployment, interrupt the round, or replace outer signoff.

No HDC, VM, SSH, device action, build, or private-data inspection was performed.
