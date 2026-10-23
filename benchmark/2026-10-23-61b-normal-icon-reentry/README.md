# 61b ordinary desktop icon launch (T56, 2026-10-23)

- **Identity**: fresh, equal to T55. Boot 350d374d, host HAP b18978b8, cfg 7b9f2c0e → ROOT `icon-manual-20261021-r3`,
  guardian 4005 waiting.
- **UI path** (all ordinary UI): lock screen → swipe up → Home → page 1 → exact icon `org.westlake.imehost.EntryAbility`
  (189,234; eye-read 今日头条) → **one** automated click at 10:22.
- **First launch failed: white screen.** `first-t30.jpeg` and `first-t120.jpeg` both show a blank light-grey page.
- **Event chain** for the current boot: BOOTSTRAP (child 6243) → UI_UNVERIFIED ×3 → +40 s `process_exit
  first_read_exited` → `AWAITING_REENTRY`. The child never reached READY.
- **Window state**: WMS shows the host window imehost0 full screen with no Toutiao window. The bounded hilog is
  used only to mark the child exit at 10:22:54 (natural exit; not investigated).
- **Reopen**: not executed. The stop rule applies because the first launch was white.
- **Restore**: `power-shell timeout -r` read back `Timeout=30000ms`. The before-image line `OverrideTimeout=10000ms` is
  no longer shown, so the override restore is unknown. Lock held 233 s and released.
- **Confounder**: the leftover T55 read-only hash shell was still running at click time.
- **Not claimed**: lifecycle pass, seal, cold power cycle, root cause.
