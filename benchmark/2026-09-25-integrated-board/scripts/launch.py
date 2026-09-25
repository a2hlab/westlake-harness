import json, subprocess, pathlib, sys, time
A=pathlib.Path("/home/dspfac/a2hlab/source-closure/verify")
H="/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh"
S="5cd1e3dd00000000000000000923012c"
R=pathlib.Path.home()/"a2hlab/board"/S/"verify32"
run=sys.argv[1]
app=sys.argv[2] if len(sys.argv)>2 else "toutiao"
framework=R/"framework/device-report.json"
cmd=["python3",str(A/"out-touch21/probe-local/tools/probe_source_app.py"),
"--workspace",str(A),"--westlake-source",str(A/"westlake-all0925"),
"--framework-report",str(framework),"--app-input",str(pathlib.Path.home()/"a2hlab/app-inputs"/app),
"--app",app,"--hdc",H,"--serial",S,"--out",str(R/run),
"--host-build",str(A/"out/signed-host"),"--webview-input",str(A/"out/webview-input-source"),
"--source-webview-build",str(A/"out-all0925/webview-candidate"),
 "--runtime-env","WL_TOUCH_TRACE=1"]
if app=="toutiao": cmd += ["--android-native-target","libvision_core.so","--android-native-target","libc++_shared.so","--android-native-target","libsscronet.so","--android-native-net-target","libsscronet.so"]

if run.startswith("fd"): cmd += ["--runtime-env","WL_TOUCH_FD_MAIN=1"]
with (R/(run+".log")).open("w") as f:
 subprocess.run(cmd,cwd=pathlib.Path.home()/"a2hlab/manifest",stdout=f,stderr=subprocess.STDOUT,check=True)
d=json.loads((R/run/"device-report.json").read_text())
print("READY",run,d["child"],flush=True)
