# 最终 seal 操作卡（外环执行；本交件零设备访问）

完成签认范围内 10 个游戏点击前后留图后执行。截图失败记不稳定，不扩大应用集合、不自动同意隐私，不清数据或杀 parent。本卡只收集/编译/自检；不重跑恢复、安装器、driver 或 reboot。

## 0. 一次设置路径及补齐外环输入

```sh
set -euo pipefail
: "${WORKSPACES:?设置工作区父目录}"
: "${HDC:?设置外环已验证的本地HDC可执行路径}"
export HDC WORKSPACES
export MAIN="$WORKSPACES/westlake-harness"
export RUN="$MAIN/benchmark/2026-10-12-v1-seal-execution"
export EXACT="$MAIN/benchmark/2026-10-12-exact-realization"
export T5="$MAIN/benchmark/2026-10-09-demo-baseline/t5"
export COLLECT="$MAIN/benchmark/2026-10-12-seal-snapshot-adapter"
export MANIFEST="$MAIN/benchmark/2026-10-09-demo-baseline/demo-manifest.json"
export SERIAL=61b0657200000000000000000324012c
export FINAL="$RUN/seal-final-$(date +%Y%m%d-%H%M%S)"
mkdir "$FINAL"
cd "$MAIN"
```

固定 `seal-final-inputs/groups.json` SHA `2229957460884f35fddf695c7a52ed5ec503f08482cbe54f55e3d67782d2d6f9`。完整 manifest SHA `7a2627326cb536bc8b0ee35587827999f448f827a91e22bdc663809767d82933`，128 apps；不可换成 inputs/demo-manifest-20.json。

外环在 `$FINAL/route-b-binding.json` 生成以下对象（不从 HAP 的1.0.0推断嵌入 APK 版本）：

```json
{
  "version_name": "实际toutiao.apk版本名",
  "version_code": "实际toutiao.apk版本码",
  "apk_sha256": "a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395",
  "identity_evidence": {"path": "APK元数据实证文件", "sha256": "完整SHA"},
  "source": {"path": "外环已审完整RouteB来源说明/manifest", "sha256": "完整SHA"},
  "rollback": {"path": "外环已审RouteB回滚入口", "sha256": "完整SHA"}
}
```

这些是需主树生成/签认的输入，不是本卡代签。source/rollback 不得因为同名就随意选一份24-controls或5cd-only回滚器来代表完整61b RouteB。游戏10项 before/after、头条当前feed/文章/返回/刷新、boot及缺陷说明另存签认附件；build_seal 不替代 UI 签认。

## 1. 完整只读 collect（由外环调用）

```sh
python3 "$COLLECT/collect.py" --serial "$SERIAL" --hdc "$HDC" \
  --groups "$RUN/seal-final-inputs/groups.json" --manifest "$MANIFEST" \
  --extra-package org.westlake.imehost --out "$FINAL/capture"
```

输出 `capture/{capture.json,snapshot.json,*.stdout.txt,*.stderr.txt}`。要求同boot、errors=[]、811目标全部成功，安装清单为128+宿主；真实数量以输出为准。collector 包含 BMS 实际安装 archive 的 SHA，不能用安装输入文件代替。不得删读失败项再编 seal。

## 2. 同 boot 的独立 WMS/host 证据与源字节（外环只读）

以下代码只使用已冻结 ReadOnlyCollector 读件方法；WID 来自 WMS，PID/UID/GID/birth/cmdline/HAP 分别交叉核对。它为运行中的源 run.sh 和新增5个文本文件保存原字节，并复用其余已钉 CAS；与 snapshot 不等就拒，不能改 snapshot 迁就模板。

