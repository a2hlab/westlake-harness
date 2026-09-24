"""Recompute analysis from the audited snapshot, not the mutable VM directory."""
import collections,gzip,json,sys
from pathlib import Path
p=Path(sys.argv[1]);a=json.loads((p/'audit.json').read_text())['apps'];maps=json.loads(gzip.decompress((p/'gap-maps.json.gz').read_bytes()))
HARD={'missing','null','strict','denied','stub','hollow','unresolved','absent'}
hits=collections.defaultdict(list);members=collections.defaultdict(set);symbols=collections.defaultdict(set);open_symbols=collections.defaultdict(set)
for key,m in maps.items():
 for r in m['rows']:
  if r['verdict']!='supplied':hits[r['id']].append((key,r))
  for mm in r.get('members',[]):
   if mm['kind'] in ['missing_class','missing_method','missing_field']:
    members[(mm['kind'],mm['owner'],mm.get('name'),mm.get('signature'))].add(key)
 covered={sym for row in m['rows'] for sym in row.get('covered_symbols',[])}
 for s in a[key]['oh_missing']:
  symbols[s['symbol']].add(key)
  if s['symbol'] not in covered:open_symbols[s['symbol']].add(key)
def route(gid,h):
 v={r['verdict'] for _,r in h};r=h[0][1];oh=r.get('oh_touchpoint')
 if gid=='load:runtime-silent-success':return ('integrity','registration-audit','核对 staged JNI 与内建注册表逐签名差集；验证 JNI_OnLoad/失败传播，不以每 app 复制行计 APK 缺口。',[2,5],'medium')
 if v=={'not-a-platform-service'}:return ('observation','detector','复核常量传播和调用寄存器；不是平台服务名不得创建产品 shim。',[0.5,2],'low')
 if gid.startswith('java:'):
  if not (v & {'missing'}):return ('candidate','AOSP-review','对照同 API 级 AOSP 逐成员检查：合法空回调不修；C8 需调用/反射/动态 DEX 证明；确认 C9 才移植。',[1,3],'low')
  return ('apk-dependency-candidate','AOSP','逐签名核对 API 版本和 SDK_INT 分支；移植已有 AOSP 实现，底层 '+str(oh)+' 另做适配；C1/C4/C9 须重分，不能按分组首行推断。',[3,10],'medium')
 if gid.startswith('pm:call:'):
  return ('apk-dependency-candidate','AOSP-PackageManager','按 AOSP PackageManager 语义实现 '+gid.split(':')[-1]+'；解析冻结 APK 的组件/IntentFilter/flags/权限，涉及其他包与 UID 时接 OH bundle 身份映射。',[1,3],'medium')
 if gid=='pm:providers':return ('candidate','probe','核对 provider 安装次序、initOrder、authority 和 onCreate；unverified 不是 missing，先做契约探针。',[1,2],'medium')
 if gid=='pm:multiprocess' or gid=='wv:renderer-process':return ('apk-dependency-candidate','AOSP+OH','保留 Android 进程/Provider/WebView 生命周期协议，接 OH appspawn、IPC、surface；远程进程和 renderer 不得用空代理伪装。',[10,25],'high')
 if gid.startswith('svc:'):
  name=gid[4:]
  if v=={'unresolved'}:return ('candidate','resolve-first','沿 AOSP fetcher/helper 找到真实 Binder，验证 '+name+' 的实际实现和启动调用，再选择适配；不把未知当缺失。',[1,3],'low')
  if name in ['accessibility','autofill','credential','appwidget','telecom','media_projection','media_router','statusbar','content_capture','launcherapps']:
   return ('candidate','truthful-unsupported-or-OH','验证 AOSP manager 无服务降级路径；真无设备/能力则暴露真实 feature/异常；需要时接 '+str(oh)+'，不可把 inert 自动当启动阻塞。',[1,3],'medium')
  if name=='user':return ('apk-dependency-candidate','AOSP-local','UserManager 的用户/解锁/限制查询返回当前宿主真实状态；保留权限与失败语义，消除 strict 代理无条件抛异常。',[1,3],'low')
  if name in ['jobscheduler','notification','audio']:
   return ('apk-dependency-candidate','AOSP+OH','恢复 '+name+' 的状态、回调、取消及错误语义；适配 '+str(oh)+'，用启动初始化与生命周期契约验证，不能返回默认成功。',{'jobscheduler':[3,7],'notification':[3,7],'audio':[5,15]}[name],'medium')
  if name in ['biometric','fingerprint','keyguard','wifi','sensor','camera','vibrator','phone','usb','servicediscovery','download','usagestats','wifip2p']:
   return ('apk-dependency-candidate','AOSP+OH-or-unsupported','提供 Android manager/失败语义并映射 '+str(oh)+'；逐设备确认能力/授权，不可由 OH 有对应子系统推断可用；缺硬件用真实 unavailable。',[3,10],'medium')
  return ('apk-dependency-candidate','truthful-unsupported-or-OH','按 '+name+' 的 AOSP 契约确认能力和权限；可用则接 '+str(oh)+'，不可用则返回规定的 unsupported/feature 状态，证明调用方降级。',[1,5],'medium')
 if gid.startswith('sym:'):return ('apk-dependency-candidate','AOSP-ABI+OH','按每个 symbol 拆 C1 转发、C2 布局/常量翻译、C4 NDK 后端；当前没有 Android NDK 声明索引，bionic-private 标签不可信。',[5,20],'high')
 if gid.startswith('load:'):return ('apk-dependency-candidate','AOSP-loader','按依赖和 SONAME 建立 app namespace、装载次序及 JNI 注册所有权；复用 AOSP linker 语义；禁止全局抢符号和假成功。',[2,5],'high')
 if gid.startswith('policy:'):return ('apk-dependency-candidate','OH-policy-or-unsupported','依据实际对象操作和设备策略重验；由 OH 系统侧决定沙箱内支持，或暴露真实 errno/unsupported；不得放宽全局策略或伪造成功。',[5,15],'high')
 if gid.startswith('dep:'):return ('apk-dependency-candidate' if 'absent' in v else 'candidate','truthful-unsupported','Google 专有服务不由 AOSP 提供：保留不可用信号；push/maps 等另审 OH 后端适配，不能承诺 Google 登录、授权或服务端校验通过。',[1,3],'medium')
 if gid.startswith('env:'):return ('candidate','truthful-unsupported','比较 Android 正常基线，保留完整性/设备能力真实结果；SDK 被拒载后的降级与服务端接受度需实测，不伪造认证。',[1,3],'high')
 return ('candidate','investigate','以行内 AOSP/OH 证据定位契约，先确认启动因果再改实现。',[2,5],'high')
