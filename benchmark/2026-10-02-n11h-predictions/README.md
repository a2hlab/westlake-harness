# N11h 61b window — prediction table (written before the window, B10)

Pre-window prediction for the proposed **N11h** host single-owner observation window on 61b. B10 rule: predict
before boarding, pin before deploy. This lane does **not** board; it only reads existing evidence (U9 first-wall
table, U9 outer-signoff, the N11h blueprint, DIGEST) and records falsifiable per-key predictions. The outer reads
t20 at the window and signs `predict_vs_actual`; this lane supplies no lit count.

## What N11h changes (and the oracle)
N11h = on the deployed U9 host (`appspawn-x` 1d3b0881), before the bridge/app namespaces first load, inherit the
already-resident **sealed.child** owners and have `StockOpenNamespace` return a NOLOAD resident handle for the two
exact owner paths. Target metric: **bridge and runtime each a single load base** (U9/U10.1 both show 2 each;
N11f/N11g proved the child callback is clean, so the 2nd copy is minted on the host side). Child dc73a28d,
provider, ART/JVM, all JARs/images stay unchanged. Blueprint:
`$WORKSPACES/westlake-harness-u7-executor/benchmark/2026-10-02-n11h-host-owner-blueprint/README.md`.

Oracle (blueprint §4): "A target that remains white or any control/canary/Wikipedia regression refutes the proposed
gain." So the bet is: the **double-copy is what blanks these windows**; single load-base lets the app's real
session/classloader bind and draw.

## Discriminator — which white is double-copy, which is another wall
From the U9 first-wall table (`benchmark/2026-10-01-u9-sweep/u9-first-wall.{json,md}`, distilled from the U9 sweep
hilog) all 14 `alive-white-window` keys were signed by the outer at t20 (`.../outer-signoff.json`):

- **`no-fatal` white window** (13 of 14) = process + window up, **no fatal in hilog, no content**. This is the
  double-copy signature: with bridge/runtime loaded twice, the app's classloader/JNI native state splits across two
  copies, so the Activity's window is created (OH mints the surface) but the copy wired to the surface never runs the
  app's init — no exception, just blank. These are the N11h candidates.
- **A specific fatal, or an app-class with its own render wall** = another wall that single-copy will not clear.
  Exactly one white key carries a logged fatal (`x`); two more are app-classes with a known separate wall
  (WebView, libGDX/GL).

## Predictions
Vocabulary: **lit** / **still-white** / **unchanged** (control already lit, expected to stay lit) /
**possible-regression** (control that the host-namespace blast radius could break — the refutation signal).

| key | group | U9 verdict | U9 first wall | session-miss | prediction | conf | counts toward N11h gain | why |
|---|---|---|---|---|---|---|---|---|
| fd-noice | session-miss | alive-white-window | no-fatal | **yes** | **lit** | high | yes | no-fatal white + named session-miss = double-copy signature; single owner should bind the session |
| noice | session-miss | alive-white-window | no-fatal | **yes** | **lit** | high | yes | same app as fd-noice (duplicate key) |
| fd-uhabits | session-miss | alive-white-window | no-fatal | **yes** | **lit** | high | yes | plain View habit tracker, no other wall logged; session-miss |
| cv2-org-andresoviedo-dddmodel2 | session-miss | alive-white-window | no-fatal | **yes** | **lit** | high | yes | 3D viewer but no GL fatal logged → not GL-blocked; session-miss → double-copy |
| cv2-ca-vaults-randomlydie | other-white | alive-white-window | no-fatal | unknown | lit | medium | yes | no-fatal white, no other wall; lit iff double-copy is the general cause |
| cv2-com-bytehamster-flowitgame | other-white | alive-white-window | no-fatal | unknown | lit | medium | yes | light Canvas puzzle; no-fatal white → double-copy candidate |
| cv2-com-degeder-yam | other-white | alive-white-window | no-fatal | unknown | lit | medium | yes | no-fatal white, no other wall |
| cv2-com-paultirk-yatoo | other-white | alive-white-window | no-fatal | unknown | lit | medium | yes | no-fatal white, no other wall |
| fd-AppManager | other-white | alive-white-window | no-fatal | unknown | lit | medium | yes | **was LIT in the 2026-09-27 breadth sweep** → it can render; gone white = strong runtime-binding regression candidate |
| fd-app | other-white | alive-white-window | no-fatal | unknown | lit | medium | yes | no-fatal white, no other wall |
| termux | other-white | alive-white-window | no-fatal | unknown | lit | low | yes | no-fatal white, BUT termux forks/execs a shell — the terminal-session exec path could be a separate silent wall; low conf |
| x | excluded-other-wall | alive-white-window | **java:NullPointerException** | no | **still-white** | high | **no** | real fatal: `null cannot be cast to non-null type android.telephony.TelephonyManager` — missing-service wall, orthogonal to double-copy |
| cv2-dev-obfusk-jiten-webview | excluded-other-wall | alive-white-window | no-fatal | no | **still-white** | medium | **no** | WebView app — blank WebView needs a working WebView provider (separate deep wall); single-copy won't supply it |
| fd-shatteredpixeldungeon | excluded-other-wall | alive-white-window | no-fatal | no | **still-white** | medium | **no** | libGDX/GL game — no-fatal white = GL surface/engine not drawing; separate render wall |
| wikipedia | canary/control | lit | — | n/a | **unchanged** | high | no (control) | currently lit; must stay lit; host-namespace blast radius → **possible-regression** is the refutation signal |
| fd-k9 | canary/control | lit | — | n/a | **unchanged** | high | no (control) | currently lit control; watch possible-regression |
| fd-com-amaze-filemanager | canary/control | lit | — | n/a | **unchanged** | high | no (control) | currently lit control; watch possible-regression |
| fd-libretube | canary/control | lit | — | n/a | **unchanged** | high | no (control) | currently lit control; watch possible-regression |

