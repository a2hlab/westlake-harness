# Guardian/video compatibility audit

The original T34 toolchain cannot accept a new r3 guardian by changing fresh input alone. The executor pins two old constants; the binder compares old cfg twice and all 18 old controls. Transport and driver source pins also require an exact successor.

`results.json` records original file/line findings. The adjacent `guardian-r3-video` package implements only the precise substitutions in `mechanical.diff`, retaining old files. **29 actual offline tests pass** (including original transaction/transport/recovery cases); real r3 installation and fresh authorization remain unknown to this audit. No device calls. The actual armed package has 20 deployment members, of which the original 18 control basenames are pinned; screen-gate/probe and cfg backups are not silently counted as those controls.

Fresh capture must also select the new root and successor paths. Merely passing an old W04 intake to the new binder is rejected. Recovery retains the r3 guardian and restores the six video states; runtime restoration does not establish feed health.
