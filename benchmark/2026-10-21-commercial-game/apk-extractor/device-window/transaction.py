"""G13-specific transaction adapter for the two known swap provider failure edges.

Uses swap's checked_hashes/backup_name and layout, but never its exception rollback.
"""
import json
from pathlib import Path
import shlex
import time
from policy import TARGETS,ORIGINAL,CANDIDATE,need,Refuse
class TransportUnknown(Refuse):pass

def validate_kit(kit,sha):
    kit=Path(kit);manifest=json.loads((kit/'manifest.json').read_text())
    need(manifest.get('baseline')=={'libinstalls.z.so':ORIGINAL},'kit baseline keys/SHA')
    need(manifest.get('candidate')=={'libinstalls.z.so':CANDIDATE},'kit candidate keys/SHA')
    need(sha(kit/'libinstalls.z.so')==CANDIDATE,'kit library SHA')
    return manifest

def unknown_resolved(state,cfg,statefile,sha):
    if not state.get('transport_unknown'):return
    evidence=cfg.get('resolved_unknown_write')
    need(isinstance(evidence,dict) and evidence.get('reviewer')=='outer(codex)' and evidence.get('transaction_state_sha256')==sha(statefile) and evidence.get('pending_remote_writer') is False and evidence.get('evidence_path') and evidence.get('evidence_sha256')==sha(evidence['evidence_path']),'unknown remote write unresolved; reconcile only')

def transact(action,board,provider,cfg,window,log,save,sha):
    v=cfg['bindings'];kit=Path(v['kit']);validate_kit(kit,sha)
    remote='/data/local/tmp/installer-'+v['transaction'];statefile=window/'g13-transaction.json'
    provider.REMOTE=remote
    if action=='apply':
        need(not statefile.exists(),'transaction already exists; do not replay apply')
        state=dict(remote=remote,holder=v['holder'],boot=cfg['expected_boot'],status='preparing',desired='candidate',before={p:ORIGINAL for p in TARGETS})
        save(statefile,state)
    else:
        need(statefile.is_file(),'no transaction state');state=json.loads(statefile.read_text())
        need(state['remote']==remote and state['holder']==v['holder'] and state['boot']==cfg['expected_boot'],'transaction binding drift')
        unknown_resolved(state,cfg,statefile,sha)
        state['desired']='baseline'
    q=shlex.quote
    def persist(status):
        state['status']=status;save(statefile,state);save(log/('transaction-state-'+str(time.time_ns())+'.json'),state)
    def reseal():
        rc,text=board.shell('cat /proc/mounts');rows=[x.split() for x in text.splitlines() if len(x.split())==6 and x.split()[1]=='/']
        need(rc==0 and len(rows)==1,'cannot determine root mount state')
        if 'rw' in rows[0][3].split(','):board.shell('mount -o ro,remount /')
        _,text=board.shell('cat /proc/mounts');rows=[x.split() for x in text.splitlines() if len(x.split())==6 and x.split()[1]=='/']
        need(len(rows)==1 and 'ro' in rows[0][3].split(','),'RO recovery not proven')
        state['root_ro_verified']=True;save(statefile,state)
    try:
        if action=='apply':
            need(provider.checked_hashes(board,TARGETS)==state['before'],'baseline drift')
            board.shell('mkdir -p '+q(remote+'/backup'))
            for path in TARGETS:
                dest=provider.backup_name(path)
                board.shell('test ! -e '+q(dest)+' && cp -p '+q(path)+' '+q(dest))
            need(provider.checked_hashes(board,[provider.backup_name(p) for p in TARGETS])=={provider.backup_name(p):ORIGINAL for p in TARGETS},'board backup hash')
            persist('backups_verified')
            board.send(kit/'libinstalls.z.so',remote+'/libinstalls.z.so')
            need(provider.checked_hashes(board,[remote+'/libinstalls.z.so'])=={remote+'/libinstalls.z.so':CANDIDATE},'stage hash')
        else:
            need(provider.checked_hashes(board,[provider.backup_name(p) for p in TARGETS])=={provider.backup_name(p):ORIGINAL for p in TARGETS},'original backups incomplete')
        # Within try from BEFORE remount: known failure cannot bypass RO recovery.
        state['root_ro_verified']=False;persist('remount_rw_requested');board.shell('mount -o rw,remount /')
        for path in TARGETS:
            source=remote+'/libinstalls.z.so' if action=='apply' else provider.backup_name(path)
            tmp=path+'.g13-new';state['last_write_target']=path;persist('replace_requested')
            board.shell('cp -p '+q(source)+' '+q(tmp)+' && chmod 0755 '+q(tmp)+' && chown root:root '+q(tmp)+' && chcon u:object_r:system_lib_file:s0 '+q(tmp)+' && mv -f '+q(tmp)+' '+q(path))
        expected=CANDIDATE if action=='apply' else ORIGINAL
        need(provider.checked_hashes(board,TARGETS)=={p:expected for p in TARGETS},'post-write hash')
        persist('candidate_files_verified' if action=='apply' else 'original_files_verified')
    except (TransportUnknown,KeyboardInterrupt):
        state['transport_unknown']=True;persist('UNKNOWN_REMOTE_OUTCOME_RECONCILE_ONLY')
        # Deliberately no compensating writes, including remount, while a writer may remain.
        raise
    except Exception:
        persist('KNOWN_FAILURE_RESEAL_THEN_EXPLICIT_RESTORE')
        try:reseal()
        except TransportUnknown:
            state['transport_unknown']=True;persist('UNKNOWN_DURING_RESEAL_RECONCILE_ONLY');raise
        raise
    else:
        try:reseal()
        except TransportUnknown:
            state['transport_unknown']=True;persist('UNKNOWN_DURING_RESEAL_RECONCILE_ONLY');raise
        state['transport_unknown']=False;persist('APPLIED' if action=='apply' else 'ROLLED_BACK')
