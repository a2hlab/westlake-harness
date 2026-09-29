"""Run via dockbuild (a2hlab-b5-java image): B7 helper merge into 5cd's accepted runtime JAR.

Same method as B5 (alias-entry/build.py): compile the helpers, baksmali the pinned
baseline, add the helper classes, inject exactly one call, reassemble, and prove
that no other existing class changed.
"""
from pathlib import Path
import hashlib, json, re, shutil, subprocess, sys, zipfile

ROOT = Path(__file__).resolve().parents[2]
REPORT = Path(__file__).resolve().parent
OUT = Path('/home/zhaoyue/a2hlab/build-runs/20260929-oh6.1.0.31-b7')
INPUT = OUT / 'inputs'
BUILD = OUT / ('build-' + (sys.argv[1] if len(sys.argv) > 1 else 'r1'))
BUILD.mkdir(exist_ok=False)
# pr03: 5cd before the #63 generation switch; zigzag: the 5ea/ZigZag candidate generation
# (strict-20260809T160651Z-21101), which already ships User/Storage/Display projection proxies.
BASELINES = {'pr03': ('baseline.jar', '06141543bec26c5036931d8d2d71b0efaa45d5ffd73434557d165cd42672be0d'),
             'zigzag': ('baseline-9161b507.jar', '9161b50756d3ffdfb2a8908ea7ec13f908214688321b2785365977ac40b28dea'),
             # B5 JAR = zigzag + B5 alias helpers and call (alias-entry/build-result.json).
             'b5': ('baseline-250958dc.jar', '250958dc3f133b67fb38c5da3caf81714fd6958e2247556e327d917b1f0d3146')}
BASE_NAME = sys.argv[2] if len(sys.argv) > 2 else 'pr03'
BASE_JAR = INPUT / BASELINES[BASE_NAME][0]
BASELINE = BASELINES[BASE_NAME][1]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(BASE_JAR) == BASELINE
cp = ':'.join(str(p) for p in sorted(INPUT.glob('*.jar')) if p.name not in ('android.jar', 'd8.jar') and not p.name.startswith('baseline'))


def run(args):
    subprocess.run([str(x) for x in args], check=True)


classes = BUILD / 'classes'; classes.mkdir()
dex = BUILD / 'helper-dex'; dex.mkdir()
src = ROOT / 'bms/src/adapter/framework/activity/java'
helpers_src = [src / 'B7BindFixes.java', src / 'UserManagerProjectionProxy.java',
               # B5 alias fix, verbatim sources (alias-entry/build.py): 5cd never carried the
               # B5 JAR (built on the ZigZag-generation 9161b507), so it rides on this overlay.
               src / 'LaunchActivityAliasProjection.java', src / 'BinaryAndroidManifestOrientation.java',
               # B8 (#65) items 1-2: 00.Workspace ManifestComponentProjection (verbatim) + driver/hook.
               src / 'ManifestComponentProjection.java', src / 'SelfComponentFallback.java',
               # B8 (#65) items 6/7/15: Westlake LocalServiceBinders + CompatChangeTable.
               src / 'LocalServiceBinders.java', src / 'CompatChangeTable.java', src / 'B8BindExtras.java',
               # B8 (#65) r8b: Java manifest parse feeding the isomorphic JSON back through
               # AppSchedulerBridge's own path when nativeParseManifestJson is missing (6cb40cd6).
               src / 'ManifestJsonFallback.java',
               # B8 (#82) r15: runtime-JAR proxies over the BCP IWindowSession (addToDisplay + CLAMP48)
               # and IActivityManager (in-app bindService), installed from B7BindFixes at bind.
               src / 'WindowSessionProxy.java', src / 'ActivityManagerBindProxy.java',
               # r17 (cc-wiki): own-uid getPackagesForUid/getNameForUid so StorageManager.getVolumeList
               # asks the child-local mount binder instead of returning empty (amaze AppConfig <clinit>).
               src / 'SelfUidPackages.java',
               # r17d (#media_session): verbatim Westlake local ISessionManager so a MediaSessionCompat
               # service (noice/musicplayer) does not NPE on a null MediaSessionManager.
               src / 'WlMediaSession.java']
