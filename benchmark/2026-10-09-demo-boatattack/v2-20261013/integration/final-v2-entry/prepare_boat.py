#!/usr/bin/env python3
"""Missing BMS registration + original APK + controlled empty target. Never launches or deletes a bundle directory."""
import argparse,importlib.util,json,os,shlex,sys
from pathlib import Path
import restore_entry as r
HERE=Path(__file__).resolve().parent
PACKAGE='com.Unity3d.BoatAttackDay'
APK='/data/app/el1/bundle/public/'+PACKAGE+'/android/base.apk'
APK_SHA='8dc636657cccdad1310332928b8cc8eca7da03f4b528de6fb0c63118173e0444'
LIBDIR='/data/app/el1/bundle/public/'+PACKAGE+'/android/lib/arm64-v8a'
SIGNAL=LIBDIR+'/libwestlake_bionic_signal_box.so'
EMPTY='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
STOCK={'libunity.so':'1e44603c528af84aed2e4a538d411c119166b9ccadd7aa2abf51ffa97ef47ca2','libil2cpp.so':'58555c421de763165225e8bd9e2940f2e5c84515a2c87cdefc0892cae216f4fe'}
META={'mode':'755','uid':0,'gid':0,'label':'u:object_r:data_app_el1_file:s0'}
SIGNAL_META=dict(META,mode='644')
BMS_SHA='f41efa6ae2450adadda1f02c3c09335b74479c7d025872bbf95b3c8a444b177c'
ENTRY_SHA='e1f1cf4d4eae1db52ad48a9eb5455d8a00b4255c2d1bda33a3f04e7bcc47b589'
COMMON_SHA='df39c939529c9b571091c6df1c11b10c19003298d3f1f42bc98ce0e8ca915341'
def module(p,name):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def metadata(board,target):
    rc,text=board.shell('set -eu; p='+shlex.quote(target)+'; walk="$p"; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done; test ! -L "$p"; if [ -f "$p" ]; then echo EXISTS; sha256sum "$p"; stat -c "%a:%u:%g:%C" "$p"; elif [ ! -e "$p" ]; then echo ABSENT; else exit 2; fi')
    r.need(rc==0,'metadata command failed')
    if text.strip()=='ABSENT':return {'exists':False}
    lines=text.strip().splitlines();r.need(len(lines)==3 and lines[0]=='EXISTS','metadata parse')
    h,path=lines[1].split(None,1);r.need(path==target,'metadata target')
    mode,uid,gid,label=lines[2].split(':',3)
    return dict(exists=True,sha256=h,mode=mode,uid=int(uid),gid=int(gid),label=label)

def protect(board):
    for name,h in STOCK.items():r.need(metadata(board,LIBDIR+'/'+name)==dict(exists=True,sha256=h,**META),'pre-existing stock library drift: '+name)

