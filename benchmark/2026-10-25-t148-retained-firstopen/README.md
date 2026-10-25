# T148 — one software-reboot first-open

**Observed success, candidate retained.** One normal software reboot and one desktop icon click produced a real feed; one swipe produced changed content, independently viewed by the outer reviewer. This does not establish physical power-cycle behavior or AV acceptance.

The click returned at 2026-10-25 09:15:57.477010 +08:00. Capture intervals relative to that return were 6.444–6.816s (white), 31.537–32.100s (white), and 61.373–61.829s (feed). The changed-content frame was captured at 83.566–84.002s. Labels s5/s30/s60 are scheduling targets, not exact capture times. No s90/s120 or additional icon click was needed.

New boot `2c299f4e-7463-417c-8f12-16a36b4fe90c`; final host4846/b8892, parent4970/b9059, main child6849/b10692. Actual child mapping and final backing object match candidate3291, dev66352/inode590080. Power returned to base30000/override10000; final held query at 09:17:36.961–36.966 +08:00 returned rc1 with empty stdout/stderr. Total window 194.160s. No deployment or rollback occurred.

`observe.py` reuses reviewed T141 UI/lock/binding/readiness methods (source SHA be8336df180ee124d921a11d3a3f66cf5943c06dd303d2cf798a37cc85ad6e4d), without calling its deployment/rollback workflow. The first local guard failure occurred before any device call and is preserved separately. Offline checks are adapter checks, not device evidence. The raw inherited runtime_result=pending_review field remains unmodified; actual status and external image reviews are reported separately.

`facts.txt` counts actual files and command receipts. `results.json` gives exact capture times. `evidence/` holds four key original images, their reviews, actual mapping and final command receipts. The complete private runs and console logs are backed up at `$HOME/.local/share/westlake/t148-retained-firstopen-20261025/collection-01`; `raw-index.json` pins every file. No extra device action was performed for archiving.
