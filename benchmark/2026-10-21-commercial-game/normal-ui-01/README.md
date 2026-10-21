# Normal desktop launch observation

Previously, installation was verified but agent-observed launch behavior was missing. An ordinary desktop icon tap now shows a white screen at the 2-second capture and the desktop by the 20-second capture. This is a failed launch attempt, not a game frame or playability result.

The unmodified installed APK was opened via its visible Genshin Impact icon. PID 10029 (UID 20011077) exists at t2 and is absent at t10/t20. The completed filtered log records an uncaught `UnityPlayer.nativeRestartActivityIndicator()` UnsatisfiedLinkError and process exit code 1. Earlier, `libMHYComboCrypto.so` fails relocation for `__errno`; the causal relationship is not yet established.

No installer, runtime, APK or app data was replaced. Power was restored to SLEEP / timeout 30000 / override 10000 and the ordinary UI lock was released. G13/G14 historical receipts remain unchanged. This observation did not execute their automation.

## Evidence

- [Visible desktop icon](last.jpeg)
- [White screen](genshin/t2.jpeg)
- [Returned desktop](genshin/t20.jpeg)
- [Exact exit-log excerpts](exit-log-excerpt.txt), [original hash and ranges](log-provenance.json)
- [Actual record](genshin/record.json), [counted facts](facts.txt), [result](results.json)

Private raw files remain under `$HOME/.local/share/westlake/commercial-game-20261021/normal-ui-01/`. Initial unfiltered collection timed out; that attempt is not claimed as successful. The filtered log completed with rc=0. No runtime fingerprint or t5 sample was taken here; missing facts remain unknown.
