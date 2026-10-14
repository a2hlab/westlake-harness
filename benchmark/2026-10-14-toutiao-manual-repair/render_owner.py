#!/usr/bin/env python3
"""Offline command renderer. Never calls HDC; outer owns lock, execution and raw logs."""
import argparse, hashlib, json, pathlib, re, shlex
HERE = pathlib.Path(__file__).resolve().parent
SERIAL = '5cd1e3dd00000000000000000923012c'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def render(action, boot, parent, birth, hdc, observation=None):
    assert re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', boot), 'boot'
    assert parent > 1 and birth > 0, 'parent identity'
    expected = '-'
    if action != 'preflight':
        assert observation and observation['schema']=='toutiao-owner-observation/v1'
        assert observation['status']=='VERIFIED' and observation['boot_id']==boot
        assert observation['parent_pid']==parent and observation['parent_birth']==birth
        expected = observation['after']
        required = '0:0' if action in ('apply','reconcile') else '20011300:20011300'
        assert re.fullmatch(r'\d+:\d+\|'+required+r'\|755\|u:object_r:appdat:s0', expected), 'exact before'
        assert observation['action'] in (('preflight',) if action in ('apply','reconcile') else ('apply','reconcile')), 'receipt action'
    body = 'set -- '+shlex.join([action,boot,str(parent),str(birth),expected])+'\n'+(HERE/'owner_remote.sh').read_text()
    remote = '/system/bin/sh -c '+shlex.quote(body)+'; owner_rc=$?; printf "\\nOWNER_REMOTE_RC=%s\\n" "$owner_rc"'
    return dict(schema='toutiao-owner-command/v1', execution_enabled=False, action=action,
        serial=SERIAL, boot_id=boot, requires='outer-held board lock; current authorization; preserve raw stdout/stderr/time and require HDC rc0 + OWNER_REMOTE_RC=0 + VERIFIED JSON',
        argv=[hdc,'-t',SERIAL,'shell',remote], source_sha256=sha(HERE/'owner_remote.sh'),
        expected_before=expected, mutation_count=0 if action in ('preflight','reconcile') else 1)
def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['preflight','apply','rollback','reconcile'])
    for name in ['boot','hdc','out']:p.add_argument('--'+name,required=True)
    p.add_argument('--parent',type=int,required=True);p.add_argument('--birth',type=int,required=True)
    p.add_argument('--observation',type=pathlib.Path)
    p.add_argument('--failed-command',type=pathlib.Path);p.add_argument('--failed-stdout',type=pathlib.Path)
    a=p.parse_args();o=json.loads(a.observation.read_text()) if a.observation else None
    d=render(a.action,a.boot,a.parent,a.birth,a.hdc,o)
    if a.observation:d['observation_sha256']=sha(a.observation)
    if a.action=='reconcile':
        assert a.failed_command and a.failed_stdout, 'original failed apply evidence required'
        failed=json.loads(a.failed_command.read_text());raw=a.failed_stdout.read_text()
        assert failed['action']=='apply' and failed['serial']==SERIAL and failed['boot_id']==a.boot
        assert failed['expected_before']==o['after'], 'failed command before binding'
        assert failed['argv'][1:4]==['-t',SERIAL,'shell'], 'failed transport serial'
        assert 'OWNER_INTENT action=apply before='+o['after']+' after=' in raw
        assert re.search(r'^OWNER_REMOTE_RC=[1-9][0-9]*$',raw,re.M), 'original nonzero required'
        d['failed_apply_evidence']={'command_sha256':sha(a.failed_command),'stdout_sha256':sha(a.failed_stdout),'original_success':False}

    with pathlib.Path(a.out).open('x') as f:json.dump(d,f,indent=2);f.write('\n')
if __name__=='__main__':main()