```sh
python3 - <<'PY'
import json,os,sys
from pathlib import Path
sys.path.insert(0,os.environ['EXACT'])
import realization as r, observations as o
from selfcheck import ReadOnlyCollector
root=Path(os.environ['FINAL']); snap=r.read(root/'capture/snapshot.json')
c=ReadOnlyCollector(os.environ['HDC'],os.environ['SERIAL'],root/'source-running')
readings={}
def read(k,cmd):
 raw,readings[k]=c.read(k,cmd); return raw
cmd=o.commands('placement')
before=read('boot_before',cmd['boot_before']).decode().strip()
uid,gid=map(int,read('host_owner',cmd['host_owner']).decode().strip().split(':'))
read('host_hap',cmd['host_hap'])
w=o.parse_window(read('window_dump',o.WINDOW_COMMAND)); pid=w['host_pid']
cmd=o.commands('running',pid)
read('host_status',cmd['host_status'])
birth=o.parse_birth(read('host_stat',cmd['host_stat']),pid)
read('host_cmdline',cmd['host_cmdline'])
expected={t:h for group in snap['files'].values() for t,h in group.items()}
fp=r.read(Path(os.environ['EXACT'])/'source-fingerprint.json')
known={x['target']:x for x in fp['files']}; sources={}
for n,(target,sha) in enumerate(sorted(expected.items())):
 row=known.get(target)
 if row and row['sha256']==sha and not target.endswith('/run.sh'):
  p=r.pin(row['source'],Path(os.environ['EXACT'])); sources[target]={'path':str(p),'sha256':sha}
 else:
  allowed={
   '/system/etc/init/00_westlake_u13_recover-v3.cfg',
   '/system/etc/westlake-u13-recover-v3.sh',
   '/data/westlake-demo/u13/selinux-mode',
   '/data/westlake-demo/u13/u13-recover-table.tsv',
   '/data/westlake-demo/u13/u13-recover-table.json',
   '/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh'}
  r.need(target in allowed,'unexpected source drift needs review: '+target)
  raw,ref=c.read('source-%04d'%n,'cat '+target)
  r.need(r.bytes_sha(raw)==sha,'source bytes changed since snapshot: '+target)
  sources[target]={'path':str(c.directory/ref['stdout']['path']),'sha256':sha}
after=read('boot_after',cmd['boot_after']).decode().strip()
r.need(before==after==snap['boot_before']==snap['boot_after'],'source capture and snapshot must share boot')
obs={'schema':o.SCHEMA,'serial':os.environ['SERIAL'],'boot_before':before,'boot_after':after,
 'host_uid':uid,'host_gid':gid,'host_pid':pid,'host_birth':birth,'window_id':w['window_id'],
 'readings':readings,'synthetic':False}
p=c.directory/'observation.json';r.write(p,obs)
params={'serial':obs['serial'],'boot_id':before,'host_uid':uid,'host_gid':gid,
 'control_root':'/data/westlake-demo/toutiao/recovery-attempts/r1-9763171a-preview','window_id':w['window_id']}
ref={'path':str(p),'sha256':r.digest(p)}
r.write(root/'source-running-validation.json',o.validate(ref,p.parent,params,'running'))
r.write(root/'source-files.json',sources);r.write(root/'source-parameters.json',params)
PY
```

必须保留 observation及其所有raw件，不仅 normalized JSON。run.sh里的WID必须与上述独立观测精确相符；无活窗口/同boot证据时停止源seal派生，不硬填33。此要求只针对**源61b seal**，不阻塞已批准的**5cd placement WID=null**。

## 3. 从实测 overlay map 生成输入，调用原 build_seal

```sh
python3 - <<'PY'
import os,sys
from pathlib import Path
sys.path.insert(0,os.environ['EXACT']); import realization as r
root=Path(os.environ['FINAL']);s=r.read(root/'capture/snapshot.json');b=r.read(root/'route-b-binding.json')
for k in ('identity_evidence','source','rollback'):r.pin(b[k],root)
r.need(str(b['version_code']).isdigit() and b['version_name'],'embedded APK version missing')
payload='/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/toutiao.apk'
r.need(s['files']['overlays'][payload]==b['apk_sha256'],'embedded APK SHA differs')
row={'id':'toutiao-route-b','state':'active','route':'B','launch_kind':'embedded-in-hap',
 'host_package':'org.westlake.imehost','package':'com.ss.android.article.news','payload_path':payload,
 'apk_sha256':b['apk_sha256'],'version_code':b['version_code'],'version_name':b['version_name'],
 'source':b['source'],'rollback':b['rollback'],
 'files':[{'role':'ttbundle','target':t,'sha256':h} for t,h in sorted(s['files']['overlays'].items())]}
r.write(root/'overlays.json',{'schema':'demo-overlays/v1','seal_stage':'v1','items':[row,
 {'id':'boatattack','state':'absent','files':[],'reason':'v1 excludes Boat; independent v2 admission required'}]})
PY
python3 "$T5/build_seal.py" --snapshot "$FINAL/capture/snapshot.json" \
  --overlays "$FINAL/overlays.json" --manifest "$MANIFEST" --out "$FINAL/seal.json"
```

