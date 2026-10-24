# Recreated-title click: dispatched and handled; one early frame is inconclusive

The unchanged feed frame is not a passing content-response image. It also does not establish a missing input handler or child exit. Full persisted child6915 stderr is25,364,255 bytes,230,132 lines, SHA1b71581e35cba53e9afc3f45237d2e5028806f519e653b127ab42487cc7318b8. Before/after stat/full SHA and all transfer receipts agree. Original bodies remain private; backup location and exact pins are in `backup.json`. Collection occurred after restoration under boot2a0a0e76, not live candidate boot95e4dd54.

| Observation | Exact evidence |
|---|---|
| Touch command | `0261-recreated-content`:04:46:59.283739–59.658650, `click3871540`, local0/remote0 |
| App dispatch | Full-log213655 DOWN uptime288037ms;213708 UP288138ms; coordinates387,1540, app visible/not stopped/added |
| Handled |213718 Decor handled=true at288139ms;213719 receiver handled=1;213721 dispatch end |
| Recovery |212356/212384/212396: logical30/31/32 outcome6 (Committed) |
| Activity/new window |213935: JIT compilation of ArticleInflowActivity.onCreate at printed04:47:00 (compilation, not proof of onCreate completion);214255 session48;214277 RESUMED uptime289183ms |
| Show/focus |214620–214621 have no own timestamp; adjacent log markers289942/290032ms. LaterFocus214904 is adjacent290520/290536ms |
| Response capture |0270 capture04:47:00.965152–01.406314,1.306–1.747s after click return; externally reviewed unknown, unchanged feed |
| Still alive |0278 rollback-reboot-before at04:47:18.531985–18.662620: same6915/b10896 and9986/b26754 before normal recovery reboot |

A conditional correlation using the already captured same-boot `/proc/uptime307.08` command bracket and local monotonic elapsed differences places the screenshot command around uptime289.383–289.964s (assumes equally advancing clocks/no suspend). This is not an exact capture instant. Show's neighboring timestamps overlap that interval; **Show cannot strictly be declared later than the screenshot**. The later Focus neighbors follow it. Missing own timestamps must remain unknown. A single roughly2s image cannot exclude later content expansion; bounded later real images are needed. No existing image is relabeled passing.

The b503ee success clicked1100,888 at04:24:56.710450–57.067494; its capture started1.374s after click return and was actually reviewed usable. Different targets/boots are not a controlled comparison. Its original archived RUN had no child6715 stderr/hilog/parent-log collection commands. A subsequent explicitly authorized full6715 read now supplies the missing dispatch/focus side, separately pinned below.

The current parent log contains no6915-specific exit record; later-boot log absence is not an exit finding. A positive original process sample already shows6915 alive after the click. No random-exit explanation is attempted. The current persisted window record was also collected after reboot and cannot substitute for the candidate-time snapshot.

Boot1-02 stopped on the unknown content image, restored exact baseline actual mapping, original power and lock. No boot2/handoff/retention pass. `check_evidence.py` replays hashes, exact lines, timestamps, identity and comparison offline; no subprocess/device operation. No runtime modification or new board window was performed for this review.

## Later authorized6715 comparison

Complete40,100,120-byte/427,269-line persisted6715 log SHA4f6c43bd2f26313f79d04b7e59eba3ced9b439e2a9b3ac1514b638f4a24af5d9 was received with stable pre/post stat/full SHA and rc0. Durable backup is indexed in `success6715-backup.json`. The original b503ee mapping binds6715/b9179 and candidate3291; the later collection is not live current-boot6715 evidence.

Successful1100,888 input:412851 DOWN uptime352566ms;412989 UP352670ms;413208–413209 handledtrue/1 at353010ms;413446 creates session44;413467 RESUMED353451ms;413583–413584 Show/Focus44 (no own timestamp; neighboring353688/353799ms). Recovery Committed29/30 appears396372/396394. Both examples reached visible app dispatch and new-window operations. The six ArticleInflowActivity matches10724/10729/30325/30330/30995/31006 are configuration-body strings, not execution evidence; whether successful全文 navigation used that class remains **unknown**. No pure-delay or API-defect cause is inferred.
