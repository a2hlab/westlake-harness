# Demo path PROVEN — foreground icon tap launches Toutiao on screen, no permission grant (cc-t3 #91)

The outer's reframe was right: at demo time the audience **taps the 今日头条 icon on the desktop**, which is a
**foreground** launch and needs **no** background-start permission. On 5ea (original imehost, skip-push overlay), a real
foreground tap brought the host window up and the feed on screen, three times, with watchdog self-heal — no re-sign, no
`atm` grant, no `/system` change.

## Why the earlier `aa start` failed and the tap works
- `aa start -b org.westlake.imehost` from an hdc shell = **background** caller → AMS `canStartAbilityFromBackground` →
  10107101. (This is what the re-sign/grant work was chasing — the wrong lever for the demo.)
- A **foreground tap on the desktop icon** (SceneBoard is the foreground caller) launches imehost's EntryAbility directly —
  **allowed**, no permission needed.

## Tap pitfalls found (so the automation is repeatable)
- The icon node `今日头条` is a non-clickable `Text` label `[126,255][253,287]`; its clickable parent is the
  `RelativeContainer` `[53,98][326,371]`. Tapping the **text label** did not launch.
- `uinput -T -d x y -u x y` registered as a **long-press** → opened the icon context menu (`AppIconLongPressGestureEvent`).
- **What works**: a short `uitest uiInput click` on the **icon image** (upper half of the container, ~`(189,176)`) →
  `WMSLife session start bundleName:org.westlake.imehost Id:71` → `imehost0` fronted (ZOrd 101). The board has no `python3`,
  so icon bounds are parsed off-board from `uitest dumpLayout` JSON.

## Three cold starts + self-heal (facts-5ea-tap.txt; screenshots are ground truth)
| cold start | method | result | snapshot |
|---|---|---|---|
| 1 | foreground tap on icon | imehost0 fronted (pid 21930) → state READY | `5ea-cold1-final.png` (1.29 MB, content-rich) |
| 2 | kill child → watchdog self-heals | child 22753→23838 → READY, **host 21930 unchanged** | `5ea-cold2.png` (239 KB) |
| 3 | kill child → watchdog self-heals | child 23838→24675 → READY, **host 21930 unchanged** | `5ea-cold3.png` (734 KB) |

- **Self-heal PROVEN**: with the host (imehost0) alive, the watchdog restarts **only** the Toutiao child; the host pid
  stayed 21930 across both kills; appspawn-x was never touched (RUNBOOK #12 respected).
- **On-screen**: each cold start reached imehost0-fronted + state READY + a content-rich snapshot. Per "截图是地面真相",
  the outer reads the three PNGs to confirm feed headlines; the window/state/process evidence is objective.
- **ICU walls**: cleared (the child runs; no `libtttext_lite ICUWrapper` SIGSEGV).

## Net
The Toutiao demo path on the unified base is established via the **foreground icon tap** — no re-sign, no grant, no
`/system` change, fully reversible (rollback OK). The re-sign/grant investigation (`host-launch-grant.md`) was the wrong
lever for the *demo* (it matters only for a *shell/background* launch). Screenshots: `5ea-cold1-final.png`, `5ea-cold2.png`,
`5ea-cold3.png` (force-added as evidence).
