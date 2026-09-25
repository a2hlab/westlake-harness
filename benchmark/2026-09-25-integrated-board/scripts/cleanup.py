import pathlib,json,subprocess,re,hashlib
S="5cd1e3dd00000000000000000923012c";root=pathlib.Path.home()/"a2hlab/board"/S;o=root/"verify32/cleanup";o.mkdir(exist_ok=True)
h=["/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh","-t",S]
def dev(c):return subprocess.check_output(h+["shell",c],timeout=40).replace(b"\r",b"")
ps=dev("ps -A -o PID,PPID,STAT,NAME");(o/"ps-before.txt").write_bytes(ps)
reports=[]
for f in root.rglob("device-report.json"):
 try:d=json.loads(f.read_text())
 except:continue
 if d.get("child") and d.get("runtime"):reports.append((f,d))
# Archive available original child streams before terminating old test parents.
arch=[]
for f,d in reports:
 if d.get("parent") not in [int(l.split()[0]) for l in ps.decode().splitlines()[1:] if "appspawn-x" in l]:continue
 remote=d["runtime"]+"/private-tmp/adapter_child_"+str(d["child"])+".stderr"
 local=f.parent/"child.stderr"
 if local.is_file() and local.stat().st_size: data=local.read_bytes()
 else:
  recv="old-"+str(d["child"])+".stderr"
  subprocess.run(h+["file","recv",remote,recv],cwd=o,timeout=120,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  data=(o/recv).read_bytes() if (o/recv).is_file() else b""
 if data:
  name=str(d["child"])+"-"+hashlib.sha256(str(f).encode()).hexdigest()[:10]+".stderr";(o/name).write_bytes(data);arch.append({"report":str(f),"remote":remote,"local":name,"sha256":hashlib.sha256(data).hexdigest()})
(o/"archives.json").write_text(json.dumps(arch,indent=2))
killed=[]
for l in ps.decode().splitlines()[1:]:
 fields=l.split()
 if len(fields)<4 or fields[-1] not in ["appspawn-x","touchfwd"]:continue
 pid=int(fields[0]);exe=dev(f"readlink /proc/{pid}/exe").decode().strip();stat=dev(f"cat /proc/{pid}/stat").decode()
 if not exe.startswith(("/data/local/tmp/a2hlab-","/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-")):continue
 now=dev(f"cat /proc/{pid}/stat").decode()
 if ") " in stat and ") " in now and stat.rsplit(") ",1)[1].split()[19]==now.rsplit(") ",1)[1].split()[19]:dev(f"kill -9 {pid}");killed.append({"pid":pid,"exe":exe})
# Remove only nine #23 runs whose raw child evidence was previously committed.
removed=[]
for f,d in reports:
 if f.parent.parent!=root/"applib23" or not f.parent.name.startswith("bounds-"):continue
 if not (f.parent/"child.stderr").is_file():continue
 for key in ["stage","runtime"]:
  path=d.get(key,"")
  if re.fullmatch(r"/data/local/tmp/a2hlab-app-[0-9a-f]+",path) or re.fullmatch(r"/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-[0-9a-f]+",path):
   dev("rm -rf -- "+path);removed.append({"path":path,"archived_stderr":str(f.parent/"child.stderr")})
(o/"cleanup.json").write_text(json.dumps({"killed":killed,"removed":removed},indent=2));(o/"after.txt").write_bytes(dev("df -h /data; ps -A -o PID,PPID,STAT,NAME"));print("archived",len(arch),"killed",len(killed),"removed",len(removed))
