# location-answers probe

Records Westlake's location answers (ADR-0009), one line each (`[WL-LOC-PROBE] <name> = <value>`), so one
launch says what an app sees:

- whether LocationManager exists, the device's location switch, the providers and whether each is enabled;
- `checkSelfPermission` for fine location next to the answer of a runtime permission request;
- the last known location on the fused provider;
- a one-shot `getCurrentLocation` on the fused provider, and how long its answer took;
- a listener on the fused provider for 60 seconds: the number of fixes, the first three described;
- `verdict = PASS_FIXES` when the listener got a fix, `NO_FIXES` otherwise.

Coordinates are never logged: only whether a fix came, its provider, its accuracy and its age.

    ./build.sh      # out/location-answers-probe.apk (pure Java; D8 from the cmdline-tools R8 jar)

## First run (framework 257, 2026-11-14)

OH's location library bound; the board's location switch off. Location disabled, four providers
(passive, network, fused, gps) all disabled; `checkSelfPermission` granted but the permission request
answered denied (the host application does not request OH's location permission); no last known
location, `getCurrentLocation` null at once, no listener fixes: `NO_FIXES`.