run(['javac', '--release', '8', '-cp', INPUT / 'android.jar', '-d', classes, *helpers_src])
# r16 (#90): cc-wiki's OnlineConnectivityManager compiles against the Westlake android.net sources
# (ConnectivityManager/Network/NetworkInfo/NetworkCapabilities/NetworkRequest, which expose the
# public ctors the compile android.jar hides), and ONLY its adapter.activity.OnlineConnectivityManager*
# classes go into the dex -- android.net.* resolve to the boot android at runtime. B7BindFixes calls
# install() reflectively so it needs no compile-time reference.
wl_net_dir = REPORT / 'onlinecm-deps/android/net'
wl_net = [wl_net_dir / (c + '.java') for c in
          ('ConnectivityManager', 'Network', 'NetworkInfo', 'NetworkCapabilities', 'NetworkRequest')]
online_classes = BUILD / 'online-classes'; online_classes.mkdir()
run(['javac', '-source', '8', '-target', '8', '-bootclasspath', INPUT / 'android.jar',
     '-cp', INPUT / 'android.jar', '-d', online_classes, '-nowarn',
     src / 'OnlineConnectivityManager.java', *wl_net])
online_kept = sorted((online_classes / 'adapter' / 'activity').glob('OnlineConnectivityManager*.class'))
assert online_kept, 'no OnlineConnectivityManager classes compiled'
for p in online_kept:
    shutil.copyfile(p, classes / 'adapter/activity' / p.name)
# r17 (#93): Westlake HTTPS/TLS Java side, compiled against android.jar as BOOTCLASSPATH so the
# SSLSocket/SSLSession/X509ExtendedTrustManager abstract sets match the platform exactly (a
# --release 8 pass binds the JDK's abstract set instead -> AbstractMethodError at class load). Chain:
# adapter.security.{OhTrustBridge, OhTrustManagerFactorySpi, OhSystemTrustManager, OhPeerCertificates,
# WestlakeTlsInstall} + adapter.compat.{WestlakeSecureRandomSpi, WestlakeSSLSocket, WestlakeSSLSession}.
# B7BindFixes calls adapter.security.WestlakeTlsInstall.install() reflectively (no compile-time ref).
tls_src = [src / 'WestlakeTlsInstall.java', src / 'OhTrustBridge.java',
           src / 'OhTrustManagerFactorySpi.java', src / 'OhSystemTrustManager.java',
           src / 'OhPeerCertificates.java', src / 'WestlakeSecureRandomSpi.java',
           src / 'WestlakeSSLSocket.java', src / 'WestlakeSSLSession.java',
           # r17d (#93): default-HTTPS factory chain over WestlakeSSLSocket, gated on the native
           # self-test (WestlakeTlsInstall). android.net/ssl types -> android.jar bootclasspath pass.
           src / 'WestlakeSSLSocketFactory.java', src / 'WestlakeSSLContextSpi.java',
           # r17b (#tagsoup): tagsoup-free Html.fromHtml replacement (android.text.* -> needs the
           # android.jar bootclasspath pass), called by oc-t4's libwestlake_html_compat.so.
           src / 'HtmlCompatFallback.java']
tls_classes = BUILD / 'tls-classes'; tls_classes.mkdir()
run(['javac', '-source', '8', '-target', '8', '-bootclasspath', INPUT / 'android.jar',
     '-cp', INPUT / 'android.jar', '-d', tls_classes, '-nowarn', *tls_src])
tls_kept = sorted(tls_classes.rglob('*.class'))
assert tls_kept, 'no TLS classes compiled'
for p in tls_kept:
    dest = classes / p.relative_to(tls_classes)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(p, dest)
