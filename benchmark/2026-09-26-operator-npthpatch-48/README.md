# Direct libnpth hook patch: warm reliability remains blocked

**Pure baseline + patch: 3/5 survived240s, three distinct articles readable, two early SIG11 failures. Not an operator reliability pass.** Board61b06572 only. Independent branch `test/npth-nohooks-48`; no push, system partition writes, guardian, #50, or master-switch shim.

| Formal round | Original child / parent | Observed seconds | Survival | Body |
|---|---|---:|---|---|
| pure-r1 |22674 /22641|240.009|planned cleanup, alive|人民日报：把中美建设性战略稳定关系从愿景转化为行动|
| pure-r2 |27874 /27841|240.009|planned cleanup, alive|光明网：纪念长征胜利90周年主题展览|
| pure-r3 |1087 /1023|24.498|SIG11, platform-single|not reached|
| pure-r4 |4135 /4114|240.000|planned cleanup, alive|央视：习近平圆满结束对美国的国事访问|
| pure-r5 |9492 /9462|17.424|SIG11, npth-worker|not reached|

Survival measured from original app spawn to observation/cleanup, **not180s after article RESUMED**. No restarts counted as survival. All rounds preserve consent, start with both pidof sets empty, and clean child+appspawn with memory verification afterward. Per-HDC deadline<=55s and original PID/birth one-shot cleanup prevent stuck rounds. Full maps copied to normal board files before receive.

## Deployment and isolation

Backed up8b8d559c then deployed libnpth SHA `4f7cc3a62b08216b4ad3e114ec13f1468256b76ad35c94d870a83a052c27b0d2` to runtime `lib/arm64-v8a/libnpth.so`, mounted as `/data/local/tmp/asx/lib/arm64-v8a/libnpth.so`. claude-3's script (harness dd9356d) changes two instructions at file offsets0x1ffb4/0x24a34 to mov x0,#1. Exact8-byte region diff and hashes retained; no rebuild.

Preliminary **patch-r1** used df779574 shim and is excluded from the five formal rounds. It survived240.007s and opened Xinhua Mid-Autumn body. Before pure-r1, explicitly restored shim `85c789f48b2bc0c31658c9dc591cd27784cc0ddfe559005e8d36d1d7d220476a`, backing up df779574. Every formal round verifies all seven component hashes. mc46 bridge, refined metasec1021a058, tt targets/LD_PRELOAD, core libandroid, passive ART recorder retained. Anonymous JIT; map_count1048576. Relative to the stable baseline, libnpth is the single changed library.

All five formal rounds have complete valid maps (crash snapshot for r5) showing libnpth. All have SOURCE-NATIVE-LOAD and **ULE=0, npth load failure=0, parent exit(1)=0**. For surviving rounds, `/proc/PID/root/.../libnpth.so` SHA directly matches4f7cc3a6. The two early deaths have initial component SHA plus original-child crash maps; post-death /proc probe absence is not a load failure. Mapping and absent load/JNI errors support successful loading under the requested criterion; **no direct JNI_OnLoad return-value trace exists**, so none is claimed.

## Physical article evidence

| Round | Real uinput coordinate | Click uptime | NewDetail RESUMED uptime | Delta | Body screenshot |
|---|---|---:|---:|---:|---|
|pure-r1|380,541|123308.95|123324.244|15.294s|[正文](evidence/pure-r1/article-late.jpeg)|
|pure-r2|380,673|123557.70|123573.931|16.231s|[正文](evidence/pure-r2/article-body-2.jpeg)|
|pure-r4|380,291|123947.82|123977.094|29.274s|[正文](evidence/pure-r4/article-late.jpeg)|

Each click was `uinput -T -d x y -u x y`, after inspecting real unobstructed feed. No i/c injection. Each has anchored NewDetail ENTRY and corresponding RESUMED plus manually inspected body, not JSON substring counts. r2 initially had an empty body shell after RESUMED; only the later text+image frame is accepted. No <2s performance claim.

## Failures and limits

- **pure-r3**: parent confirmedsignal11; event-43f-8a1-1, platform-single/TID2209, fault0. musl ELF PC0xd6e20 (file0xd5e20), LR0xd6a18 (file0xd5a18), allocator metadata check/null-write failure path. Initial seven hashes correct. maps20=3896 lines; crash maps=3952. npth+bytehook/shadowhook+godzilla-memsponge/godzilla-sysopt+jato/monitorcollector-lib mapped. The victim does not establish the corruptor.
- **pure-r5**: parent confirmedsignal11; event-2514-2623-1, npth-worker/TID9763, SEGV_ACCERR. musl ELF PC0x111974 (file0x110974), LR0x111918; `sigaction+0x1a4`, `str x8,[x19,#144]`. This is a distinct sigaction-write fault, not automatically a mallocng failure. Full crash maps3569 lines include patched npth, monitorcollector-lib, bytehook/shadowhook and npth backtrace libraries. Registers/maps/nearby disassembly retained.
- Both recorders captured metadata/ucontext/maps but `/proc/self/mem` EACCES; **no complete native backtrace**. No missing stack is represented as a complete one.
- Successful pure rounds1/2/4 each also log nonfatal `Chrome_ProcessLauncherThread RuntimeException: Illegal meta data value: the child service doesn't exist`; full stacks retained. These did not stop the observed article pages, but are not silently treated as absent.

Two failures falsify the sufficiency of this patch with85c789f4. The test does not prove which remaining monitor or ABI path causes them, nor that Bionic is necessary.

## Final board state and validation

App and appspawn pidof empty. Both `/data/local/tmp/operator45/stop` and `/data/local/tmp/operator45/fresh48/stop` present, no fresh guardian lock; no delivery instance running. Consent retained,85c789f4+4f7cc3a6 left staged, map_count1048576. See final-check/board-state.txt. R2=partially: deployment and five observations verified, reliability acceptance failed.

Run `python3 verify.py --git` after commit to verify all exported raw/gzip hashes and tracking. Python scripts pass syntax checks. Raw samples, lifecycle/input logs, screenshots, all seven component hashes, parent/child stderr and both recorder events are in evidence/manifest.json. No ART/WebView rebuild was performed.
