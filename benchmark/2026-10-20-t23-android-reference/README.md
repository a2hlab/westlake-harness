# Android reference baseline (read only)

The reference device has the exact same installed Toutiao APK as the current OH experiment: SHA-256 `a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395`, version 13.9.0 / code 13900 / targetSdk 30 / arm64-v8a. Its OS is Android 16, API 36, userdebug, model uis7885_2h10_native. This gives an application-input match, not an equivalent OS, GPU, codec or player execution path.

The main app process was absent (`pidof` rc 1); a later exact-name process-list read found only PID 3263 `com.ss.android.article.news:push`. Foreground is QuickstepLauncher. No app launch or UI input was performed. Existing bounded logcat was read privately and is not a playback observation. Boot reads matched.

All 17 commands used the explicit reference serial and a 10-second host timeout. Shell UID was 2000, with no elevation attempted. The actual media/player/audio/SurfaceFlinger services were listed. Perfetto v49 query returned rc 0, advertised frame timeline and Linux ftrace sources, and showed zero existing sessions. Atrace advertised gfx/view/audio/video/sched. Perfetto help returned rc 1 with its usage on stderr; this does not prove trace capture permission.

`trace-plan.json` is an unexecuted outer command package: select the same clip normally, bind a fresh process, then collect one self-expiring 20-second gfx/view/audio/video/sched trace. The asynchronous start keeps each host command within 10 seconds; a local wait is separate. Use unique output paths, retain original rc/streams and failures, and never interpret a timeout as success or retry an unknown start blindly. Do not infer decoded moving content from timestamps, audio, trace events or controls alone.

`source-index.json` pins private raw argv/stdout/stderr/rc. Raw package details and general logcat remain private. No device setup, installation, force-stop, data clearing, logging reset, network/account mutation or trace start occurred. Main source code was not edited.

## Later authorized playback observation

The earlier read-only baseline and unexecuted plan are preserved as their original stages. A subsequent, explicitly authorized Android lock window executed normal UI and one bounded trace; see `window/README.md` and its distinct results. No old baseline field was rewritten to imply it had launched the app.