run(['java', '-cp', INPUT / 'd8.jar', 'com.android.tools.r8.D8', '--release', '--min-api', '22',
     '--lib', INPUT / 'android.jar', '--output', dex, *classes.rglob('*.class')])
with zipfile.ZipFile(BASE_JAR) as z:
    (BUILD / 'baseline.dex').write_bytes(z.read('classes.dex'))
smali, helpers, post = BUILD / 'smali', BUILD / 'helper-smali', BUILD / 'postflight'
run(['java', '-cp', cp, 'org.jf.baksmali.Main', 'disassemble', BUILD / 'baseline.dex', '-o', smali])
original = {str(p.relative_to(smali)): p.read_bytes() for p in smali.rglob('*.smali')}
run(['java', '-cp', cp, 'org.jf.baksmali.Main', 'disassemble', dex / 'classes.dex', '-o', helpers])
# A helper the baseline already ships (UserManagerProjectionProxy on zigzag) is compiled only so
# B7BindFixes links against it; the baseline's own class is kept.
ALREADY_SHIPPED = {'adapter/activity/UserManagerProjectionProxy.smali',
                   'adapter/activity/UserManagerProjectionProxy$UserBinder.smali',
                   'adapter/activity/LaunchActivityAliasProjection.smali',
                   'adapter/activity/BinaryAndroidManifestOrientation.smali',
                   'adapter/activity/BinaryAndroidManifestOrientation$StringPool.smali'}
B5_SHIPPED = 'adapter/activity/LaunchActivityAliasProjection.smali' in original
for p in helpers.rglob('*.smali'):
    dest = smali / p.relative_to(helpers)
    if str(p.relative_to(helpers)) in original:
        assert str(p.relative_to(helpers)) in ALREADY_SHIPPED, p
        continue
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(p, dest)

# ensureBindApplication: right after "[B43-BIND] resolved ApplicationInfo ..." is printed,
# v10 holds the ApplicationInfo that becomes AppBindData.appInfo.
scheduler = smali / 'adapter/activity/AppSchedulerBridge.smali'
text = scheduler.read_text()
start = text.index('.method private static declared-synchronized ensureBindApplication(')
end = text.index('.end method', start)
body = text[start:end]
anchor = ('invoke-virtual {v8, v0}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V\n\n'
          '    .line 201\n')
assert body.count(anchor) == 1, body.count(anchor)
assert 'iget-object v4, v10, Landroid/content/pm/ApplicationInfo;->nativeLibraryDir' in body
call = ('invoke-virtual {v8, v0}, Ljava/io/PrintStream;->println(Ljava/lang/String;)V\n\n'
        '    invoke-static {v10}, Ladapter/activity/B7BindFixes;->apply(Landroid/content/pm/ApplicationInfo;)V\n\n'
        '    .line 201\n')
text = text[:start] + body.replace(anchor, call) + text[end:]
# B5: exactly one call after buildActivityInfoFromAbility, same pattern as alias-entry/build.py.
pattern = r'(?m)(^    invoke-static[^\n]*->buildActivityInfoFromAbility\([^\n]+\n\s*\n?    move-result-object ([vp]\d+))'
hits = list(re.finditer(pattern, text)); assert len(hits) == 1, len(hits)
h = hits[0]
if B5_SHIPPED:
    assert text.count('LaunchActivityAliasProjection;->apply(') == 1, 'B5 baseline must already call the alias fix once'
else:
    text = (text[:h.end()] + '\n\n    invoke-static {' + h[2] +
            '}, Ladapter/activity/LaunchActivityAliasProjection;->apply(Landroid/content/pm/ActivityInfo;)V' + text[h.end():])
# B8 item 3: right after setField(data, "providers", buildProvidersFromManifest(...)).
prov = re.compile(r'(    const-string (v\d+), "providers"\n\n'
                  r'    invoke-static \{(v\d+), \2, v\d+\}, Ladapter/activity/AppSchedulerBridge;->setField'
                  r'\(Ljava/lang/Object;Ljava/lang/String;Ljava/lang/Object;\)V\n)')
