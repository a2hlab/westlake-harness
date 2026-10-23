# T106 independent comparison —18 mapped files match; coverage partial

Actual offline checker rc0. Independently parsed saved ps, process stat/cmdline/maps, per-file stat/SHA/stat and final process identities. Both boards have one exact-name target child and host in fresh/final ps. Child executable is `/data/local/tmp/asx/appspawn-x`; host executable `/system/bin/appspawn`. Final boot/birth agree:

| Board | Boot | Child PID/birth/UID | Host PID/birth |
|---|---|---|---|
|61b|61aa5791-fd69-4bbb-a7b5-333b5d913c81|6291 /142694 /20011206|4958 /10879|
|5cd|62db0627-dc5e-4928-a780-e716c9f28301|21639 /2117333 /20011300|19801 /2115862|

**18/18 exact relative-path pairs match SHA:**9 native backing objects (including both libandroid variants),3 APKs,6 boot members. All36 map/file observations have matching dev/inode and unchanged before/after stat fields. File bytes are read through the observed PID root; this is not a live-memory hash or proof of a named linker namespace.

Both processes map `asx/libandroid.so` (c9969638…) and `asx/webview-t-lib/libandroid.so` (76512d97…), different files/inodes within each board. Both variants independently match across boards. Repeated map segments of one backing object are not counted as distinct instances. No duplicate-process target was found in the sampled ps, but this is not a global historical instance claim.

Actual core receipts: 47 command receipts, only two held=1 and other recorded core rc0; one explicit5cd_exact_files NOT_RUN index row is not an executed receipt.61b additionally has27 physical disk hashes, each with one stat sample; these are not27 mapped or cross-board comparisons. Nine BCP JARs and HAP lack comparable two-board hashes; active BCP order remains unknown.

Both supplemental `hap_supp` attempts are **rejected evidence**, despite aggregate rc0: serial includes the PID, body uses `/proc//…`, and output is CPU statistics without HAP stat/SHA. Original failure receipts are pinned. T106B corrected batch is not yet consumed; HAP stays unknown and will be a separate supplement. Initial checker failure also remains: it tried to open an explicit NOT_RUN row's nonexistent receipt; corrected parsing distinguishes unexecuted plan entries, and rc0 replay is recorded separately.

No version difference in these18 core backing files supports swapping packages. This does not prove equal conditions or equal causes: boot, UID, process age, application data/cache/configuration and unsampled files differ or remain untested. No timing or failure attribution is made.

Reproduce `checker.py --raw <cc root> --plan-files <fixed files.json> --output <new output>`. Actual invocation stdout/stderr/receipts are `.private/`; raw input pins are in results. Device/frozen/REA/Git operations zero. No supplementary collection requested or executed.
