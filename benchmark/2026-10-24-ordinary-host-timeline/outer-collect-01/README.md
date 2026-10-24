# Host4958 bounded log interpretation

The original stdout SHA is `9e41bc754e240efca423cf69af0fafe77a688906a3e09a72a4339074d572cbd3` (83,783bytes). Outer collected it; this task only parsed local files. Both guards show boot `61aa5791-fd69-4bbb-a7b5-333b5d913c81`, PID4958/birth10879, PPID379, cmdline `org.westlake.imehost`. Uptime is 66194.66–66194.77s; identity is stable.

Observed log timestamps span **2026-10-23T17:00:02.342+08:00 to 2026-10-24T11:08:37.479+08:00**, including the11:06 click minute. This is an observed range, not proof of uninterrupted complete logging.

- Original L225–227: onForeground call11:06:10.579, WL_IME_HOST foreground10.580, callback end10.580. L229/L248: stage-event1 at10.582 and2 at11.546.
- L299: background11:06:40.912. L365–383: another onForeground/foreground11:06:43.192, stage1 at43.194, stage2 at43.219. Both transitions must be retained; this capture alone does not assign each to a particular desktop action.
- The supplied child22035 birth6535369 at100Hz means boot-relative65353.69s. The reported approximately+44s creation is a separate outer observation, not a host callback delay measured here. Exact click epoch/clock alignment is absent from this input; no precise click-to-child or click-to-callback latency is derived.

`excerpts.txt` retains line references and sanitized ordinary event fields. Callback presence does not prove a frame/feed or explain the waiting period. No device command, extra collection, control-source inspection or oldT122 analysis was performed.
