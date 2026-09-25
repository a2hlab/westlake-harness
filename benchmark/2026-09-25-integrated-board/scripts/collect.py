import json,pathlib,subprocess,sys
r=pathlib.Path.home()/"a2hlab/board/5cd1e3dd00000000000000000923012c/verify32"/sys.argv[1]
d=json.loads((r/"device-report.json").read_text())
h="/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh"
subprocess.run([h,"-t","5cd1e3dd00000000000000000923012c","file","recv",d["runtime"]+"/private-tmp/adapter_child_"+str(d["child"])+".stderr","child.stderr"],cwd=r,check=True)
