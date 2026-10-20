#!/usr/bin/env python3
"""T34 follow-up archive. Preparation is local only; execute only after root closure."""
import argparse,hashlib,io,json,os,shlex,subprocess,tarfile,time
from pathlib import Path,PurePosixPath
HOME=Path.home(); OLD=HOME/'.local/share/westlake/t34-window-archive-01'
ROOTS={
 'window/W-04':HOME/'.local/share/westlake/t34-demo61b-video-20261021/W-04',
 'window/W04-after-close-read-01':HOME/'.local/share/westlake/t34-demo61b-video-20261021/W04-after-close-read-01',
 'peer/window-driver-outer':HOME/'.local/share/westlake/t34-window-driver-outer-01',
 'environment-read':HOME/'.local/share/westlake/t34-environment-read-20261021',
 'peer/environment':HOME/'.local/share/westlake/t34-environment-peer',
 'peer/window-driver-author':HOME/'.local/share/westlake/t34-window-driver-peer',
 'peer/window-driver-independent':HOME/'.local/share/westlake/t34-window-driver-peer-01',
 'peer/candidate-view':HOME/'.local/share/westlake/t34-candidate-view-peer',
}
ALIAS='HW248_ARTIFACT_ROOT/t34-demo61b-video-20261021/window-04.tar.gz'
def digest(b):return hashlib.sha256(b).hexdigest()
def put(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def inventory():
    out=[]
    for label,root in ROOTS.items():
        assert root.is_dir() and not root.is_symlink(),root
        for p in sorted(root.rglob('*')):
            assert not p.is_symlink(),f'symlink not silently followed: {p}'
            if p.is_file():
                st=p.stat();out.append((label+'/'+str(p.relative_to(root)),p,(st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)))
    return out
def invoke(out,index,argv,stdin=None,timeout=180):
    d=out/f'command-{index}';d.mkdir();put(d/'argv.json',argv)
    if stdin is not None:(d/'stdin').write_bytes(stdin)
    try:
        p=subprocess.run(argv,input=stdin,capture_output=True,timeout=timeout);rc=p.returncode;stdout=p.stdout;stderr=p.stderr
    except subprocess.TimeoutExpired as e:
        rc=124;stdout=e.stdout or b'';stderr=(e.stderr or b'')+b'\nHOST_TIMEOUT\n'
    (d/'stdout').write_bytes(stdout);(d/'stderr').write_bytes(stderr);(d/'rc').write_text(str(rc)+'\n')
    assert rc==0,f'command-{index} rc={rc}; preserve originals, do not retry blindly'
    return stdout
def main():
    a=argparse.ArgumentParser();a.add_argument('--execute',action='store_true');a.add_argument('--closed-confirmation',type=Path);a.add_argument('--out',type=Path);args=a.parse_args()
    ssh=json.loads((OLD/'command-2/argv.json').read_text());scp=json.loads((OLD/'command-1/argv.json').read_text());assert ssh[0]=='ssh' and scp[0]=='scp'
    endpoint,oldpath=scp[-1].split(':',1);assert oldpath.endswith('/window.tar.gz')
    final=str(PurePosixPath(oldpath).with_name('window-04.tar.gz'));reserve=final+'.reserve';staged=reserve+'/payload.tar.gz'
    verifier=(OLD/'command-2/stdin').read_bytes();assert b'all_members_match' in verifier
    if not args.execute:
        print(json.dumps({'status':'PREPARED_ONLY_NOT_SNAPSHOTTED','remote_alias':ALIAS,'source_labels':list(ROOTS),'requires':'Root CLOSED_AND_UNLOCKED confirmation with pinned closure receipts, --execute and fresh --out','device_calls':0}));return
    assert args.closed_confirmation and args.out
    c=json.loads(args.closed_confirmation.read_text());assert c['approved_by']=='outer(codex)' and c['status']=='CLOSED_AND_UNLOCKED' and set(c['windows'])=={'W-04'}
    assert c['evidence']
    for r in c['evidence']:
        p=Path(os.path.expandvars(r['path']));assert p.is_file() and digest(p.read_bytes())==r['sha256']
    closed=[]
    for r in c['evidence']:
        path=Path(os.path.expandvars(r['path'])).resolve()
        if path.is_relative_to(ROOTS['window/W-04'].resolve()) and path.name=='closed.json':
            closed.append(json.loads(path.read_text()))
    assert len(closed)==1 and closed[0]['status']=='RESTORED_UNLOCKED' and closed[0]['held_after_rc']==1,'Require actual W04 recovery closure, not an old window'
    admission=json.loads((ROOTS['window/W-04']/'admission.json').read_text())
    assert closed[0]['holder']==admission['holder'] and closed[0]['start']==admission['window_start']
    assert all(not args.out.resolve().is_relative_to(root.resolve()) for root in ROOTS.values()),'Output must be outside source roots'
    args.out.mkdir(parents=True,exist_ok=False);out=args.out;put(out/'closed-confirmation.json',c)
    records=inventory();members=[];archive=out/'window-04.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:
        for name,p,identity in records:
            with p.open('rb') as f:
                st=os.fstat(f.fileno());assert (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)==identity
                b=f.read();post=os.fstat(f.fileno());assert (post.st_dev,post.st_ino,post.st_size,post.st_mtime_ns)==identity
            assert len(b)==identity[2];members.append({'path':name,'bytes':len(b),'sha256':digest(b)})
            info=tarfile.TarInfo(name);info.size=len(b);info.mode=0o600;tar.addfile(info,io.BytesIO(b))
        data=(json.dumps(members,indent=2)+'\n').encode();info=tarfile.TarInfo('MEMBERS.json');info.size=len(data);info.mode=0o600;tar.addfile(info,io.BytesIO(data))
    assert [(x[0],x[2]) for x in inventory()]==[(x[0],x[2]) for x in records],'Source changed during snapshot: abort before network'
    put(out/'members.json',members);blob=archive.read_bytes();sha=digest(blob);size=len(blob)
    with tarfile.open(archive,'r:gz') as tar:
        actual=tar.getmembers();assert len(actual)==len(members)+1
        for r in members:
            b=tar.extractfile(r['path']).read();assert len(b)==r['bytes'] and digest(b)==r['sha256']
    q=shlex.quote
    # Reservation plus hard-link publication prevents overwriting either an earlier follow-up or window.tar.gz.
    invoke(out,0,ssh[:-1]+['set -eu; umask 077; test ! -e '+q(final)+'; test ! -L '+q(final)+'; mkdir -m 700 '+q(reserve)])
    invoke(out,1,scp[:-2]+[str(archive),endpoint+':'+staged],timeout=600)
    invoke(out,2,ssh[:-1]+['set -eu; chmod 600 '+q(staged)+'; ln '+q(staged)+' '+q(final)])
    result=invoke(out,3,ssh[:-1]+['python3 - '+q(final)+' '+q(sha)+' '+str(size)],stdin=verifier,timeout=300)
    remote=json.loads(result);assert remote=={'archive_sha256':sha,'bytes':size,'members_verified':len(members),'all_members_match':True}
    put(out/'receipt.json',{'created_at':time.time(),'archive_sha256':sha,'archive_bytes':size,'members':len(members),'remote_alias':ALIAS,'source_labels':list(ROOTS),'scope':'Snapshot after explicit W04 closure; old window.tar.gz and window-03.tar.gz preserved; remote command-3 uses original command-2 verifier','remote_verification':remote,'old_verifier_sha256':digest(verifier),'closed_confirmation_sha256':digest(args.closed_confirmation.read_bytes())})
    print('VERIFIED_RECEIPT_WRITTEN')
if __name__=='__main__':main()
