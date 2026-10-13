"""English presentation only; canonical API records are never translated or mutated."""
def english_shell(first,last):
    labels={
      'lang="zh-CN"':'lang="en"', 'Harness · API 实现全景':'Harness · API implementation atlas',
      'API 实现与验证全景':'API implementation and evidence atlas',
      '从接口缺口，到实现、跨 APK 实测和冻结。这里记录的是证据能证明的范围。':'Implementation, APK tests and registration: each claim follows its evidence scope.',
      '本次离线整理；历史上屏、日志过墙、静态存在分别列出。unknown 表示缺少证据。':'Offline evidence update only. Historical screen output, log progress and static presence remain separate. unknown means missing evidence.',
      'English</a>':'中文 / Chinese</a>', 'href="index.en.html"':'href="index.html"',
      '中文完整表':'Chinese full table', '下载 CSV':'CSV', '历史 NDK 逐符号':'Historical NDK symbols', '历史 JNI 占位声明':'Historical JNI stub declarations',
      '知识条目含冻结索引、支撑工具及交叉引用，不是独立 API 数；Android 源码版本不等于支持版本。NDK API 33 的历史符号明细与当前功能有效性分开保存。':'Knowledge rows include registration indexes and supporting records, not independent API counts. Android source references do not establish supported versions. Historical NDK API33 symbols do not prove current functionality.',
      '已知版本地图与待补证据':'Version evidence and remaining gaps',
      '下一步优先补：当前部署 SHA 与 namespace/JNI 绑定、逐 APK 的版本和功能证据、跨 OH 版本的独立复验，以及源码到产物的可重建记录。历史首屏不能代替音视频、网络和后台等功能验证。':'Remaining work: actual deployment SHA and JNI bindings, per-APK versions and functional evidence, independent OH-version tests and reproducible source/build provenance. Startup screenshots do not prove general functionality.',
      '搜索 API、APK、版本、实现方法…':'Search API, APK, versions or implementation…', '搜索':'Search',
      '全部实现状态':'All implementation states','实现状态':'Implementation state','全部能力分类':'All families','能力分类':'Family',
      '全部冻结状态':'All registration states','冻结状态':'Registration state','已登记冻结':'Registered','未登记冻结':'Not registered',
      '知识条目':'Knowledge rows','冻结条目':'Registered entries','已核 SHA 来源':'SHA-checked sources','历史 NDK 符号':'Historical NDK symbols',
      '来源':'Source','API能力':'API capability','冻结索引':'Registration index','支撑知识':'Supporting knowledge',
      'API 成员':'API members','实现方法':'Implementation','源码 / 产物':'Source / artifact','Android 源码':'Android source','Android 实测':'Android tested','OH 实测':'OH tested','ABI / 路由':'ABI / route','部署证据':'Deployment evidence','冻结 / 关联':'Registration / related IDs','限制与待补':'Limits / pending evidence',
      '未记录':'Not recorded','APK 验证范围':'APK validation scope','无直接 APK 验证记录':'No direct APK validation','证据来源':'Evidence sources',
      '本地静态页面，无外部脚本或网络请求。完整覆盖边界见 source-coverage.json；全景不是整个 Android SDK 的兼容承诺。':'Local static page; no external scripts or network requests. See source-coverage.json for coverage. This atlas is not a full Android SDK compatibility claim. Existing314 row strings remain their original wording; NATIVE-173 has English presentation.',
      '显示 ${rows.length} / ${data.rows.length} 条；点开查看版本、验证结果和原始来源。':'Showing ${rows.length} / ${data.rows.length} records; expand for versions, validation and original evidence.'
    }
    # Replacements never touch the canonical JSON payload.
    for old,new in sorted(labels.items(),key=lambda pair:len(pair[0]),reverse=True):
        first=first.replace(old,new);last=last.replace(old,new)
    note='<p><strong>NATIVE-173 update:</strong> Fixed128 accepted for scoped startup nonregression with existing limitations; original947 recovery rc0. API not registered/frozen; V2 not sealed. OH tested only6.1.0.31; Android unknown/source-only.</p>'
    first=first.replace('<div class="metrics"',note+'<div class="metrics"',1)
    status="{implemented:'Implemented',partial:'Partial',stub:'Stub / fallback',missing:'Missing',unknown:'Unknown'}"
    last=last.replace("Object.entries(data.statuses)","Object.entries("+status+")").replace("data.statuses[r.implementation_status]","("+status+")[r.implementation_status]")
    return first,last

