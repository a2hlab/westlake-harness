import pathlib, subprocess, sys, json, time, re
o=pathlib.Path(__file__).resolve().parent
name,app=sys.argv[1:3]
r=pathlib.Path.home()/"a2hlab/board/5cd1e3dd00000000000000000923012c/images30cx"/name
def call(script,*args):
 return subprocess.run(["python3",str(o/script),name,*args],check=True)
subprocess.run(["python3",str(o/"launch.py"),name,app],check=True)
d=json.loads((r/"device-report.json").read_text())
call("drive.py","shell","aa start -b org.westlake.imehost -a EntryAbility")
time.sleep(4)
call("drive.py","shell",f"kill -3 {d['child']}")
time.sleep(2)
call("collect.py")
s=(r/"child.stderr").read_text(errors="replace")
m=re.findall(r'"Thread-2"[^\n]*\n.*?\| sysTid=(\d+)',s,re.S)
if not m: raise RuntimeError("UI tid missing")
(r/"ui-tid.txt").write_text(m[-1])
call("drive.py","vt")
call("drive.py","shot","before")
call("drive.py","shell","echo i "+("1119 1840" if app=="noice" else "1149 1867")+" > /data/local/tmp/noice_tap")
time.sleep(3)
call("drive.py","vt")
call("drive.py","shot","after")
call("observe.py","65")
call("drive.py","vt")
call("drive.py","shot","after-settled")
call("finish.py")
