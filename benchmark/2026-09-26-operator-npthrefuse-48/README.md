# df779574 refusal experiment, superseded by direct npth patch

Board61b06572, guardian disabled, consent retained, one original app per round. Shim source dc68e0b; deployed SHA df7795746e2c14dd501c1130705f508f79fe845de96f1aa55aef5659b02c9f51. Backed up85c789f4. Other baseline components unchanged, metasec1021a058, anonymous JIT, passive crash recorder, map_count1048576.

| Round | Original child | Seconds | Outcome | Article |
|---|---:|---:|---|---|
| npth-r1 | 1229 | 240.005 | alive, planned cleanup; no SIG11/exit1 | CCTV Mid-Autumn, title/body/two images |
| npth-r2 | 7190 | 240.009 | alive, planned cleanup; no SIG11/exit1 | CCTV tea meeting, title/body/image |
| npth-r3 | 13468 | 54.913 | user canceled, externally killed; excluded | no article attempt |

Real uinput: r1(380,515) uptime122253.47, NewDetail RESUMED122273.939 (20.469s); r2(380,375) uptime122543.64, RESUMED122564.908 (21.268s). See respective article-late.jpeg and anchored lifecycle logs. Feed refreshed between r1 gate capture and touch, so opened title differs from earlier second-row title. Current screenshot is authoritative.

Complete maps20/60/190 in both completed rounds contain libnpth.so AND libjato.so. Loader logs identify SOURCE-NATIVE-LOAD for each. Thus refusal does not cover these loading routes; no claim that the shim prevented their hooks. Refusal criterion superseded by user; failed mapping predicate retained as diagnostic. r2 has a nonfatal Chrome_ProcessLauncherThread RuntimeException: Illegal meta data value: the child service doesn't exist, with full stack. Both app survival and readable body nonetheless observed.

Third round was explicitly canceled for new patch task. Raw result reports loss of original after external cleanup, but cancelled.json records intentional cancellation; never count as spontaneous failure or completed reliability sample. All three apps and appspawn cleaned, free memory checked. No guardian restarted.

R2 partially: two warm survival/body observations verified, five-round objective canceled by user, refusal mechanism not effective on npth/jato. No push. Evidence hashes: python3 verify.py (or --git after commit).
