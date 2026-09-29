# OH 6.1 BMS route deployment on three boards

The initial plan was wrong: the R155 activation script assumes a PR03 base already exists. It is not a fresh-board deployment recipe. The accepted local reproduction suite supplies that base, restores BMS host libraries, reboots, and verifies the Android APK with visible pixels and a touch callback.

The scope was narrowed by the user to **HelloWorld + ZigZag on all three boards**. Capybara and BoatAttack received read-only checks before this change; neither was installed or launched by this task. No flashing or source build was performed. Deployment used the explicitly requested local-Mac reproduction skill and its fixed DevEco hdc; supplementary board readbacks used the VM hdc wrapper.

## Acceptance evidence

| Board | HelloWorld restore | Before/after images | ZigZag |
|---|---|---|---|
| 5ea34a45 | PASS, parent/child 4202/4708 | [Before](evidence/5ea34a45/helloworld/before.jpeg), [red after tap](evidence/5ea34a45/helloworld/after.jpeg) | PASS, score 0 → 1 |
| 61b06572 | PASS | [Before](evidence/61b06572/helloworld/before.jpeg), [red after tap](evidence/61b06572/helloworld/after.jpeg) | PASS, score 0 → 1 |
| 5cd1e3dd | PASS | [Before](evidence/5cd1e3dd/helloworld/before.jpeg), [red after tap](evidence/5cd1e3dd/helloworld/after.jpeg) | PASS, score 0 → 1 |

All three exact APKs registered as `bundleType=10`. Each restore receipt validates a stable child process, visible first-frame pixels, a CHANGE COLOR callback on the Android main Looper, changed decoded pixels, and no fatal/lifecycle markers. cx-t0 inspected all six screenshots: black Hello World text becomes red and the view logs `Color -> RED`. Independent outer review remains pending. 61b was subsequently synchronized to the Mac epoch with a measured -1 second skew; see [clock record](evidence/61b06572/clock-sync.json). These images demonstrate the offline UI only: board wall clocks reset after reboot (clock_skew); they do not establish TLS/network correctness.

The additional [foundation identity records](evidence/) compare seven patched library hashes through `/proc/<foundation pid>/root`, rather than merely the shell's filesystem. All 21 comparisons match. Each process maps five of these libraries: bms, apk_installer, appms, appspawn_client, abilityms. The records do **not** claim libinstalls or the HAP domain wrapper were mapped. Complete maps and `bm dump -n com.example.helloworld` are retained per board.

## Reproduction and change boundary

Source: local `00.Workspace-games-ad1ab0a7`, cloned with `cp -Rc` into `workspaces/westlake-bms-suite`, including ignored APK/payload/state. Source files were not edited. Seven shell scripts only gained exact serial whitelist alternatives; see [patch](serial-whitelist.patch) and [before/after hashes](script-changes.json). Existing board alternatives remain supported. `resign.sh` has no serial whitelist and was left unchanged. No signing fallback was needed.

The suite entry has no `check` command (actual exit 2 on all boards). Individual HelloWorld checks reported the missing APK; they passed all local payload checks. The three `reproduce-helloworld/scripts/reproduce.sh restore <serial>` runs were then started concurrently. Both `board_note.sh` locks and the reproduction scripts' per-device channel locks were held.

The initial ZigZag check failed because the cloned `current` pointer names an absolute path in `games-c-5ea1`, outside the clone's accepted candidate root. The wrapper driver SHA also needed to reflect the authorized whitelist edit. These two relocation changes were requested explicitly because #22 requires every other byte to remain unchanged. The user explicitly authorized both changes; the [exact patch](proposed-zigzag-relocation.patch) was applied, and all three ZigZag checks then passed. The [13 candidate hashes](zigzag-candidate-identity.json) already match the accepted manifest exactly. No candidate/APK bytes or acceptance gates were changed.

## Recovery and validation

The original restore recipe retains an existing PR03 backing at `/data/pr03-74e6-portable.pre-restore-20260928T094221Z-<board-prefix>`. This is a backing recovery point, **not a full stock-system rollback**: the recipe replaces host libraries and init configuration. HelloWorld restore left PR03 active; subsequent ZigZag quick deployed the accepted R155 candidate as trial overlays. Reboot persistence of that candidate was not tested or claimed. Raw logs and full deployment evidence remain under the clone's `var/state` and `var/evidence` paths recorded by each receipt.

Validation: seven modified shell scripts pass `bash -n`; known-answer repository tests: 69 run, 67 passed, 2 skipped. No new binaries or APKs are committed. R2 is **partially**: HelloWorld has machine and screenshot evidence on 3/3 boards; ZigZag also passed on 3/3 boards, but independent visual acceptance and long-duration stability are not claimed. No agent-spec lifecycle verdict is claimed for the new operational #22 entry (it supplies no spec selector).

## ZigZag completion and observed limits

All three final independent receipts report PASS, five delivered touches, TopScore 0 → 1, four distinct decoded frames, and stable PIDs at t+3/9/15. Each run also revalidated HelloWorld on the candidate generation. cx-t0 read the t+9 and after-taps screenshots from each board: actual game geometry, ball, score screen, and playable scene are visible.

| Board | Final receipt | Game image | After touches |
|---|---|---|---|
| 5ea34a45 | [receipt](evidence/5ea34a45/zigzag/receipt.env) | [t+9](evidence/5ea34a45/zigzag/screen-t9.jpeg) | [after](evidence/5ea34a45/zigzag/screen-after-taps.jpeg) |
| 61b06572 | [receipt](evidence/61b06572/zigzag/receipt.env) | [t+9](evidence/61b06572/zigzag/screen-t9.jpeg) | [after](evidence/61b06572/zigzag/screen-after-taps.jpeg) |
| 5cd1e3dd | [receipt](evidence/5cd1e3dd/zigzag/receipt.env) | [t+9](evidence/5cd1e3dd/zigzag/screen-t9.jpeg) | [after](evidence/5cd1e3dd/zigzag/screen-after-taps.jpeg) |

The first simultaneous run exposed an upstream artifact collision: the wrapper uses only second-resolution UTC time and mode for its output directory. The 61b summary pointed to 5cd evidence. Those attempts are preserved under `zigzag-initial` but are not the final receipts. Starting the next three runs more than two seconds apart retained concurrent execution and produced three distinct receipt paths. Each final receipt board matches its raw envstamp board. No script logic was modified to solve this.

Each final run recorded one native fault classified by the original oracle as recoverable `ART_IMPLICIT_NULLCHECK_SIGSEGV8`, with `NO_TERMINATING_NATIVE_FATAL`. This is not a claim of zero fault logs. Later handoff inspection found the accepted PIDs still alive on 5ea/5cd, but 61b had no ZigZag process and displayed a [blank surface](evidence/61b06572/post-quick-handoff.jpeg). The cause of that later exit is unverified; the earlier bounded acceptance remains documented separately. Raw post-run logs are retained. The user subsequently confirmed BMS usable and requested the #23 batch next.

Four positive whitelist dry-runs and two negative controls (malformed 61b serial and unknown serial) behaved as expected without device writes. The original source tree remained unchanged. Local commits only; no push. The three board locks carried over to explicitly assigned #23. Baseline machine results are preserved in [baseline-results.json](baseline-results.json).