gaps=[]
for gid,h in sorted(hits.items(),key=lambda x:(-len(x[1]),x[0])):
 origin,path,plan,days,risk=route(gid,h);hard={k for k,r in h if r['verdict'] in HARD};keys={k for k,r in h}
 gaps.append({'id':gid,'apps':len(keys),'which':sorted(keys),'hard_apps':len(hard),'hard_which':sorted(hard),'verdicts':dict(collections.Counter(r['verdict'] for _,r in h)),'classes':dict(collections.Counter(r.get('shim_class') for _,r in h)),'stack_counts':dict(collections.Counter(a[k]['stack'] for k in keys)),'hard_stack_counts':dict(collections.Counter(a[k]['stack'] for k in hard)),'dynamic_reached':None,'first_confirmed_blocker':None,'observed_stage_transition':None,'origin_assessment':origin,'repair_route':path,'repair_plan':plan,'effort_engineer_days':days,'risk':risk,'oh':sorted({str(r.get('oh_touchpoint')) for _,r in h}),'source_evidence':sorted({str(r.get('provider_source')) for _,r in h if r.get('provider_source')})})
# Ordered, deliberately broad repair packages. This is a sensitivity model, not a forecast.
packages=[('user',{'svc:user'}),('package-manager',{g for g in hits if g.startswith('pm:call:')}),('jobscheduler',{'svc:jobscheduler'}),('notification',{'svc:notification'}),('native-entrypoints',{g for g in hits if g.startswith('sym:')}),('loader',{g for g in hits if g.startswith('load:') and g!='load:runtime-silent-success'}),('java-members',{g for g in hits if g.startswith('java:')}),('audio',{'svc:audio'}),('webview-process',{'wv:renderer-process','pm:multiprocess'}),('device-managers',{'svc:wifi','svc:keyguard','svc:biometric','svc:fingerprint','svc:servicediscovery','svc:usb','svc:usagestats','svc:wifip2p','svc:storagestats','svc:search','svc:media_metrics','svc:device_policy','svc:dropbox','svc:restrictions'})]
# Unknown and unmeasured are not silently considered fixed. Candidate-only rows are separate.
sets={k:{r['id'] for r in m['rows'] if r['verdict'] in HARD and r['id']!='load:runtime-silent-success'} for k,m in maps.items()}
remaining=collections.Counter();covered=set();scenarios=[]
for n,(name,ids) in enumerate(packages,1):
 covered|=ids;touched=sorted(k for k,s in sets.items() if s&covered);clear=sorted(k for k,s in sets.items() if s and not (s-covered))
 # Relax policy, vendor-dependency, hardware services only: exact sensitivity assumptions listed in output.
 optional={g for g in hits if g.startswith(('policy:','dep:','svc:')) and g not in {'svc:user','svc:jobscheduler','svc:notification','svc:audio'}}
 optimistic=sorted(k for k,s in sets.items() if s&covered and not(s-covered-optional))
 scenarios.append({'N':n,'package':name,'gap_ids':sorted(ids),'touched_apps':len(touched),'touched_which':touched,'all_hard_rows_cleared':len(clear),'all_hard_rows_cleared_which':clear,'optimistic_startup_candidates':len(optimistic),'optimistic_which':optimistic,'actual_startup_unlocks':None,'guaranteed_new_unlocks':0})
