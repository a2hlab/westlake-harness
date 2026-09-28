# OH 6.1 BMS route deployment on three boards

The initial plan was wrong: the R155 activation script assumes a PR03 base already exists. It is not a fresh-board deployment recipe. The accepted local reproduction suite supplies that base, restores BMS host libraries, reboots, and verifies the Android APK with visible pixels and a touch callback.

The scope was narrowed by the user to **HelloWorld + ZigZag on all three boards**. Capybara and BoatAttack received read-only checks before this change; neither was installed or launched by this task. No flashing or source build was performed. Deployment used the explicitly requested local-Mac reproduction skill and its fixed DevEco hdc; supplementary board readbacks used the VM hdc wrapper.

## Current evidence

| Board | HelloWorld restore | Before/after images | ZigZag |
|---|---|---|---|
| 5ea34a45 | PASS, parent/child 4202/4708 | [Before](evidence/5ea34a45/helloworld/before.jpeg), [red after tap](evidence/5ea34a45/helloworld/after.jpeg) | Pending clone relocation |
| 61b06572 | PASS | [Before](evidence/61b06572/helloworld/before.jpeg), [red after tap](evidence/61b06572/helloworld/after.jpeg) | Pending clone relocation |
| 5cd1e3dd | PASS | [Before](evidence/5cd1e3dd/helloworld/before.jpeg), [red after tap](evidence/5cd1e3dd/helloworld/after.jpeg) | Pending clone relocation |

All three exact APKs registered as `bundleType=10`. Each restore receipt validates a stable child process, visible first-frame pixels, a CHANGE COLOR callback on the Android main Looper, changed decoded pixels, and no fatal/lifecycle markers. cx-t0 inspected all six screenshots: black Hello World text becomes red and the view logs `Color -> RED`. Independent outer review remains pending. These images demonstrate the offline UI only: board wall clocks reset after reboot (clock_skew); they do not establish TLS/network correctness.

The additional [foundation identity records](evidence/) compare seven patched library hashes through `/proc/<foundation pid>/root`, rather than merely the shell's filesystem. All 21 comparisons match. Each process maps five of these libraries: bms, apk_installer, appms, appspawn_client, abilityms. The records do **not** claim libinstalls or the HAP domain wrapper were mapped. Complete maps and `bm dump -n com.example.helloworld` are retained per board.

## Reproduction and change boundary

Source: local `00.Workspace-games-ad1ab0a7`, cloned with `cp -Rc` into `workspaces/westlake-bms-suite`, including ignored APK/payload/state. Source files were not edited. Seven shell scripts only gained exact serial whitelist alternatives; see [patch](serial-whitelist.patch) and [before/after hashes](script-changes.json). Existing board alternatives remain supported. `resign.sh` has no serial whitelist and was left unchanged. No signing fallback was needed.

The suite entry has no `check` command (actual exit 2 on all boards). Individual HelloWorld checks reported the missing APK; they passed all local payload checks. The three `reproduce-helloworld/scripts/reproduce.sh restore <serial>` runs were then started concurrently. Both `board_note.sh` locks and the reproduction scripts' per-device channel locks were held.

ZigZag check currently fails because the cloned `current` pointer names an absolute path in `games-c-5ea1`, outside the clone's accepted candidate root. A second known gate will require the wrapper's driver SHA to reflect the authorized whitelist edit. These two relocation changes were requested explicitly because #22 requires every other byte to remain unchanged. The [13 candidate hashes](zigzag-candidate-identity.json) already match the accepted manifest exactly. No candidate/APK change or gate relaxation is proposed.

## Recovery and validation

The original restore recipe retains an existing PR03 backing at `/data/pr03-74e6-portable.pre-restore-20260928T094221Z-<board-prefix>`. This is a backing recovery point, **not a full stock-system rollback**: the recipe replaces host libraries and init configuration. Successful restore leaves the accepted PR03 generation active and HelloWorld in front. Raw logs and full deployment evidence remain under the clone's `var/state` and `var/evidence` paths recorded by each receipt.

Validation: seven modified shell scripts pass `bash -n`; known-answer repository tests: 69 run, 67 passed, 2 skipped. No new binaries or APKs are committed. R2 is **partially**: HelloWorld has machine and screenshot evidence on 3/3 boards; ZigZag and independent visual acceptance remain outstanding. No agent-spec lifecycle verdict is claimed for the new operational #22 entry (it supplies no spec selector).
