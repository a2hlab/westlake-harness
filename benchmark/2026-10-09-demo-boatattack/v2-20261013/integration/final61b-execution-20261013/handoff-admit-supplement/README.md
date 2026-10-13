# Offline admit supplement; not board authorization

The corrected runner remains4d6598b4bd24c0c4f9cc273a4a2e0ce628fbfe089b2c476276e97966950612bf. The twelve-file parent freeze8324f7bf24169a6b526a29ea4e0e8d301e966b577014136e93041295a7149b6e is unchanged.

The original raw old-preview file was overwritten during the pre-freeze refresh. No historical raw copy was found in local handoff or its main counterpart. `old-preview.replayed.json` is a new exact-byte replay of rejected runnerdc3526, explicitly REPLAY_NOT_ORIGINAL_RAW. The rejected source is retained as `.py.txt`, not an executable entry. Its preview returns rc0 because preview never calls admit. It must not be used on the board.

`check_admit.py` calls the original unchanged admit body, using actual provider-plan/capture serial, UID and originboot in an explicitly synthetic local fixture. The corrected runner accepts those real identity parameters; wrong board and wrong runner pin reject; the olddc3526 runner rejects the same real32-character serial. Subprocess/Popen and the execution function are blocked; observed calls are zero. The fixed clock only replays the local60-second synthetic authorization; it is not a freshness proof for a real board window.

The actual game plan still has execution_enabled=false and boot_id=null in the parent delivery. Root must derive its newboot and authorization from the live candidate window. The synthetic fixture here is not an enabled game request, valid device authority, successful geometry test or game acceptance. The inherited admit function does not itself reject a synthetic marker, so these fixture files must never be passed to the execution CLI.

Replay locally:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 check_admit.py
```
