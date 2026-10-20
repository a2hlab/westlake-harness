#!/usr/bin/env python3
"""Compile actual EGL state machine, with explicit host provider/loader seams."""
import hashlib,json,os,subprocess,tempfile
from pathlib import Path
p=Path(__file__).resolve().parent
cases=['same_image_two_displays','success','full','duplicate','wrong_display','destroy_retry','create_fail','display_absent','display_multiple','foreign','fence','provider_refused','native_fail','target_refused']
out=Path(os.environ.get('T23_CHECK_OUT',Path.home()/'.local/share/westlake/t23-egl-host'))
out.mkdir(parents=True,exist_ok=True)
run=Path(tempfile.mkdtemp(prefix='run-',dir=out));commands=[]
def call(name,argv):
 (run/(name+'.argv.json')).write_text(json.dumps(list(map(str,argv)),indent=2)+'\n')
 with (run/(name+'.stdout')).open('wb') as so,(run/(name+'.stderr')).open('wb') as se:
  try:rc=subprocess.run(list(map(str,argv)),stdout=so,stderr=se,timeout=30).returncode
  except subprocess.TimeoutExpired:rc=124
 (run/(name+'.rc')).write_text(str(rc)+'\n');commands.append({'name':name,'rc':rc});assert rc==0,(name,rc)
call('compile',['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-pthread','-DR23_SLOTS=2',p/'test_egl.c','-o',run/'test'])
for case in cases:call(case,[run/'test',case])
platform_cases=['success','scope_drift','wrong_owner_offset','unreadable_slot','mixed_provider','missing_destroy','wrong_path','mixed_egl','foreign_proc']
call('compile-platform',['cc','-std=c11','-O2','-Wall','-Wextra','-Werror','-pthread',p/'test_platform.c','-o',run/'test-platform'])
for case in platform_cases:call('platform-'+case,[run/'test-platform',case])
r={'status':'HOST_STATE_MACHINE_PASS','scope':'actual egl_import.c; provider functions and caller/display identities are seams, not device evidence','cases':cases,'platform_cases':platform_cases,'commands':commands,'sources':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in [p/'egl_import.c',p/'egl_import.h',p/'test_egl.c',p/'test_platform.c',p/'platform.c',p/'exact_binding.h',Path(__file__)]}}
(run/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':len(cases)+len(platform_cases),'raw':str(run),'device_calls':0}))