result={'schema':'static-100-analysis/v1','dynamic_evidence':'not-collected','gaps':gaps,'missing_members':[{'kind':k[0],'owner':k[1],'name':k[2],'signature':k[3],'apps':len(v),'which':sorted(v)} for k,v in sorted(members.items(),key=lambda x:-len(x[1]))],'oh_missing_symbols':[{'symbol':k,'apps':len(v),'which':sorted(v)} for k,v in sorted(symbols.items(),key=lambda x:-len(x[1]))],'open_native_symbols_after_shim':[{'symbol':k,'apps':len(v),'which':sorted(v)} for k,v in sorted(open_symbols.items(),key=lambda x:-len(x[1]))],'scenarios':scenarios,'model_assumptions':{'policy':'sensitivity-only, no probability or dynamic reach inferred','hard_verdicts':sorted(HARD),'integrity_excluded':['load:runtime-silent-success'],'optimistic_tolerated_ids':sorted(optional),'unknown_rows_remain_unverified':True}}
(p/'gap-analysis.json').write_text(json.dumps(result,indent=1,ensure_ascii=False)+'\n')
lines=['# 全量分组处置表（分析口径 v1）','','`静态/硬` 是唯一 app 数。动态到达、首阻塞与阶段跃迁全部未测。工日按本行小契约估计，不能把各行相加；共享修复见 README。Java 分组不是规范 §12 的 canonical gap。','','| ID | 静态/硬 | 队列 | 修复路径与证据要求 | 工日 | 风险 |','|---|---:|---|---|---|---|']
for g in gaps:lines.append(f"| `{g['id'].replace('|','/')}` | {g['apps']}/{g['hard_apps']} | {g['origin_assessment']} | {g['repair_plan']} | {g['effort_engineer_days'][0]}–{g['effort_engineer_days'][1]} | {g['risk']} |")
(p/'GAP-DISPOSITION.md').write_text('\n'.join(lines)+'\n')
print('gaps',len(gaps),'canonical missing members',len(members),'stacks',dict(collections.Counter(v['stack'] for v in a.values())))
for s in scenarios:print(s['N'],s['package'],s['touched_apps'],s['all_hard_rows_cleared'],s['optimistic_startup_candidates'])
