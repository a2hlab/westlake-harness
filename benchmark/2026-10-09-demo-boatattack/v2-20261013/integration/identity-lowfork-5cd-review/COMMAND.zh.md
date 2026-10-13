# 5cd metadata 原/新同目标只读对照（root 最后启动）

仅 5cd `5cd1e3dd00000000000000000923012c`，expected boot `c9436daa-b3ca-44dc-985f-9ee03445567a`。61b 不在此程序白名单。先读本目录 freeze/README。`PKG` 可指生产者目录或 root 已核字节相等的落库目录。必须从 Mac 启动锁与 Orb 调度，Reader 本体在 Orb Linux，两个 helper 都复用同一 `hdc_mac.sh` 和 `/system/bin/sh -c`。不部署 helper 到设备。

`BOARD` 指 root 当前 canonical 黑板绝对路径；`RUN` 必须全新。以下为 root 执行代码，本交件没有执行这些命令。若 root 已有本板合法独占锁，可保留该锁并按原调度收尾，不重复抢锁。

```bash
set -euo pipefail
: "${WORKSPACES:?}" "${BOARD:?canonical absolute board path}"
B=benchmark/2026-10-09-demo-boatattack/v2-20261013
PKG="$WORKSPACES/westlake-harness-t4/$B/integration/identity-lowfork-5cd-review"
RUN="$WORKSPACES/westlake-harness/$B/outer/metadata-lowfork-5cd-$(date +%Y%m%dT%H%M%S)"
NOTE="$WORKSPACES/westlake-harness/scripts/lab/board_note.sh"
SERIAL=5cd1e3dd00000000000000000923012c
mkdir "$RUN"
bash "$NOTE" lock "$BOARD" "$SERIAL" 'outer(codex)' 'readonly metadata original then lowfork; <=20min, no deployment'
trap 'bash "$NOTE" unlock "$BOARD" "$SERIAL" "outer(codex)"' EXIT
bash "$NOTE" held "$SERIAL" > "$RUN/held.txt"
python3 - "$PKG" "$RUN" <<'PY'
import hashlib,json,sys,time
from pathlib import Path
p,r=map(Path,sys.argv[1:]);h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((p/'plan.disabled.json').read_text());assert plan['execution_enabled'] is False
plan['execution_enabled']=True
(r/'plan.enabled.json').write_text(json.dumps(plan,indent=2)+'\n')
held=(r/'held.txt').read_text().strip();assert len(held.split())==3 and held.split()[0]=='outer(codex)'
auth={'approved_by':'outer(codex)','action':'metadata-readonly-ab','serial':plan['serial'],'boot_id':plan['boot_id'],'holder':held,'plan_sha256':h(r/'plan.enabled.json'),'runner_sha256':h(p/'compare_metadata.py'),'expires_epoch':time.time()+1200}
(r/'authorization.json').write_text(json.dumps(auth,indent=2)+'\n')
(r/'authorization.sha256').write_text(h(r/'authorization.json')+'\n')
PY
orb -m a2hlab env WORKSPACES="$WORKSPACES" MAC_HOME="$HOME" PYTHONDONTWRITEBYTECODE=1 \
 python3 "$PKG/compare_metadata.py" --plan "$RUN/plan.enabled.json" \
 --out "$RUN/compare" --authorization "$RUN/authorization.json" \
 --authorization-sha256 "$(cat "$RUN/authorization.sha256")" --execute \
 > "$RUN/compare.stdout.txt" 2> "$RUN/compare.stderr.txt"
```

每阶段顺序：核 Mac 真实全行 holder → 原 strict transport 读 boot/18 候选 SHA → `verify_metadata(507 files,5 dirs)` 共23批 → 同 boot/18 SHA → 再核 holder。先原 helper，成功后才跑 new。两者每项同 expected、同序列、同 parser、同远端 shell；除 UUID rc marker 外，23批 metadata 原始输出还须逐批相等。原 helper 不匹配就停止，不能拿两者同样错误算 PASS。

授权1200s，程序同预算且每次远端调用保留90s；不可能转入61b、coldboot、安装、bind 或输入事件。失败保留全部stdout/stderr及 `result.json`，trap 释放 root 所持锁；没有板上修改需要回滚。不要因只读失败改元数据使其通过。

结果仅 `METADATA_AB_PASS_ONLY`，衡量该次固定顺序的 metadata 耗时（不含 boot/SHA/held bookends），不是完整954/128准入，不允许替换正在跑的 pin。单次先旧后新有缓存/调度顺序影响；没有预先承诺性能增幅。