phits = prov.findall(text); assert len(phits) == 1, len(phits)
text = prov.sub(lambda m: m.group(1) + '\n    invoke-static {' + m.group(3) +
                '}, Ladapter/activity/B8BindExtras;->afterProviders(Ljava/lang/Object;)V\n', text)
# B8 item 15: right after setField(data, "disabledCompatChanges", new long[0]).
compat = re.compile(r'(    const-string (v\d+), "disabledCompatChanges"\n\n(?:    [^\n]+\n\n){0,3}?'
                    r'    invoke-static \{(v\d+), \2, v\d+\}, Ladapter/activity/AppSchedulerBridge;->setField'
                    r'\(Ljava/lang/Object;Ljava/lang/String;Ljava/lang/Object;\)V\n)')
chits = compat.findall(text); assert len(chits) == 1, len(chits)
text = compat.sub(lambda m: m.group(1) + '\n    invoke-static {' + m.group(3) +
                  '}, Ladapter/activity/B8BindExtras;->afterBindData(Ljava/lang/Object;)V\n', text)
# B8 #73/r14: replace the native nativeParseManifestJson call at EVERY call site
# (ensureBindApplication AND the WL-THEME-SYNC appTheme path) with ManifestJsonFallback.parseManifestJson.
# The bridge on 6cb40cd6 and the v3a 846 (84695d62) bridge export neither, so the native call throws
# UnsatisfiedLinkError at both; the Java replacement has the same (String)->String signature, never
# throws, and returns the isomorphic JSON so providers + className/theme + the WL-THEME-SYNC appTheme
# all get their data. (On v3a the ZigZag control has its westlake libs, so the extra manifest parse on
# the SLA thread is harmless -- the earlier "window type 2" was a missing-lib environmental issue.)
npm = re.compile(r'invoke-static \{(v\d+)\}, Ladapter/activity/AppSchedulerBridge;'
                 r'->nativeParseManifestJson\(Ljava/lang/String;\)Ljava/lang/String;')
nhits = npm.findall(text); assert len(nhits) >= 2, nhits
text = npm.sub(lambda m: 'invoke-static {' + m.group(1) + '}, Ladapter/activity/ManifestJsonFallback;'
               '->parseManifestJson(Ljava/lang/String;)Ljava/lang/String;', text)
# B8 #70 wall 1 (per-activity theme): in buildActivityInfoFromAbility, resolve the launching
# activity's own manifest theme before the (single) return. ScheduleLaunchAbility runs before
# bindApplication enriches appInfo.theme, so OH's abilityJson leaves ActivityInfo.theme 0 and the
# activity reaches AppCompat with no theme. resolveActivityTheme reads the theme from the APK
# manifest (activity android:theme, else application theme) and fills it only when still 0.
mkey = 'buildActivityInfoFromAbility(Ljava/lang/String;Ljava/lang/String;Landroid/content/pm/ApplicationInfo;Ljava/lang/String;)'
mstart = text.index('.method private static ' + mkey)
mend = text.index('.end method', mstart)
mbody = text[mstart:mend]
rets = list(re.finditer(r'\n    return-object (v\d+)\n', mbody))
assert len(rets) >= 1, 'buildActivityInfoFromAbility return not found'
last = rets[-1]; areg = last.group(1)
inject = ('\n    invoke-static {' + areg + '}, Ladapter/activity/ManifestJsonFallback;'
          '->resolveActivityTheme(Landroid/content/pm/ActivityInfo;)V\n'
          '\n    return-object ' + areg + '\n')
mbody = mbody[:last.start()] + inject + mbody[last.end():]
text = text[:mstart] + mbody + text[mend:]
scheduler.write_text(text)