def perform(data,base,out,b,board,entry,common):
    """Injection boundary for offline tests; production supplies the exact BMS module."""
    boot=data['boot_id'];board.ready();r.need(board.boot.strip()==boot,'preinstall boot')
    app=data['app'];source=b.resolve_input(r.path(data['input_root'],base),app)
    r.need(source['package']==PACKAGE and source['apk_sha256']==APK_SHA and r.sha(source['apk'])==APK_SHA,'original APK identity')
    protect(board)
    signal_before=metadata(board,SIGNAL)
    r.need(signal_before in ({'exists':False},dict(exists=True,sha256=EMPTY,**SIGNAL_META)),'unknown pre-existing signal target; no install')
    # Preserve exact originals before an installer can touch an unregistered bundle directory.
    for name,h in STOCK.items():
        dest=out/(name+'.preinstall');board.receive(LIBDIR+'/'+name,dest);r.need(r.sha(dest)==h,'stock backup SHA')
    rc,dump=board.shell('bm dump -n '+PACKAGE,required=False)
    r.need(rc==0,'BMS read failed, not absence')
    installed=metadata(board,APK)
    if dump.strip().lower()==entry.ABSENT:
        r.need(installed=={'exists':False},'BMS absence without APK absence')
        protect(board)
        entry.b=b
        result=entry.install_one(board,app,r.path(data['input_root'],base),out/'install','/data/local/tmp/boat-v2-original-apk')
        r.need(result.get('status')=='installed' and result.get('install',{}).get('return_code')==0,'actual missing-only install failed')
    else:
        # No reinstall, cold_stop, uninstall, -r, or directory cleanup path.
        identity=module(HERE.parent/'final-v2-candidate-r2/boat_identity.py','preinstall_identity')
        identity.parse(dump);r.need(installed.get('sha256')==APK_SHA,'existing Boat APK drift')
        result={'status':'already-equal'}
    protect(board)
    r.need(metadata(board,APK).get('sha256')==APK_SHA,'installed APK SHA readback')
    identity=module(HERE.parent/'final-v2-candidate-r2/boat_identity.py','installed_boat_identity')
    rc,dump=board.shell('bm dump -n '+PACKAGE,required=False);r.need(rc==0,'BMS readback');uid=identity.parse(dump)
    before=metadata(board,SIGNAL);wanted=dict(exists=True,sha256=EMPTY,**SIGNAL_META)
    if before=={'exists':False}:
        r.save(out/'placeholder-intent.json',dict(target=SIGNAL,before=before,after=wanted,serial=r.SERIAL,boot_id=boot))
        # Same empty target policy as historical lightup.sh:470; fail if concurrently created.
        script='set -eu; test -d '+shlex.quote(LIBDIR)+'; test ! -L '+shlex.quote(LIBDIR)+'; test ! -e '+shlex.quote(SIGNAL)+'; test ! -L '+shlex.quote(SIGNAL)+'; (set -C; : > '+shlex.quote(SIGNAL)+'); chown 0:0 '+shlex.quote(SIGNAL)+'; chmod 644 '+shlex.quote(SIGNAL)+'; chcon u:object_r:data_app_el1_file:s0 '+shlex.quote(SIGNAL)
        board.shell(script)
        r.need(metadata(board,SIGNAL)==wanted,'empty placeholder readback')
        rc,inode=board.shell('stat -c %d:%i '+shlex.quote(SIGNAL));r.need(rc==0,'placeholder identity')
        r.save(out/'placeholder-created.json',dict(target=SIGNAL,before=before,after=wanted,identity=inode.strip(),serial=r.SERIAL,boot_id=boot))
    else:r.need(before==wanted,'existing signal target differs; no replacement')
    protect(board);board.ready();r.need(board.boot.strip()==boot,'preinstall changed boot')
    return dict(status='PREINSTALL_COMPLETE_PENDING_FRESH_CAPTURE',serial=r.SERIAL,boot_id=boot,boat_uid=uid,apk_sha256=APK_SHA,install=result,stock_libraries_preserved=True,placeholder=wanted,provider_compiled=False,restored=False,reboots=0)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--request',type=Path,required=True);ap.add_argument('--request-sha256',required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--execute',action='store_true');a=ap.parse_args()
    try:
        r.need(r.sha(a.request)==a.request_sha256,'request independent pin');data=r.read(a.request);base=a.request.resolve().parent
        r.need(data['schema']=='boat-missing-preinstall/v1' and data['serial']==r.SERIAL,'preinstall scope')
        snapshot=r.read(r.pin(data['preinstall_snapshot'],base))
        r.need(snapshot['serial']==r.SERIAL and snapshot['boot_before']==snapshot['boot_after']==data['boot_id'] and snapshot['complete'] is False and snapshot['boat_registered'] is False,'preinstall source scope')
        for name,h in STOCK.items():r.need(snapshot['files'][LIBDIR+'/'+name]==dict(exists=True,sha256=h,**META),'captured stock metadata')
        r.need(data['app']['package']==PACKAGE and data['app']['apk_sha256']==APK_SHA,'fixed original Boat APK')
        b=module(r.pin(data['executor'],base,BMS_SHA),'frozen_bms');entry=module(HERE/'frozen-apk/missing_apk_entry.py','missing_only')
        r.need(r.sha(HERE/'frozen-apk/missing_apk_entry.py')==ENTRY_SHA,'missing-only source drift')
        r.need(r.sha(HERE/'frozen-apk/provider_common.py')==COMMON_SHA,'common source drift');common=module(HERE/'frozen-apk/provider_common.py','preinstall_common')
        identity=r.pin(data['identity_program'],base);r.need(identity==(HERE.parent/'final-v2-candidate-r2/boat_identity.py').resolve(),'identity program location')
        resolved=b.resolve_input(r.path(data['input_root'],base),data['app']);r.need(resolved['package']==PACKAGE and resolved['apk_sha256']==APK_SHA and r.sha(resolved['apk'])==APK_SHA,'original local APK')
        r.need(not a.out.exists(),'fresh preinstall evidence output')
        if not a.execute:print(json.dumps({'status':'OFFLINE_PREINSTALL_PREVIEW','device_calls':0,'next':'fresh same-boot BMS UID/private metadata capture; then compile new disabled provider'}));return 0
        r.need(data.get('execution_enabled') is True and not data.get('synthetic'),'disabled/synthetic request')
        a.out.mkdir(parents=True);receipt=dict(status='FAILED_PRESERVE_EVIDENCE',restored=False,reboots=0)
        try:
            transport=data['transport']
            expanded={k:shlex.join([os.path.expandvars(v) for v in shlex.split(transport[k])]) for k in ('hdc_cmd','lock_cmd')}
            board=b.Board(r.SERIAL,expanded['hdc_cmd'],expanded['lock_cmd'],transport['lane'],a.out/'commands')
            receipt=perform(data,base,a.out,b,board,entry,common);return 0
        except Exception as error:
            receipt['error']=str(error);raise
        finally:r.save(a.out/'preinstall-receipt.json',receipt)
    except (ValueError,KeyError,TypeError,OSError) as e:print('PREINSTALL REFUSED: '+str(e),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
