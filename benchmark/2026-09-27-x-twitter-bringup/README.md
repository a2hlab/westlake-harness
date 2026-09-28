# X/Twitter (com.twitter.android 12.17.0, Java/Kotlin) bring-up on 5ea34a45 — #48 horizontal (2026-09-27)

Goal: light X to first usable screen. Old record: past getRunningAppProcesses+provider install, stuck at
Firebase service-level `<meta-data>` (fix "verifying"). Re-test on the current runtime.

## Result: launch PASS, Firebase blocker RESOLVED (stale record), NEW blocker = telephony.registry NPE → parked
| Item | Outcome |
|------|---------|
| Stage + launch | PASS — probe_source_app (framework-2 = a2hlab-framework-cab462ff) staged runtime `a2hlab-source-27246e1d`, spawned child 15627 |
| Firebase meta-data | RESOLVED — `[SOURCE-PM] getServiceInfo HIT com.google.firebase.components.ComponentDiscoveryService flags=0x80 meta=16` (service-level meta-data returned; old blocker is past) |
| First usable screen | NOT reached — exit(1) during ActivityThread init |

## New blocker (the actual current wall)
`java.lang.NullPointerException: Attempt to invoke ... 'void com.android.internal.telephony.ITelephonyRegistry.listenWithEventList(...)' on a null object reference`
- at `com.twitter.util.telephony.a.run` → Twitter registers a PhoneStateListener; `TelephonyManager.listen`/`listenWithEventList`
  resolves `ITelephonyRegistry` (ServiceManager "telephony.registry") which is **null** in the westlake runtime → NPE →
  `launchActivityThread returned unexpectedly → child_main:_exit(1)`.
- westlake has NO ITelephonyRegistry handling (grep telephony.registry/ITelephonyRegistry/listenWithEventList = empty).
  Stub points exist: `framework/core/java/LocalServiceBinders.java`, `OHServiceManager.java`,
  `framework/mainline-stubs/java/android/telephony/TelephonyFrameworkInitializer.java`.

## Fix direction (framework change, NOT pure config → parked)
Add a no-op `ITelephonyRegistry` stub binder registered under "telephony.registry" (or via TelephonyFrameworkInitializer's
service manager) whose `listenWithEventList`/`listen` no-op and return cleanly, so TelephonyManager.listen() gets a non-null
registry. Requires editing the westlake framework Java + rebuilding out/framework-java + re-staging the framework — M effort,
touches the shared verify tree. Route to claude-3 / a framework-fix pass. Same class as McDonald's "phone|inert|M" gap.

## Board state
5ea34a45, framework-2 base ready. X runtime `a2hlab-source-27246e1d` staged (child exited). 61b06572 untouched (Toutiao demo).