## (2) Keys NOT related to the double-copy — exclude from N11h gain
These stay white for a reason N11h does not touch, so a white result at the window must **not** count as an N11h
failure:

1. **x** — logged Java fatal `NullPointerException: null cannot be cast to non-null type
   android.telephony.TelephonyManager` (`[CHILD_CK] J_invokeStaticMain_main_threw`). Missing/forbidden TelephonyManager
   service, not a runtime load-base problem.
2. **cv2-dev-obfusk-jiten-webview** — WebView app; the blank is the WebView provider/engine render wall (separate deep
   wall seen across the 2026-09 sweep), which remains after single-copy.
3. **fd-shatteredpixeldungeon** — libGDX/GL game; no-fatal white = GL surface/engine not drawing, a render-path wall
   distinct from the bridge/runtime double-copy.

(Low-confidence caveat, still counted as a gain candidate: **termux** — its no-fatal white could instead be the
shell fork/exec path, not double-copy. If it stays white while the session-miss four light, read it as the exec wall.)

## Gain accounting
- **N11h candidate gain = up to 11 white keys** (4 session-miss high-confidence + 7 other no-fatal white, medium/low).
  The 4 session-miss are the blueprint's primary test; if even they stay white, the double-copy→white hypothesis is
  refuted.
- **3 white keys excluded** (x / jiten-webview / shatteredpixeldungeon): another wall, do not count.
- **4 controls** (wikipedia + 3 canaries): expected **unchanged (stay lit)**; any regression refutes the gain
  (host namespace serves every spawn — global blast radius).

## Honest caveats
- This is a **pre-window, probabilistic** table. The double-copy → no-fatal-white causal link is the hypothesis N11h
  tests; it is not proven for any single key (N11f/N11g proved the double-copy exists and the child is clean, not that
  it is what blanks each window).
- "session-miss" membership is only known for the 4 keys the blueprint names; the other no-fatal whites are marked
  `unknown` and predicted `lit` at medium/low confidence purely on the shared no-fatal signature.
- Verdict at the window is **t20 screenshot, outer-read** (ground truth), not process-alive; this lane reports no lit
  count.

## Evidence (read-only)
- `benchmark/2026-10-01-u9-sweep/u9-first-wall.{json,md}` — per-key first wall / family / first fatal (14 white keys).
- `benchmark/2026-10-01-u9-sweep/outer-signoff.json` — t20 verdicts (14 `alive-white-window`, canaries `lit`).
- `$WORKSPACES/westlake-harness-u7-executor/benchmark/2026-10-02-n11h-host-owner-blueprint/` — N11h mechanism,
  session-miss targets, 61b window/oracle.
- DIGEST / N11f-g — double-copy exists, child callback clean, 2nd copy is host-side.
