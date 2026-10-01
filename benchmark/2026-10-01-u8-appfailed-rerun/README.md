# U8 app_failed keys re-run with the fixed tool (61b, 2026-10-01)

**What was wrong.** Three keys of the U8 sweep ended `app_failed` before launch. cc-wiki showed two of them
(page-bizzle, clipboardeditor; the first two keys of the 5cd cv2 run) were searched on a desktop whose app grid was
not drawn yet: 20 layout dumps each with zero app tiles, judged "exact desktop icon absent".

**Fix.** bms_batch now retries a tile-less dump (Home, 5 s, max 3) and reports "desktop not ready" instead
(0aa1798f3); it also keeps the install-window hilog (`install-hilog.txt`, 83d39efa3).

**Re-run** on 61b, same U8 state (RUNTIME `e953c0921536`, BOOTIMAGE `4db882a81732`), after a U8 controls smoke PASS.
facts: `TOTAL keys=4 screenshots_captured=6/6 alive_t5=2 alive_t20=2`. Outer read of every screenshot
(`contact-t5-t20.jpeg`):

| key | U8 sweep | re-run |
|---|---|---|
| page-bizzle | app_failed | **lit** (own editor page) |
| clipboardeditor | app_failed | dead (clicked, back on the desktop at t5) |
| privacyfriendlypasswordgenerator | lit | lit |
| frequent-habits | app_failed | app_failed — a real icon problem, see below |

U8 sign-off amended: **lit 99 → 100**, dead 52 → 53, app_failed 3 → 1.

**frequent-habits, now visible thanks to install-hilog.txt:** the manifest icon resolves to `res/d2.webp` (1485 bytes);
the installer's icon normalizer only handles PNG ("skip, not a decodable PNG") and writes the WebP bytes as
`android/icon.png`; no desktop tile appears. (Earlier "0 png/webp in the APK" counted only `res/drawable|mipmap`;
this APK's resource paths are obfuscated, e.g. `res/BW.xml`, `res/d2.webp`.) Whether WebP icons in general lose
their tile is the next check.
