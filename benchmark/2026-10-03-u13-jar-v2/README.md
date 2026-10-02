# U13 JAR v2 = 6790d500 + a "telephony.registry" present-but-off binder (one class): x's next wall

#90, JAR, offline. Nothing was deployed to a board.

`2026-10-03-termux-and-u12-jar-check` found that U12's telephony fixes moved x's first fatal, from "object graph is not
defined" to a new wall:
`NullPointerException: … ITelephonyRegistry.listenWithEventList(…)`.
- Stack: `TelephonyRegistryManager.listenFromListener` ← `TelephonyManager.listen` ← `com.twitter.util.telephony.a.run`.
- It comes right after `[OHServiceManager] getService("telephony.registry") → null` (U12 window 4, 61b).

This round closes that wall the way U12 closed "phone" and "isub".

## Fix

New file `adapter.activity.TelephonyRegistryStub`. It is **one class**: no inner classes, no new handler.
- `install()` calls the existing `TelephonyFetcher.seedSafeBinder("telephony.registry",
  "com.android.internal.telephony.ITelephonyRegistry", "WlTelephonyRegistryStub")` by reflection (the method is private
  static).
- This is the same seeding `TelephonyFetcher.install()` already does for `phone` (`WlTelephonyStub`) and `isub`
  (`WlSubStub`):
  - a Binder whose `queryLocalInterface` returns a Proxy of the interface;
  - `ZeroHandler` answers every call with the zero value of its return type, so the `listen*` / `add*Listener` voids are
    no-ops;
  - the Binder is put into ServiceManager's cache.
- So `ITelephonyRegistry.Stub.asInterface(ServiceManager.getService("telephony.registry"))` is non-null.
- `ITelephonyRegistry` is in the deployed `framework.jar` (dexdump).

**Needle.** In `B7BindFixes`, right after `TelephonyServiceNames.install()`, which follows
`SystemServiceFetcherStubs.install()` where TelephonyFetcher runs: `TelephonyRegistryStub.install()`. That is at bind,
before any app code can build a `TelephonyRegistryManager`. Its `sRegistry` static is filled at construction, so the
seed must come first.

**Marker:** `[B8-FETCH] telephony.registry present-but-off binder seeded (WlTelephonyRegistryStub)`.

## Artifact and gates

| | |
|---|---|
| jar | `oh-adapter-runtime-u13-v2.jar` = `506abe23dd08f12eadb9ee1a0a111b42816cda0bbf83437a8712068b4839bac0` |
| base | U13 JAR `6790d500` (U12 r2 0482c9b1 + ThemeProbe + webkit glue) |
| deterministic | built twice, byte-identical (`build_v2.py`, pinned toolchain of `2026-10-02-u12-jar-plan`) |
| `deployed_class_diff --deployed` 5ae3dd29 (the boards' runtime jar) | **0 dropped, 0 reshaped**; 20 added: U12 r1/r2 (OwnProviderLocal, WlSettings*, ProviderAuthorityRefs, TelephonyServiceNames, GcmDefaultNonce*), U13 (ThemeProbe*, WebkitSupportGlue*, SupportLibReflectionUtil*), and `TelephonyRegistryStub` (`gates/class-diff-vs-5ae3dd29.txt`) |
| vs `6790d500` | 0 dropped, 0 reshaped, +1 `TelephonyRegistryStub` (`gates/class-diff-vs-6790d500.txt`) |
| deploy | runtime PathClassLoader jar: single-file replacement, no boot-image rebake |
| persisted | `$WORKSPACES/westlake-inputs/generations/u13-jar-v2/` (`SHA256SUMS`) |

## Who it touches (`registry_scan.py` → `registry-scan.csv`)

| runs | ask for `telephony.registry` | die on the null ITelephonyRegistry |
|---|---|---|
| U10.1T8 signing population (133) | 0 | 0 |
| U12 windows 1–4 (171) | 1 (x) | 1 (x) |

U10.1T8 has no hits because x died earlier there, at the object graph. The stub only changes processes that ask for
the service. The blast radius on the current evidence is x.

## Prediction

| key | prediction |
|---|---|
| x | **The first fatal moves again (high):** `listenWithEventList` becomes a no-op. The next wall is unknown, and x is large (Twitter: network, Compose, many services), so lit is low. |
| every other key | 0: none asks for the service in 304 runs |

## Also for the U13 window (outer loop scheduling)

notepad, clipboardeditor, packlist and moodcairns never ran in U12 windows 1–4. v2 contains all of U12 r2, so one
single-key pass each on a v2 board tests U12's four untested predictions (≈ 12 min):
- notepad: R1 ProviderAuthorityRefs;
- clipboardeditor: R2 + S1 telephony;
- packlist: S2 Predicate on BCP;
- moodcairns: R3 GcmDefaultNonce.

## Files

- `src/adapter/activity/TelephonyRegistryStub.java`, `build_v2.py`.
- `gates/class-diff-vs-5ae3dd29.txt`, `gates/class-diff-vs-6790d500.txt`.
- `registry_scan.py` → `registry-scan.csv`, `registry-scan.txt`.
- `results.json`.