# B8: in PackageManagerProjectionProxy.invoke (zigzag/B5 baselines), pass the delegate's answer
# through SelfComponentFallback right after the delegate call, while p2=Method and p3=args are intact.
pm_proxy = smali / 'adapter/activity/PackageManagerProjectionProxy.smali'
if pm_proxy.exists():
    ptext = pm_proxy.read_text()
    ps = ptext.index('.method public invoke(Ljava/lang/Object;Ljava/lang/reflect/Method;[Ljava/lang/Object;)Ljava/lang/Object;')
    pe = ptext.index('.end method', ps)
    pbody = ptext[ps:pe]
    hook = re.compile(r'(    invoke-virtual \{p2, p1, p3\}, Ljava/lang/reflect/Method;->invoke\(Ljava/lang/Object;\[Ljava/lang/Object;\)Ljava/lang/Object;\n\n    move-result-object p1\n    :try_end_\w+\n    \.catch Ljava/lang/reflect/InvocationTargetException; \{:try_start_\w+ \.\. :try_end_\w+\} :catch_\w+\n)')
    hits = hook.findall(pbody); assert len(hits) == 1, len(hits)
    pbody = hook.sub(lambda m: m.group(1) + '\n    invoke-static {p2, p3, p1}, Ladapter/activity/SelfComponentFallback;->apply('
                     'Ljava/lang/reflect/Method;[Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;\n\n'
                     '    move-result-object p1\n', pbody)
    pm_proxy.write_text(ptext[:ps] + pbody + ptext[pe:])

run(['java', '-cp', cp, 'org.jf.smali.Main', 'assemble', smali, '-o', BUILD / 'classes.dex'])
run(['java', '-cp', cp, 'org.jf.baksmali.Main', 'disassemble', BUILD / 'classes.dex', '-o', post])
# smali drops an explicit "= false" static-boolean initializer (the encoded default);
# that is the only round-trip difference tolerated.
norm = lambda b: re.sub(rb'(?m)^(\.field [^\n]*:Z) = false$', rb'\1', b)
changed = [n for n, d in original.items()
           if not (post / n).exists() or norm((post / n).read_bytes()) != norm(d)]
expected = ['adapter/activity/AppSchedulerBridge.smali'] + (
    ['adapter/activity/PackageManagerProjectionProxy.smali'] if pm_proxy.exists() else [])
assert sorted(changed) == sorted(expected), changed
post_scheduler = (post / 'adapter/activity/AppSchedulerBridge.smali').read_text()
assert post_scheduler.count('B7BindFixes;->apply(') == 1
assert post_scheduler.count('LaunchActivityAliasProjection;->apply(') == 1
assert post_scheduler.count('B8BindExtras;->afterBindData(') == 1
assert post_scheduler.count('B8BindExtras;->afterProviders(') == 1
assert post_scheduler.count('ManifestJsonFallback;->parseManifestJson(') >= 2
assert post_scheduler.count('AppSchedulerBridge;->nativeParseManifestJson(') == 0
assert post_scheduler.count('ManifestJsonFallback;->resolveActivityTheme(') == 1
output = BUILD / 'oh-adapter-runtime.jar'
with zipfile.ZipFile(BASE_JAR) as source, zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as dest:
    for item in source.infolist():
        dest.writestr(item, (BUILD / 'classes.dex').read_bytes() if item.filename == 'classes.dex'
                      else source.read(item.filename))
result = {
    'baseline': BASE_NAME,
    'baseline_sha256': BASELINE,
    'output': str(output),
    'output_sha256': sha(output),
    'changed_existing_classes': changed,
    'added_classes': sorted(str(p.relative_to(post)) for p in post.rglob('*.smali')
                            if str(p.relative_to(post)) not in original),
    'sources': {str(p.relative_to(ROOT)): sha(p) for p in helpers_src + tls_src},
    'inputs': {p.name: sha(p) for p in sorted(INPUT.glob('*.jar'))},
}
(REPORT / ('build-result-' + BUILD.name[len('build-'):] + '.json')).write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