`SEAL_COMPILED_OFFLINE` 不等于签字。应得到811个唯一declared files（包含v3 script43491…及另4静态输入）；原seal JSON一经固定，不为备机改serial/UID/WID或重签内容。

## 4. 生成两个显式request，compile及独立appendix

```sh
python3 - <<'PY'
import copy,os,sys
from pathlib import Path
sys.path.insert(0,os.environ['EXACT']);import realization as r
root=Path(os.environ['FINAL']);seal=root/'seal.json';obs=root/'source-running/observation.json'
base=r.read(Path(os.environ['EXACT'])/'request.5cd.placement.json')
base['source_identity']={'kind':'seal','path':str(seal),'sha256':r.digest(seal)}
base['source_seal']={'path':str(seal),'sha256':r.digest(seal)}
base['source_parameter_evidence']={'path':str(obs),'sha256':r.digest(obs)}
base['source_files']=r.read(root/'source-files.json')
r.write(root/'request.5cd.sealed.json',base)
same=copy.deepcopy(base);same['phase']='running';same['parameters']=r.read(root/'source-parameters.json')
same['parameter_evidence']=base['source_parameter_evidence']
r.write(root/'request.61b.sealed.json',same)
PY
python3 "$EXACT/exact_realization.py" compile \
  --request "$FINAL/request.61b.sealed.json" --out "$FINAL/realization-61b"
python3 "$EXACT/appendix.py" \
  --realization "$RUN/exact-5cd-placement/realization.json" \
  --sealed-request "$FINAL/request.5cd.sealed.json" --out "$FINAL/appendix-5cd"
```

appendix 内会调用同一compile，生成 `appendix-5cd/sealed-realization/realization.json`；无须重复独立compile 5cd一次。它保留实际部署所绑的原candidate proof SHA、真实seal SHA、所有旧目标SHA，并追加5个静态目标。status仍 `UNSIGNED_REQUIRES_OUTER_SIGNOFF`。源WID与模板不同仅经single assignment+同boot独立WMS证明通过；其余字节不等即拒。

## 5. 61b只读自检；5cd必须走r3激活绑定

```sh
export SOURCE_BOOT="$(python3 -c 'import json,os;print(json.load(open(os.environ["FINAL"]+"/source-parameters.json"))["boot_id"])')"
bash scripts/lab/demo_selfcheck.sh --realization "$FINAL/realization-61b/realization.json" \
  --serial "$SERIAL" --boot-id "$SOURCE_BOOT" --hdc "$HDC" --out "$FINAL/selfcheck-61b.json"
```

若重新开机，SOURCE_BOOT须外环重新独立读取；当前WID由新自检WMS/host读取，不能反读run.sh。自检发现合法WID字段尚未派生也不可忽略SHA；任何实际字节变更另走外环已授权流程，本卡不写板。

**5cd blocker已定位：3791的placement proof是disabled，restore.prepare激活了startup.env及startup.expected.sha256。禁止直接以3791 selfcheck验激活板，也禁止忽略这两项。** r3独立入口必须先复原并核对prepared，精确替换仅两项预期，再派生当前WID；全811目标及原seal非文件判据均保留。

外环在 `$FINAL/activation-binding.5cd.json` 生成 `exact-activation-selfcheck-binding/v1`（由下方r3 build_binding.py生成，勿手造成功回执）：

