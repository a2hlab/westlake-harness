# Restore the second v2 spare

A 319-file SHA match was insufficient: ten root-owned baseline source directories retained mode 750 on 5ea. Ordinary children failed to load the adapter with errno 13 and exited 123. The exact 31-ancestor comparison against healthy 5cd isolated ten mode differences, with matching UID/GID/labels. Changing only those ten source modes to 755 restored both controls.

The reviewed BASE5 transaction first replaced five boot controls, preserving the old Boat archive and all runtime sources. One authorized reboot produced autonomous READY/56 and Permissive. The first hash sample ran before READY and is deliberately retained as incomplete boot-time evidence; the next sample after READY matched all 319 files.

The initial smoke and its white screenshots are failures. The same smoke after the mode correction passed the fingerprints, two controls, GCM marker and child-view checks. Outer independently inspected both t20 screenshots: HelloWorld controls and the ZigZag start scene are visible. This is spare baseline recovery, not Boat/v2 acceptance.

Sources: `benchmark/2026-10-12-v1-seal-execution/restore-v6-base-placement/apply.sh` SHA 0ddcad1e; exact boot/stage/mode/archive-preservation delta in `delta.patch`; independent review in `independent-review-original.json`; real raw transaction receipts in `execution/`, `reboot/`, `dir-repair/`. Unknown or failed records were not overwritten.

The old six-object Boat archive remains intact. Its obsolete adc runtime is not active. The primary 61b was not modified.
