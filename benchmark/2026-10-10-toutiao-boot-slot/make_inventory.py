"""Record local donor hashes, never query a device."""
import json,tarfile,hashlib
from pathlib import Path
D=Path(__file__).parent
rt='/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d';stage='/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d'
inputs=json.loads((D/'.artifacts/payload-v2/placement.json').read_text())['source_inputs'];rows=[]
roles={'source-host.hap':('imehost OH foreground host','Installed HAP/data persists; install once, never per boot.','Real desktop tap must produce imehost0; require UID 20010053.'),'tt-rt.tar':('Route B ART/adapter/spawner/private runtime','Extracted /data tree persists; private binds, sockets and processes do not.','Donor source_app_namespace after the current host window exists.'),'tt-stage.tar':('namespace helper and host_spawn request payload','Extracted stage directory on /data persists.','spawn.sh sends request.bin to the private A2HSource socket.'),'tt-wd.tar':('validated selfheal watchdog and screen classifier','operator45 scripts persist; PID/birth must be rediscovered.','Start existing watchdog and keeper once after a real foreground tap.')}
for r in inputs:
 role,persist,action=roles[r['input']];rows.append(dict(component=r['input'],sha256=r['sha256'],bytes=r['size'],source='$HOME/a2hlab-provision/ttbundle/'+r['input'],board=r['board_archive'],role=role,persistence=persist,boot_action=action,provenance_commit='0cd47f8b6b; 54dcb31125'))
for archive,names,base in [('tt-rt.tar',['./appspawn-x','./run.sh','./prepare_jit50.sh'],rt),('tt-stage.tar',['source_app_namespace','host_spawn','request.bin'],stage)]:
 with tarfile.open(Path.home()/'a2hlab-provision/ttbundle'/archive) as t:
  for name in names:
   m=t.getmember(name);data=t.extractfile(m).read();rows.append(dict(component=Path(name).name,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),source=archive+':'+name,board=base+'/'+Path(name).name,role='unchanged donor runtime executable/script/request',persistence='/data retained; private mounts/processes not retained',boot_action='donor launch chain; appspawn-x copied to asx-spawner with identical bytes, run.sh rename patch only'))
for p in (D/'payload/scripts').glob('*.sh'):
 rows.append(dict(component=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size,source=str(p.relative_to(D)),board='/data/westlake-demo/toutiao/scripts/'+p.name,role='inactive prepared boot-slot script',persistence='one-time approved placement required',boot_action='see README; PID/birth/UID/executable/private-root guard'))
(D/'inventory.json').write_text(json.dumps({'schema':'route-b-boot-inventory/v1','execution_enabled':False,'board':'61b0657200000000000000000324012c','members':rows,'optional_aot':'Not an input; preserve the proved non-AOT Route B recipe.'},indent=2)+'\n')
