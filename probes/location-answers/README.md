# location-answers probe

Records Westlake's location answers (ADR-0009), one line each (`[WL-LOC-PROBE] <name> = <value>`), so one
launch says what an app sees:

- whether LocationManager exists, the device's location switch, the providers and whether each is enabled;
- `checkSelfPermission` for fine location next to the answer of a runtime permission request;
- the last known location on the fused provider;
- a one-shot `getCurrentLocation` on the fused provider, and how long its answer took;
- a listener on the gps provider (GNSS) for 180 seconds: the number of fixes, the first three described;
- `verdict = PASS_FIXES` when the listener got a fix, `NO_FIXES` otherwise.

Coordinates are never logged: only whether a fix came, its provider, its accuracy and its age.

    ./build.sh      # out/location-answers-probe.apk (pure Java; D8 from the cmdline-tools R8 jar)

## First run (framework 257, 2026-11-14)

OH's location library bound; the board's location switch off. Location disabled, four providers
(passive, network, fused, gps) all disabled; `checkSelfPermission` granted but the permission request
answered denied (the host application does not request OH's location permission); no last known
location, `getCurrentLocation` null at once, no listener fixes: `NO_FIXES`.

## With the host granted location (framework 258, 2026-11-14)

The host application requesting and granted OH's location permissions, the board's location switch on:
location on, four providers enabled, the permission request answered granted. getCurrentLocation on fused
(OH's low-power scene) answered null at 30 s; OH filed it as passive, as the board has no network location
service. The gps listener (OH's GNSS scene) got no fix in 180 s: OH's GNSS ability started it, but the board's
vendor GNSS manager could not reach its engine (`gnss_engine_ctrl failed` in hilog), so a HAP gets no fix
either. Delivering a fix still needs a device whose GNSS works.
