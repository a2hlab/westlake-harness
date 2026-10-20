# T34 guarded UI entry

W02 lacked a verified feed before subsequent content actions. This helper does not diagnose the child exit or make a feed decision. It adapts the T33 guarded Board pattern and reuses pinned BMS desktop-launch/capture, with fresh 61b session identity and a bounded capture schedule.

Only launch/capture/tap/back/power are exposed. There are no HAP, runtime, reboot, lock-create or unlock actions. Before every transport command, exact holder and boot are checked under a monotonic budget initialized from the real holder start. Ordinary actions expire at1200s; explicit recovery launch/capture/power expires at1800s. The UI dispatch also verifies boot in its remote shell. Lock checking is a pre-command check, not a remote lock held atomically through input.

Every uitest, including layout dumps, runs the original operation followed by override86400000 and readback in one shell. Individual UI/power/readback rc values survive in the receipt. Unknown transport outcomes do not trigger retries. Fresh desktop selection is delegated to BMS, not a stored icon center. Images need human review before a new content action. Process survival and audible/visual success remain unknown unless separately evidenced.

Eight offline tests passed using the real BMS raw marker parser with mocked transport, plus local bash control-flow testing. No device command was issued. These tests do not prove actual focus, UI appearance, or device transaction completion. Commands and limits are in COMMANDS.md; original dependencies are pinned in source-pins.json. Frozen T34 executor/transport/data and T33 sources are unchanged.