def english_presentation(row):
    vals=[dict(v) for v in row['validations']]
    vals[0]['result']='Six actual host function branches passed: successful dedicated SurfaceView child uses requested geometry; main and failed-child fallback use1200x1920. Not a full BLAST implementation.'
    vals[1]['result']='Root GAME_PASS on5ea/boot b711, samePID5158/birth7195/UID20011062 and seven pins. Round1920x1200 HUD; visible left/right/accelerate/reset and LAP0/3 to1/3. Not a completed circuit or whole-game functional claim.'
    for v in vals[2:7]:
        v['result']='Reported BMS visual review of the original db429 f28 t20 group: required popup controls retained. Original foreground_unconfirmed stays unchanged. This group is not borrowed for b711 admission.'
    vals[7]['result']='Outer ACCEPT_SCOPED_STARTUP_NONREGRESSION_WITH_EXISTING_LIMITATIONS: fixed128 original eight-window driver rc0;256/256 screenshots captured. Original alive counts t5=125/t10=120/t20=5 do not prove general usability. Original947 recovery rc0. APK startup branches and current-data replay on original947 reproduce sNotz/Toodoo content states across different boots. NOT_LIT/loading/splash/empty states, foreground_unconfirmed and failed app rc remain. No single-variable causal proof, note-store integrity certification or filter/edit/save functional tests. API not frozen; V2 not sealed; no61b write authority.'
    ev=[dict(e) for e in row['evidence']]
    for e,text in zip(ev[-4:],[
        'Authoritative outer final scoped startup nonregression acceptance, existing limitations, fixed128 and recovery rc0; V2 not sealed and no61b write authority.',
        'APK startup explanation plus original947 current-data cross-boot replay of sNotz/Toodoo content states; not a single-variable causal experiment or general app usability.',
        'Actual original full128 eight-window driver execution rc0; app statuses are retained.',
        'Actual original retained recovery entry execution rc0 after full128.'
    ]):e['supports']=text
    return {
       'family':'JNI / candidate window geometry','capability':'R6 BLASTBufferQueue.nativeUpdate: successful dedicated SurfaceView child requested geometry, main-window compatibility geometry (not frozen)',
       'method':'Only BBQ_nativeUpdate: use requested width/height after oh_rs_get_child_surface_window successfully resolves the dedicated child; main/ViewRoot and failed-child fallback retain panel1200x1920. SurfaceView name alone is insufficient. Other three geometry paths, lazy/STAGE0/M1/SQLite and failure returns remain unchanged. Not a whole BLAST family implementation.',
       'android_source':'unknown; source-only. JNI registration/source comments do not establish an Android support range.',
       'oh_tested':'OpenHarmony6.1.0.31 only, actual5ea. Boat b711 and popup db429 groups remain distinct. Fixed128 scoped startup nonregression accepted; original947 restored. Other OH versions unknown.',
       'abi':'aarch64/arm64-v8a; original787 exports, SQLite and three-consumer static ABI guards passed; no claim for all Android ABIs.',
       'route_generation':'5ea U13/R6 bounded candidate, c208 source/f28 runtime, original337 identity and7binds; fixed128 acceptance is scoped to startup/screenshots, not V2 sealing.',
       'validations':vals,'evidence':ev,'gaps':[
           'API not frozen: frozen_ids stays empty; source/runtime archive does not confer API registration.',
           'Fixed128 startup nonregression accepted with existing limitations; not general functionality. Original raw app statuses and failures remain. Protected61b unseal and final sameboard acceptance still pending.',
           'Android runtime version, API support range and APK targetSdk remain unknown/source-only.',
           'Popup db429 and functional Boat b711 evidence retain their own boot boundaries; earlier incomplete Boat attempt is not retroactively accepted.',
           'Main ViewRoot policy changes relative to947; tested groups do not establish every popup/native method.',
           'Historical transaction stubs and mixed-surface gaps remain in their original314 records.',
           'sNotz/Toodoo differences reproduce on original947 current data across boots. No single-variable causal experiment; note-store integrity and filter/edit/save usability remain untested.'
       ]}
