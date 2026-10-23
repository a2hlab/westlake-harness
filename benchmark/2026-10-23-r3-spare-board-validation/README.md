# T121: offline promotion accepted; device execution not started

**No device deployment or validation occurred.** The promotion package passed70 metadata checks, but the executor draft failed review. Its revision lane then returned an automatic rejection with `[reasoning_extraction]`; the exact trigger/command was not stated. `execution-stop.json` records the visible error and unchanged executor SHA. No alternate executor or tool retried the stopped revision.

The accepted payload is not evidence of a white-screen repair. `review/` and `executor-outer-review.json` distinguish package acceptance from outstanding execution checks. The draft executor remains in its author's analysis branch and the private outer archive; it was not promoted to a runnable main-tree deployment tool.

The later narrowed contract requires unconditional restoration of the original init and a software reboot to the old ROOT after sampling. The executor still needs that change, the exact plan adapter, global deadline and recovery handling, verified UI targeting, byte/mode readbacks, and full power-setting restoration. Do not execute the draft or the package plan on its own.

Original package preparation notes follow; their local mode and package claims remain valid.

---

# T121 — concrete offline promotion handoff

T120's outer acceptance SHA is pinned in results. Promotion executed offline with rc0. **Only startup.env's ENABLED/APPROVED_BY lines and startup.expected.sha256 bytes changed.** All other20 payload files, including the original17 fixed outputs, remain byte-identical. The original disabled package is unchanged.

Actual package: `$OWNER/benchmark/2026-10-23-r3-spare-board-validation/.private/promotion-01/`.

- package-manifest.json binds22 files and actual local modes.
- install-manifest.json gives20 installable files, exact newROOT targets, SHA, mode and intended device owner0:0. recovery.cfg and rollback-inert.cfg are excluded from installation.
- All16 member modes are applied from members.tsv: scripts and screen-gate0550, decoder image0440. Boot-entry0550, members/startup/expected0440 follow approved metadata. The two excluded cfg artifacts are0640. All22 local modes were read back. Local ownership is not claimed to be device root ownership; CC must set and verify0:0 on the device.
- init.before.cfg and init.rollback.cfg are exact T116 bytes SHA19d0201b…; init.after.cfg SHA9d9196a1… changes only service westlake-u13-toutiao-overlay path[1] to the newROOT boot-entry. Mode0550 is applied locally and required on the device; the original device owner/label/mount state must be preserved by CC. Generated recovery.cfg must never replace live init.

The plan is a concrete artifact/install handoff, not a new observation executor. CC owns fresh identity/lock/mount/SELinux checks, the existing exact init replacement/restoration method, timing, reboot/UI/facts and failure rollback. Payload send/install/readback argv are listed but were not executed. Fresh directory/label and system-write bindings remain execution prerequisites; no guessed remount or chcon command is supplied. Device execution remains disabled here until outer confirms exact SHA for CC.

The promotion uses the original approval event as provenance; it does not request new user authorization. UID remains metadata only; historical61b success is not5cd runtime qualification.

## Checks and replay

Real init single-argv and synthetic promotion allowlist assertions: final9/9. Initial8/9 failure is retained: the synthetic regular-file fixture used the OS symlinked temporary path, correctly rejected by the production path guard; the fixture was corrected to use its physical directory. Runtime implementations were only copied/hashed, never inspected or executed.

From the owner tree, choose a new persistent output directory:

```sh
python3 benchmark/2026-10-23-r3-spare-board-validation/promote.py \
  --t120 benchmark/2026-10-23-qualified-r3-board-package/.private/build-02 \
  --acceptance "$HOME/.local/share/westlake/t120-outer-review-20261023/outerreview.json" \
  --out "$HOME/.local/share/westlake/r3-spare-board-validation-replay-NEW"
```

Existing output is refused. Original argv/start/end/rc/stdout/stderr are under `.private/promote01/`; preparation and assertion failures remain separately retained. No devices, controllers, deployment, commit or push; author_commit=null.
