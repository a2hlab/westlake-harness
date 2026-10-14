#!/usr/bin/env python3
"""Offline exact-JAR transform; raw commands/stdout/stderr recorded at execution time."""
import argparse, hashlib, json, os, subprocess, zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
EXPECTED='ea5d8b277f1207c928d289196876ad69505d73ab586815daccbda7080169523e'
TOOLS=['dexlib2-2.5.2.jar','guava-31.1-jre.jar','failureaccess-1.0.1.jar','baksmali-2.5.2.jar','util-2.5.2.jar','jcommander-1.78.jar']
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def portable(s):
    w=os.environ.get('WORKSPACES')
    return str(s).replace(w,'$WORKSPACES') if w else str(s)
def build(inp,out,tools,java,javac):
    if sha(inp)!=EXPECTED: raise ValueError('REFUSE input SHA')
    lock=json.loads((HERE/'tools.lock.json').read_text())
    for name in TOOLS:
        if sha(tools/name)!=lock[name]: raise ValueError('REFUSE tool '+name)
    out.mkdir(parents=True,exist_ok=False)
    cp=os.pathsep.join(str(tools/n) for n in TOOLS)
    records=[]
    def run(name,argv):
        with (out/(name+'.stdout')).open('wb') as so,(out/(name+'.stderr')).open('wb') as se:
            p=subprocess.run(list(map(str,argv)),stdout=so,stderr=se)
        r={'argv':[portable(x) for x in argv],'rc':p.returncode,'stdout_sha256':sha(out/(name+'.stdout')),'stderr_sha256':sha(out/(name+'.stderr'))}
        (out/(name+'.json')).write_text(json.dumps(r,indent=2)+'\n');records.append(r)
        if p.returncode: raise RuntimeError('FAILED '+name)
    classes=out/'classes';classes.mkdir()
    with zipfile.ZipFile(inp) as z:
        if z.namelist()!=['classes.dex']: raise ValueError('REFUSE JAR members')
        (out/'before.dex').write_bytes(z.read('classes.dex'))
    run('01-javac',[javac,'-cp',cp,'-d',classes,HERE/'BackCallbackPatch.java'])
    run('02-transform',[java,'-cp',str(classes)+os.pathsep+cp,'BackCallbackPatch',out/'before.dex',out/'after.dex'])
    for name in ['before','after']:
        run('03-'+name,[java,'-cp',cp,'org.jf.baksmali.Main','disassemble',out/(name+'.dex'),'-o',out/name])
    before={str(p.relative_to(out/'before')):p.read_bytes() for p in (out/'before').rglob('*.smali')}
    after={str(p.relative_to(out/'after')):p.read_bytes() for p in (out/'after').rglob('*.smali')}
    target='adapter/activity/ActivityClientControllerAdapter.smali'
    changed=[k for k in before if before[k]!=after.get(k)]
    if set(before)!=set(after) or changed!=[target]: raise ValueError('REFUSE non-target class delta '+str(changed))
    import re,difflib
    pattern=r'(?ms)^\.method public onBackPressed\(Landroid/os/IBinder;Landroid/app/IRequestFinishCallback;\)V\n.*?^\.end method'
    bs=before[target].decode();as_=after[target].decode()
    if len(re.findall(pattern,bs))!=1 or re.sub(pattern,'<TARGET>',bs)!=re.sub(pattern,'<TARGET>',as_): raise ValueError('REFUSE other method delta')
    (out/'method.diff').write_text(''.join(difflib.unified_diff(bs.splitlines(True),as_.splitlines(True),fromfile='exact-ea5d',tofile='BACK51')))
    jar=out/'adapter-runtime-bcp-back51.jar'
    with zipfile.ZipFile(jar,'w',compression=zipfile.ZIP_STORED) as z:
        info=zipfile.ZipInfo('classes.dex',date_time=(1980,1,1,0,0,0));z.writestr(info,(out/'after.dex').read_bytes())
    result={'status':'OFFLINE_BUILD_PASS_NOT_INSTALLED','input_sha256':sha(inp),'candidate_sha256':sha(jar),'classes':len(before),'changed_classes':changed,'changed_methods':['onBackPressed(Landroid/os/IBinder;Landroid/app/IRequestFinishCallback;)V'],'unchanged_other_definitions':True,'source_sha256':sha(HERE/'BackCallbackPatch.java'),'java':{'path':portable(Path(java).resolve()),'sha256':sha(Path(java).resolve())},'javac':{'path':portable(Path(javac).resolve()),'sha256':sha(Path(javac).resolve())},'commands':records,'device_calls':0,'ui_result':'PENDING'}
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps({k:v for k,v in result.items() if k!='commands'},indent=2))
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--input',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a.add_argument('--tools',type=Path,required=True);a.add_argument('--java',required=True);a.add_argument('--javac',required=True);n=a.parse_args();build(n.input,n.out,n.tools,n.java,n.javac)
