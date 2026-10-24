# T123 frozen launch package, revision 3

Offline preparation only. Execute only after outer acceptance. This revision preserves the prior recorder-fix and both old run directories. Its only UI addition is the contract's conditional failure Home.

`start.py --manifest-sha <accepted-manifest-SHA> --execute` verifies every package file plus the Python/HDC/board-note/append dependencies, creates a unique private directory, copies byte-identical payload files, and writes context before T0. It then runs P0 and the full owner in the same Python PID through `runpy`; no generated scripts or process handoffs occur during the window. Without `--execute`, it only verifies local hashes. `WORKSPACES`/the pinned `lab_paths.py` resolve main. Existing run directories are never accepted as targets.

P0 is the already-verified held/boot/UID/birth/no-child/21-control-SHA/power preimage sequence. Control files are hashed only. All command argv, begin/end wall and monotonic times, stdout/stderr and rc/timeout are exclusive receipts. `owner.stdout`/`owner.stderr` persist live notices. `clock.json` establishes T0 immediately before the first formal held check; 120/180/360/480 deadlines never reset.

Notices are printed immediately and retained:

- `RUN_READY`: absolute private run directory, owner PID, accepted manifest SHA.
- Initial image receipt: path/SHA/T0/budgets/lock tuple/power preimage. Inner must view the image and corresponding layout before publishing `inner-unlock-review.json`; no script guesses that a screen is safe to unlock.
- `FINAL_IMAGE_READY`: fixed final image path/SHA and review seconds remaining. Only a matching timely `outer-review.json` allows Home/click.
- `IMAGE_READY`: each actual sample image path/SHA/elapsed time. A matching `feed-review.json` stops further UI and preserves the visible content.

See `review-schema.json` for the exact local review fields. Publishers must write complete JSON atomically. The supplied `publish_once` uses a complete fsynced temporary file and atomic create-if-absent hard link, rather than an overwriting rename. Same receipt names are refused. Never add code in the running directory during a window.

Failure Home is attempted at most once, only after valid desktop/host-white approval, an attempted UI change, no valid feed/usable review, unchanged host/appspawn boot/birth/UID, owned lock, and before T+360. A newly created article child is permitted by this identity check; it is never killed. Missing/invalid initial review, credentials, identity ambiguity, lost lock, or the recovery reserve prohibit this Home. Home errors do not prevent power restoration and owned-lock release. Final power readback must equal both captured fields.

Package verification and offline entry tests are recorded in the parent `package-v3-tests` directory. No third device window has been opened. A changed candidate requires a new reviewed manifest; the command's manifest pin is in the parent `launch-package-v3-ready.json`.

Revision 3 also separates the unlocked layout command receipt label from the received layout filename. After s120 publication it waits at most 15 seconds for matching feed review, capped at original T0+340, and rechecks feed immediately before failure Home. This preserves the original Home/recovery budgets.
