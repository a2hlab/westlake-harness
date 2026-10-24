# Parent ordinary output: sequence closed, timing unresolved

All retained command receipts and stdout SHA/size checks pass. The fd batch has identical before/after boot/PID5129/birth11126/UID0 records; fd1 and fd2 both resolve to parent.log. The later log-post identity agrees. The log batch itself does not contain an identity-before receipt; no such receipt is invented.

The regular file is281883bytes, dev66352/inode426277. Its pre/post stat is identical. The retained tail is262144bytes, offset19739, SHA `cc52a0604e13805bafc914b3c8264061f35f83c67b580487f02f2608bf187b11`; it is not the full file.

Tail L2256–2268 records **Accepted connection → Parsed spawn request → preFork OK → child22035 → response result0**. `excerpts.txt` preserves selected ordinary lines with tail-relative line numbers. These lines contain no timestamp. msgId repeats in earlier transactions, so it alone is not a unique request correlation key.

**Conclusion:** the recorded spawn sequence succeeded. Current evidence cannot place request acceptance near the click or near spawn_started. Focus mtime11:06:44 and parent/spawn mtime11:07:27 do not supply per-record times. The supplied spawn_started65351/birth65353.69/spawn_ok65355 stages remain distinct from the host's timestamped foreground callbacks. No cause for the preceding~44s is established.

**Minimal next observation, not execution:** during a separately authorized ordinary click, retain initial parent.log offset/identity, then bounded serialized~1s samples of only appended bytes plus ordinary host/parent/child process existence and birth, each bracketed by same-boot uptime. Record click interval and reuse host hilog times. Limit90s/1MiB; stop on replacement/truncation and preserve gaps. This bounds when each message became observable and when the child existed. Early visible acceptance before child creation is distinguishable; late visibility cannot prove late acceptance because output buffering is not established. If those bounds still overlap, report unresolved rather than add guessed files or mechanisms.

No device, source/control inspection, REA, hook, or automated experiment was performed.
