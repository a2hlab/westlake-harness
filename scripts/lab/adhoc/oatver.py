import re,sys,os
for p in sys.argv[1:]:
    try: b=open(p,'rb').read()
    except Exception as e: print(p,'ERR',e); continue
    vs=sorted(set(m.group(1).decode() for m in re.finditer(rb'oat\n(\d{3})\x00',b)))
    print(f"{os.path.basename(p):28s} {vs}")
