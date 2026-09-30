# 5cd went down during the boot image overlay test: init crashed, not the image

**What happened.** At 11:28 oc-t4 bind-mounted the 27 boot image files produced by the official
android-14.0.0_r16 dex2oat over `/system/android/framework/arm64/` on 5cd and restarted
appspawn-x. The board vanished from USB and needed a manual restart by the user.

**Cause, from the board's own fault log** (`cppcrash-init-0-20260930112842307.log`, pulled after
reboot): **PID 1 `init` crashed**, `SIGSEGV(SEGV_MAPERR)@0x34`, in `CheckOndemandService+156` <-
`ProcessSignal` <- `HandleSignalEvent_`, i.e. while init handled a child-exit signal. Registers
x11-x13 hold the ASCII text `t appspawn-x for service`. init dereferenced a null service record while
reacting to appspawn-x going away; an init crash takes the whole system down.

So the image was never exercised: the board fell over on the way appspawn-x was restarted, before
any app could load the overlaid image. `deploy_generation.sh` restarts appspawn-x routinely without
this crash, so the way the test restarted it is the suspect.

## Recovery (verified)

After the user restarted 5cd: all 9 boot jars and 27 image files are byte-identical to
`knowledge/toolchains/boot-image-inputs.sha256` (the overlay was bind mounts only), the installer
pair (FZ-001) survived. U0 replayed: v3c package (new boot, no `--upgrade`) active_verified, runtime
53f00423 `--replace` active_verified, JAR r17r bound; read back dd4f0eae / 53f00423 / 6aadb8b4 /
7048c7c5. HelloWorld t20 shows its own UI:
`TOTAL keys=1 screenshots_captured=2/2 alive_t5=1 alive_t20=1`.

## Rule

Restart appspawn-x only the way `deploy_generation.sh` does. A boot image board test must start from
that restart path (or load the image in a single child without restarting system services), and is
announced like an installer swap because it can take the board off USB.
