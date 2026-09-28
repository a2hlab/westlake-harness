"""Build a NEW isolated test APK; never rewrite any campaign input APK."""
from pathlib import Path
import subprocess,os,zipfile,hashlib,json
root=Path(__file__).resolve().parent
out=Path('/Users/zhaoyue/orca/workspaces/westlake-bms-suite/var/state/b5-negative');out.mkdir(exist_ok=False)
vm=Path('/home/zhaoyue/a2hlab/build-runs/20260928-oh6.1.0.31-b5')
jdk=Path('/Applications/DevEco-Studio.app/Contents/jbr/Contents/Home/bin')
sdk=Path('/Users/zhaoyue/Library/Android/sdk')
def run(args,**kw):subprocess.run([str(x) for x in args],check=True,**kw)
script=f'''set -eu
mkdir -p {vm}/negative/classes {vm}/negative/dex
javac --release 8 -cp {vm}/inputs/android.jar -d {vm}/negative/classes {root}/PresentActivity.java
java -cp {vm}/inputs/d8.jar com.android.tools.r8.D8 --release --min-api 22 --lib {vm}/inputs/android.jar --output {vm}/negative/dex {vm}/negative/classes/org/a2hlab/b5aliasnegative/PresentActivity.class
'''
(out/'compile.sh').write_text(script)
run(['/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/dockbuild.sh','run','-n','b5-negative-build','--','bash',out/'compile.sh'],env=dict(os.environ,DOCKBUILD_IMAGE='a2hlab-b5-java:24.04'))
run([sdk/'build-tools/36.1.0/aapt2','link','--manifest',root/'AndroidManifest.xml','-I',sdk/'platforms/android-36/android.jar','-o',out/'unsigned.apk'])
with (out/'classes.dex').open('wb') as f:run(['orb','-m','a2hlab','cat',vm/'negative/dex/classes.dex'],stdout=f)
with zipfile.ZipFile(out/'unsigned.apk','a',zipfile.ZIP_DEFLATED) as z:z.write(out/'classes.dex','classes.dex')
# Disposable test signing identity, outside the public repository.
run([jdk/'keytool','-genkeypair','-keystore',out/'debug.jks','-storepass','android','-keypass','android','-alias','b5-test','-dname','CN=B5 Test','-keyalg','RSA','-validity','2'])
run([jdk/'java','-jar',sdk/'build-tools/36.1.0/lib/apksigner.jar','sign','--ks',out/'debug.jks','--ks-key-alias','b5-test','--ks-pass','pass:android','--key-pass','pass:android','--out',out/'negative.apk',out/'unsigned.apk'])
run([jdk/'java','-jar',sdk/'build-tools/36.1.0/lib/apksigner.jar','verify',out/'negative.apk'])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(root/'fixture.json').write_text(json.dumps({'apk':str(out/'negative.apk'),'sha256':sha(out/'negative.apk'),'dex_sha256':sha(out/'classes.dex'),'package':'org.a2hlab.b5aliasnegative','alias':'org.a2hlab.b5aliasnegative.LauncherAlias','target':'org.a2hlab.b5aliasnegative.MissingTarget','only_dex_class':'org.a2hlab.b5aliasnegative.PresentActivity','campaign_apks_modified':False},indent=2)+'\n')