- `checker_sha256`：r3/selfcheck.py 当前不可变SHA。

- `realization`：`$FINAL/appendix-5cd/sealed-realization/realization.json` pin。
- `origin_realization`：实际部署所绑 `$RUN/exact-5cd-placement/realization.json` pin。
- `appendix`：`$FINAL/appendix-5cd/appendix.json` pin。
- `prepared_manifest`：`$RUN/exact-5cd-preview/manifest.json` pin。
- `admission`：`$RUN/exact-5cd-admission-r2/admission.json` pin。
- `restore_adapter`：`$EXACT/r2-timeout/restore.py` pin，SHA `af1ce6fc2f6b43568e8acec9f06cd63c92f48aa10c49c6b3a16c7c39258b2f05`。
- `execution_receipt`：`$RUN/exact-5cd-transaction-r2.realization-receipt.json` pin。
- `transaction` / `placed`：新txn中 `transaction.json` / `placed.json` pins。
- `member_receipts`：按plan顺序全部487份 `placed-NNN.json` pins，实际文件名以executor产生为准。
- `execution_cwd`：`$WORKSPACES/westlake-harness`，`synthetic=false`。

旧 `exact-5cd-transaction` 是rc=-15、无transaction的只读中止，不可作为成功输入。r2尚在执行时，不存在的receipt保持缺失；不先制造文件补齐。必须是executor_rc=0且实际placed全部487，完整source/origin/admission/plan/目标SHA逐项匹配。当前boot可以不同于placement boot；新观测验证当前身份，历史授权不重新变成可执行授权。

```sh
python3 "$EXACT/r3-activation-selfcheck/build_binding.py" \
  --realization "$FINAL/appendix-5cd/sealed-realization/realization.json" \
  --origin-realization "$RUN/exact-5cd-placement/realization.json" \
  --appendix "$FINAL/appendix-5cd/appendix.json" \
  --prepared-manifest "$RUN/exact-5cd-preview/manifest.json" \
  --admission "$RUN/exact-5cd-admission-r2/admission.json" \
  --restore-adapter "$EXACT/r2-timeout/restore.py" \
  --execution-receipt "$RUN/exact-5cd-transaction-r2.realization-receipt.json" \
  --transaction-dir "$RUN/exact-5cd-transaction-r2" --execution-cwd "$MAIN" \
  --out "$FINAL/activation-binding.5cd.json"
: "${TARGET_BOOT:?外环独立读取当前5cd boot UUID}"
export BINDING_SHA="$(shasum -a 256 "$FINAL/activation-binding.5cd.json" | cut -d ' ' -f1)"
python3 "$EXACT/r3-activation-selfcheck/selfcheck.py" \
  --activation-binding "$FINAL/activation-binding.5cd.json" --binding-sha256 "$BINDING_SHA" \
  --serial 5cd1e3dd00000000000000000923012c --boot-id "$TARGET_BOOT" \
  --hdc "$HDC" --out "$FINAL/selfcheck-5cd-activated.json"
```

执行前r3须已独立审收/落主树；以上不把尚未存在的r3或成功receipt声称已就绪。`--observed`只返回OFFLINE_MATCH；真正只读PASS也不代替截图验收。

## 6. 独立签认附件与入口

外环最终签认文件至少pin：原seal、两份realization、appendix、r2 admission/实际成功txn全套、两板新只读selfcheck、10游戏和头条图证据、已知随机SIG11限制；由原约定角色签认，不由compiler填写signed_by，不覆盖原seal或candidate proof。

恢复预算现走r2，最终一键入口 `scripts/lab/demo_restore.sh --realization ...` 必须已落r2 wrapper（SHA `8f83c13b7503971ef7c42086607fadb459496251625e2672e4a8d02283e94b2b`）。显式入口 `$EXACT/r2-timeout/exact_realization.py` 等价。**本卡不重启正在运行的r2 txn，也不重复restore**。r2超时仅报UNKNOWN/rc124，不能据此宣称回滚或重新安装。
