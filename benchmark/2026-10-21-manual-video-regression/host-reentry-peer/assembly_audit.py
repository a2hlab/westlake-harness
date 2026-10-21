#!/usr/bin/env python3
"""Read-only pin-chain audit. Never source startup configuration or run entry."""
import hashlib
import re
from pathlib import Path

SHA = r'[0-9a-f]{64}'
NAME = re.compile(r'[A-Za-z0-9_.-]+\Z')
REQUIRED = ('boot-entry.sh', 'entry.sh', 'watchdog.sh', 'reentry-common.sh',
            'reentry-seams.sh', 'route-b-owner.sh', 'exit-verdict.sh',
            'config-common.sh', 'launch-common.sh', 'start-parent.sh',
            'real-start-parent-bounded.sh', 'spawn.sh', 'real-spawn.sh',
            'readiness-probe.sh', 'members.tsv', 'startup.env',
            'startup.expected.sha256', 'screen-gate', 'decoder-probe.jpeg')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def audit(payload, watchdog_sha, common_sha):
    rows = []
    def check(name, ok, evidence):
        rows.append(dict(check=name, verdict='pass' if ok else 'fail', evidence=evidence))
    if payload is None:
        check('complete_payload_present', False, 'source-only candidate: no payload selected')
        return dict(passed=False, rows=rows, execution=False)
    payload=Path(payload)
    hashes={}
    for name in REQUIRED:
        p=payload/name
        valid=p.is_file() and not p.is_symlink()
        check('member_present:'+name, valid, name)
        if valid: hashes[name]=digest(p)
    def text(name):
        return (payload/name).read_text() if name in hashes else ''
    check('payload_watchdog_equals_reviewed_source', hashes.get('watchdog.sh')==watchdog_sha,
          dict(expected=watchdog_sha, observed=hashes.get('watchdog.sh','unknown')))
    check('payload_common_equals_reviewed_source', hashes.get('reentry-common.sh')==common_sha,
          dict(expected=common_sha, observed=hashes.get('reentry-common.sh','unknown')))
    members={}
    for n,line in enumerate(text('members.tsv').splitlines(),1):
        fields=line.split()
        valid=len(fields)==3 and re.fullmatch(SHA,fields[0]) and NAME.fullmatch(fields[1]) and re.fullmatch(r'[0-7]{3,4}',fields[2])
        if not valid:
            check('members_line:'+str(n),False,line);continue
        expected,name,mode=fields
        check('members_unique:'+name,name not in members,name)
        members[name]=expected
        p=payload/name
        got=digest(p) if p.is_file() and not p.is_symlink() else 'unknown'
        check('members_sha:'+name,got==expected,dict(expected=expected,observed=got,mode=mode))
    for name in ('watchdog.sh','entry.sh','config-common.sh','start-parent.sh','spawn.sh',
                 'reentry-common.sh','reentry-seams.sh','route-b-owner.sh','exit-verdict.sh',
                 'launch-common.sh','real-start-parent-bounded.sh','real-spawn.sh','readiness-probe.sh',
                 'screen-gate','decoder-probe.jpeg'):
        check('boot_copy_contains:'+name,name in members,name)
    env={}
    for name,value in re.findall(r'^(STARTUP_\w+)=[\'\"]?([^\'\"\n]*)[\'\"]?$',text('startup.env'),re.M):
        check('startup_unique:'+name,name not in env,name);env[name]=value
    check('startup_signature',text('startup.expected.sha256').strip()==hashes.get('startup.env'),
          dict(expected=text('startup.expected.sha256').strip(),observed=hashes.get('startup.env','unknown')))
    for field,name in [('STARTUP_MEMBERS_SHA','members.tsv'),('STARTUP_START_PARENT_SHA','real-start-parent-bounded.sh'),
                       ('STARTUP_DECODER_SHA','screen-gate'),('STARTUP_PROBE_SHA','decoder-probe.jpeg')]:
        check(field,env.get(field)==hashes.get(name) and name in hashes,
              dict(expected=env.get(field,'unknown'),observed=hashes.get(name,'unknown')))
    entry=text('entry.sh')
    for name in ('watchdog.sh','route-b-owner.sh'):
        # Exact literal comparison in the existing immutable entry protocol.
        found=re.findall(r'^.*sha256sum "\$HERE/'+re.escape(name)+r'".*? = ('+SHA+r') \].*$',entry,re.M)
        check('entry_pin:'+name,len(found)==1 and found[0]==hashes.get(name),
              dict(literals=found,observed=hashes.get(name,'unknown')))
    check('entry_exec_watchdog','exec /system/bin/sh "$HERE/watchdog.sh"' in entry,'entry.sh')
    check('boot_exec_entry','exec /system/bin/sh "$AUTH_STATE_ROOT/entry.sh"' in text('boot-entry.sh'),'boot-entry.sh')
    for owner in ('watchdog.sh','entry.sh','boot-entry.sh','start-parent.sh','spawn.sh'):
        for name in re.findall(r'^\. "\$HERE/([A-Za-z0-9_.-]+)"',text(owner),re.M):
            check('source_dependency:'+owner+':'+name,(payload/name).is_file() and not (payload/name).is_symlink(),name)
    manifest=payload.parent/'MANIFEST.sha256'
    check('package_manifest_present',manifest.is_file() and not manifest.is_symlink(),'../MANIFEST.sha256')
    covered=set()
    if manifest.is_file() and not manifest.is_symlink():
        for n,line in enumerate(manifest.read_text().splitlines(),1):
            fields=line.split()
            valid=len(fields)==2 and re.fullmatch(SHA,fields[0]) and fields[1].startswith('payload/') and NAME.fullmatch(fields[1][8:])
            if not valid:check('manifest_line:'+str(n),False,line);continue
            expected,name=fields;name=name[8:]
            check('manifest_unique:'+name,name not in covered,name);covered.add(name)
            file=payload/name
            got=digest(file) if file.is_file() and not file.is_symlink() else 'unknown'
            check('manifest_sha:'+name,got==expected,dict(expected=expected,observed=got))
        for name in REQUIRED:check('manifest_covers:'+name,name in covered,name)
    roots=re.findall(r'^ROOT=(.*)$',text('config-common.sh'),re.M)
    return dict(passed=all(x['verdict']=='pass' for x in rows),rows=rows,execution=False,
                scope='Exact local pin consistency and static entry edges only; no boot, process, approval or device validation.',
                files=hashes,authority=dict(startup_enabled=env.get('STARTUP_ENABLED','unknown'),
                    approved_by=env.get('STARTUP_APPROVED_BY','unknown'),configured_roots=roots,
                    deployment_authorized=False),
                external_runtime_hashes='not checked offline; not implied by assembly PASS')
