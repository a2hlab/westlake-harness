#!/usr/bin/env python3
"""Offline internal receipt-binding checks. Never executes recorded argv."""
import argparse
import hashlib
import json
import math
from pathlib import Path

SERIAL = '61b0657200000000000000000324012c'
CANDIDATE = '3291f76db0945f90b402ea61b14c3a912efbeecec9e0422af1a92fec95b8a819'
UI = ('first_open', 'same_host_return', 'new_host_old_child')
KINDS = ('lock', 'preflight', 'publish', 'activation', *UI, 'rollback', 'final', 'unlock')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def loads(data):
    def bad(value):
        raise ValueError('nonfinite JSON constant: '+value)
    return json.loads(data, parse_constant=bad)


def number(x):
    return type(x) in (int, float) and math.isfinite(x)


def positive(x):
    return type(x) is int and x > 0


class Invalid(ValueError):
    pass


class Checker:
    def __init__(self, root, plan, plan_sha, synthetic=False):
        self.root = Path(root).resolve()
        self.plan, self.plan_sha, self.synthetic = plan, plan_sha, synthetic
        self.issues, self.missing, self.pins = [], [], []
        self.events = {}
        self.commands = {}
        self.command_ids = {}
        self.candidate = 'unknown'
        self.recovery = 'unknown'
        self.unknown = ['image_meaning', 'receipt_origin_authenticity', 'producer_identity']

    def need(self, condition, message):
        if not condition:
            raise Invalid(message)

    def blob(self, ref):
        self.need(isinstance(ref, dict) and set(ref) == {'path', 'sha256'}, 'reference requires path and sha256')
        self.need(isinstance(ref['path'], str) and isinstance(ref['sha256'], str), 'reference types invalid')
        p = Path(ref['path'])
        self.need(not p.is_absolute() and p.parts and '..' not in p.parts, 'reference escapes receipt directory')
        self.need(not any(x.startswith('.env') for x in p.parts), 'forbidden reference')
        q = self.root
        for part in p.parts:
            q /= part
            self.need(not q.is_symlink(), 'symlink reference refused')
        self.need(q.is_file() and q.stat().st_size <= 64*1024*1024, 'missing or oversized reference: '+str(p))
        data = q.read_bytes()
        self.need(digest(data) == ref['sha256'], 'reference SHA mismatch: '+str(p))
        self.pins.append(ref)
        return data

    def obj(self, ref):
        return loads(self.blob(ref))

    def process(self, x, role='child'):
        self.need(isinstance(x, dict), 'process identity missing')
        self.need(all(positive(x.get(k)) for k in ('pid', 'birth')) and type(x.get('uid')) is int and x['uid'] >= 0, 'PID/birth/UID missing or invalid')
        self.need(isinstance(x.get('boot'), str) and bool(x['boot']), 'process boot missing')
        if role != 'parent':
            self.need(x['uid'] == self.plan['target_metadata']['uid'], 'process UID mismatch')
        return tuple(x[k] for k in ('boot', 'pid', 'birth', 'uid'))

    def identities(self, data, boot):
        result = {k:self.process(data[k], k) for k in ('host', 'parent', 'child')}
        self.need(all(v[0] == boot for v in result.values()), 'process boot mismatch')
        return result

    def metadata(self, value):
        self.need(value == self.plan['target_metadata'], 'metadata mismatch')

    def mapping(self, value, child, expected):
        self.need(self.process(value['child_before']) == child == self.process(value['child_after']), 'mapping child PID/birth bracket mismatch')
        self.need(value['mapped_path'] == '/data/local/tmp/asx/liboh_adapter_bridge.so', 'mapped path mismatch')
        self.need(value['backing_path'] == self.plan['target'], 'backing path mismatch')
        self.need(positive(value['device']) and positive(value['inode']), 'backing dev/inode missing')
        disk = value['process_root_stat']
        self.need(isinstance(value['mount_namespace'], str) and bool(value['mount_namespace']) and value['mount_namespace'] == disk['mount_namespace'], 'mapping namespace mismatch')
        self.need((disk['device'], disk['inode']) == (value['device'], value['inode']), 'maps/process-root dev/inode mismatch')
        self.need(value['sha256'] == disk['sha256'] == expected, 'mapped SHA mismatch (root-only SHA insufficient)')
        self.metadata(disk['metadata'])

    def command(self, ref, identity):
        c = self.obj(ref)
        self.need(all(c[f] == identity[f] for f in ('run_id','serial','clock_id','origin','boot')), 'mixed command identity')
        self.need(isinstance(c['command_id'], str) and bool(c['command_id']), 'command id missing')
        self.need(number(c['start']) and number(c['end']) and 0 <= c['start'] <= c['end'], 'invalid command monotonic time')
        self.need(c['role'] in ('read','icon','touch','publish','rollback','power','reboot'), 'unknown command role')
        self.need(type(c['write']) is bool and c['write'] == (c['role'] != 'read'), 'incorrect write classification')
        self.need(isinstance(c['argv'], list) and len(c['argv']) > 0 and all(isinstance(a,str) for a in c['argv']), 'actual argv absent')
        self.need(type(c['transport_rc']) is int and c['transport_rc'] == 0, 'transport failure')
        self.need(type(c['remote_rc']) is int and c['remote_rc'] == 0, 'remote failure/unknown write')
        self.need(c['body_errors'] == [], 'body failure despite rc0')
        self.blob(c['stdout']); self.blob(c['stderr'])
        key = ref['sha256']
        self.need(c['command_id'] not in self.command_ids or self.command_ids[c['command_id']] == key, 'command id reused with different bytes')
        self.command_ids[c['command_id']] = key
        self.commands[key] = c
        return c

    def click(self, data, receipt):
        ref = data['click']
        self.need(ref in receipt['commands'], 'click not present in phase command references')
        c = self.commands[ref['sha256']]
        self.need(c['role'] == 'icon', 'click reference is not an icon command')
        icons = [x for x in receipt['commands'] if self.commands[x['sha256']]['role'] == 'icon']
        self.need(len(icons) == 1, 'phase requires exactly one icon command')
        return c

    @staticmethod
    def object_id(mapping):
        return (mapping['device'], mapping['inode'], mapping['mount_namespace'])

    def image(self, ref):
        data = self.blob(ref)
        self.need(data.startswith(b'\x89PNG\r\n\x1a\n') or data.startswith(b'\xff\xd8\xff'), 'screenshot container missing')
        # This tests container identity only, never decodes or judges feed.

    def check(self, packet):
        try:
            self.need(packet.get('schema') == 'native-validation-receipts/v1', 'unsupported packet schema')
            self.need(packet.get('origin') in ('synthetic', 'recorded'), 'origin must be explicit')
            self.need((packet['origin'] == 'synthetic') == self.synthetic, 'synthetic mode mismatch')
            self.need(self.plan['serial'] == SERIAL, 'wrong plan serial')
            if not self.synthetic:
                self.need(self.plan['candidate_sha256'] == CANDIDATE, 'wrong approved candidate')
            self.need(packet['plan_sha256'] == self.plan_sha, 'plan SHA mismatch')
            self.need(packet['serial'] == self.plan['serial'], 'wrong serial')
            self.need(isinstance(packet['run_id'], str) and bool(packet['run_id']), 'run_id missing')
            self.need(isinstance(packet['clock_id'], str) and bool(packet['clock_id']), 'monotonic clock_id missing')
            self.need(isinstance(packet['receipts'], list), 'receipts missing')
        except (Invalid, KeyError, TypeError) as e:
            self.issues.append('packet: '+str(e))
            return self.result(packet)
        for ref in packet['receipts']:
            try:
                r = self.obj(ref)
                k = r['kind']
                self.need(k in KINDS and k not in self.events, 'unknown/duplicate stage')
                self.need(all(r[f] == packet[f] for f in ('run_id','serial','clock_id','origin')), 'mixed run/serial/clock/origin')
                self.need(isinstance(r['boot'], str) and bool(r['boot']), 'receipt boot missing')
                self.need(number(r['phase_start']) and number(r['phase_end']) and 0 <= r['phase_start'] <= r['phase_end'], 'invalid phase monotonic time')
                self.need(isinstance(r['commands'], list) and bool(r['commands']), 'command references missing')
                self.need(len({x['sha256'] for x in r['commands']}) == len(r['commands']), 'duplicate command in phase')
                for command_ref in r['commands']:
                    c = self.command(command_ref, r)
                    self.need(r['phase_start'] <= c['start'] <= c['end'] <= r['phase_end'], 'command outside phase')
                data = self.obj(r['observations'])
                self.need(all(data[f] == r[f] for f in ('kind','run_id','serial','clock_id','boot','origin')), 'observation identity mismatch')
                self.events[k] = (r, data)
            except (Invalid, KeyError, ValueError, TypeError, OSError) as e:
                self.issues.append('receipt: '+str(e))
        for k in ('lock','preflight','publish','activation','rollback','final','unlock'):
            if k not in self.events:
                self.missing.append(k)
        if self.missing:
            return self.result(packet)
        try:
            self.validate()
        except (Invalid, KeyError, ValueError, TypeError, OSError) as e:
            self.issues.append('evidence: '+str(e))
        return self.result(packet)

    def validate(self):
        p = self.plan
        lock, ld = self.events['lock']; unlock, ud = self.events['unlock']
        t0 = lock['phase_start']
        for data, names in [(ld, ('held_before_rc','acquire_rc')), (ud, ('release_rc','held_after_rc'))]:
            self.need(all(type(data.get(n)) is int for n in names), 'lock rc must be integer, not bool')
        self.need(isinstance(ld['token'], str) and bool(ld['token']), 'lock tuple absent')
        self.need(ld['owner'] == ud['owner'] and ld['token'] == ud['token'], 'lock owner/token mismatch')
        self.need(ld['held_before_rc'] == 1 and ld['held_before_stdout'] == '' and ld['acquire_rc'] == 0, 'lock acquisition evidence absent')
        self.need(ud['release_rc'] == 0 and ud['held_after_rc'] == 1 and ud['held_after_stdout'] == '', 'unlock evidence absent')
        for kind, (r,d) in self.events.items():
            self.need(t0 <= r['phase_start'] <= r['phase_end'] <= unlock['phase_end'], 'event outside lock lifecycle')
            if kind in ('publish', *UI):
                self.need(r['phase_start']-t0 < 900, 'new experiment at/after900')
        for c in self.commands.values():
            if c['write']:
                self.need(lock['phase_end'] <= c['start'] <= c['end'] <= unlock['phase_start'], 'write outside LOCK/UNLOCK')
                if c['role'] in ('icon','touch','publish'):
                    self.need(c['start']-t0 < 900, 'new command at/after900')
        self.need(unlock['phase_end']-t0 <= 1800, 'close exceeds1800')
        rollback, rd = self.events['rollback']
        self.need(rollback['phase_start']-t0 < 1200, 'rollback not begun before1200')
        pre, pd = self.events['preflight']; pub, wd = self.events['publish']; act, ad = self.events['activation']
        self.need(lock['phase_end'] <= pre['phase_start'] and pre['phase_end'] <= pub['phase_start'] and pub['phase_end'] <= act['phase_start'] <= rollback['phase_start'], 'preflight/publish/activation/rollback order')
        self.need(lock['boot'] == pre['boot'] == pub['boot'], 'preflight boot mismatch')
        ids0 = self.identities(pd, pre['boot'])
        self.mapping(pd['mapping'], ids0['child'], p['rollback_sha256'])
        self.need(pd['mapping']['device'] == p['preimage_device'] and pd['mapping']['inode'] == p['preimage_inode'], 'preimage identity differs from fixed plan')
        for name, expected in [('candidate_file',p['candidate_sha256']),('rollback_file',p['rollback_sha256']),('review02_manifest',p['review02_manifest_sha256']),('callback_review',p['callback_review_sha256'])]:
            self.need(digest(self.blob(pd[name])) == expected, name+' identity mismatch')
        gate = self.obj(pd['frozen_gate'])
        self.need(positive(gate['checked']) and gate['violations'] == [], 'frozen gate missing/zero checked/red')
        self.need(pd['non_target']['system_bridge'] == p['non_target_system_sha256'], 'non-target system mismatch')
        self.need(isinstance(pd['non_target'], dict) and bool(pd['non_target']), 'non-target manifest missing')
        for v in pd['power'].values():
            self.need(number(v) and v >= 0, 'invalid power preimage')
        self.need(set(pd['power']) == {'base','override'}, 'power preimage incomplete')
        self.need(isinstance(pd['screen'], str) and bool(pd['screen']), 'screen preimage missing')
        self.need(wd['target'] == p['target'] and wd['sha256'] == p['candidate_sha256'], 'published target/candidate mismatch')
        self.metadata(wd['metadata'])
        self.need(wd['method'] == 'same-filesystem-atomic-rename', 'publication method mismatch')
        self.need(wd['staged_device'] == pd['mapping']['device'] == wd['device'], 'cross-filesystem publication')
        self.need(Path(wd['staged_path']).parent == Path(p['target']).parent and wd['staged_path'] != p['target'], 'staging not exclusive sibling')
        self.need(positive(wd['inode']) and wd['inode'] != pd['mapping']['inode'], 'mapped inode overwritten in place')
        self.need(wd['non_target'] == pd['non_target'], 'publication changed non-target')
        self.need(any(self.commands[x['sha256']]['role']=='publish' for x in pub['commands']), 'publish command missing')
        ids1 = self.identities(ad, act['boot'])
        self.need(act['boot'] != pre['boot'], 'activation lacks new boot')
        try:
            self.mapping(ad['mapping'], ids1['child'], p['candidate_sha256'])
            self.need((ad['mapping']['device'],ad['mapping']['inode']) == (wd['device'],wd['inode']), 'activation object differs from published object')
        except (Invalid, KeyError) as e:
            self.candidate = 'activation_failed'
            self.unknown.append('activation: '+str(e))
        else:
            self.candidate = 'observed_candidate_mapping'
        initial_click = self.click(ad, act)
        self.need(number(ad['observation_end']) and pub['phase_end'] <= initial_click['start'] <= initial_click['end'] <= ad['observation_end'] <= act['phase_end'], 'activation click/observation time missing')
        self.need(ad['observation_end']-initial_click['end'] <= 120, 'activation observation exceeds120')
        if self.candidate == 'activation_failed':
            self.need(not any(k in self.events for k in UI), 'UI acceptance after activation_failed')
        else:
            previous_ids, last_end = ids1, act['phase_end']
            for i, kind in enumerate(UI):
                if kind not in self.events:
                    self.missing.append(kind)
                    continue
                r,d = self.events[kind]
                if kind == 'first_open':
                    self.need(d['click'] == ad['click'], 'activation/first_open must share one exact click receipt')
                    self.need(r['phase_start'] == initial_click['start'] and act['phase_end'] <= r['phase_end'] <= rollback['phase_start'], 'first-open aggregate coverage mismatch')
                else:
                    self.need(last_end <= r['phase_start'] <= r['phase_end'] <= rollback['phase_start'], 'UI stage order')
                last_end = r['phase_end']
                ids = self.identities(d, r['boot'])
                self.need(r['boot'] == act['boot'], 'mixed UI boot')
                self.need(ids['child'] == ids1['child'] and ids['parent'] == ids1['parent'], 'old child/parent changed; association test not established')
                self.need(self.process(d['child_after']) == ids['child'], 'UI child birth bracket mismatch')
                if kind != 'new_host_old_child':
                    self.need(ids['host'] == ids1['host'], 'same-host phase changed host')
                else:
                    self.need(ids['host'] != previous_ids['host'], 'reassociation lacks new host')
                    assoc=d['association']
                    self.need(positive(assoc['logical_before']) and assoc['logical_before']==assoc['logical_after'], 'logical identity changed/missing')
                    self.need(positive(assoc['actual_before']) and positive(assoc['actual_after']) and assoc['actual_before']!=assoc['actual_after'], 'actual identity did not change')
                    self.need(assoc['parent_after']==d['host_window_id'] and assoc['parent_before']==self.events['same_host_return'][1]['host_window_id'] and assoc['parent_before']!=assoc['parent_after'], 'window/parent mapping mismatch')
                self.mapping(d['mapping'], ids['child'], p['candidate_sha256'])
                self.need(self.object_id(d['mapping']) == self.object_id(ad['mapping']), 'UI mapped object/namespace differs from activation')
                click = self.click(d, r)
                self.need(number(d['observation_end']) and r['phase_start']<=click['start']<=click['end']<=d['observation_end']<=r['phase_end'], 'UI times missing/outside phase')
                self.need(click['start']-t0<900 and d['observation_end']-click['end']<=120, 'UI120/900 boundary')
                self.need(isinstance(d['screenshots'],list) and len(d['screenshots'])>0, 'screenshots missing')
                last=click['end']
                for shot in d['screenshots']:
                    self.need(number(shot['at']) and last<=shot['at']<=d['observation_end'], 'image time mixed/out of bounds')
                    self.image(shot['file']);last=shot['at']
                self.need(d['outcome'] in ('review_pending','failed'), 'boolean/feed PASS not accepted')
                if d['outcome']=='failed':
                    self.candidate='failed_observation'
                    self.need(not any(k in self.events for k in UI[i+1:]), 'experiment continued after failure')
                    break
                self.need(isinstance(d['touch'],list) and len(d['touch'])>=1, 'ordinary touch evidence missing')
                for touch in d['touch']:
                    self.need(touch['command'] in r['commands'], 'touch command reference missing')
                    tc=self.commands[touch['command']['sha256']]
                    self.need(touch['kind'] in ('scroll','content','video') and tc['role']=='touch' and click['end']<=tc['start']<=tc['end']<=r['phase_end'], 'touch evidence invalid')
                    self.image(touch['after_image'])
                previous_ids=ids
        self.need(any(self.commands[x['sha256']]['role']=='rollback' for x in rollback['commands']), 'rollback command missing')
        self.need(rd['target']==p['target'] and rd['sha256']==p['rollback_sha256'], 'rollback disk mismatch')
        self.metadata(rd['metadata'])
        final, fd=self.events['final']
        self.need(rollback['phase_end']<=final['phase_start'] and final['phase_end']<=unlock['phase_start'], 'cleanup order')
        ids2=self.identities(fd, final['boot'])
        self.need(final['boot']!=act['boot'], 'recovery reboot/new child missing')
        self.mapping(fd['mapping'],ids2['child'],p['rollback_sha256'])
        self.need(fd['non_target']==pd['non_target'], 'non-target restoration missing/different')
        self.need(all(number(v) and v >= 0 for v in fd['power'].values()), 'invalid restored power')
        self.need(fd['power']==pd['power'] and fd['screen']==pd['screen'], 'power/screen restoration missing/different')
        self.image(fd['screenshot'])
        self.recovery='restoration_receipts_complete'

    def result(self, packet):
        missing=sorted(set(self.missing))
        complete=not self.issues and not missing
        return {'schema':'native-validation-check/v1','receipt_binding':'internally_consistent' if complete else ('invalid' if self.issues else 'missing'),
                'status':('synthetic_valid' if self.synthetic else 'pending_review') if complete else 'pending_missing' if not self.issues else 'unverified',
                'candidate_outcome':self.candidate,'recovery':self.recovery if complete else 'recovery_required_or_unverified',
                'missing':missing,'errors':self.issues,'unknown':self.unknown,'verified_references':len(self.pins),
                'origin':packet.get('origin','unknown'),'device_validation':'unverified','visual_review':'pending_review',
                'authenticity':'not_established_by_hashes','checker_device_operations':0}


def check_directory(root, plan_path, synthetic=False):
    root=Path(root); plan_bytes=Path(plan_path).read_bytes(); plan=loads(plan_bytes)
    # Only packet.json and references rooted here are read. No directory scanning.
    packet_path=root/'packet.json'
    if not packet_path.is_file():
        interruption=root/'execution-interruption-01.json'
        retained=None
        if interruption.is_file() and not interruption.is_symlink():
            content=interruption.read_bytes()
            retained={'path':interruption.name,'sha256':digest(content),'interpretation':'interruption retained; no complete backend/device audit inferred'}
        return {'status':'pending_missing','receipt_binding':'missing','candidate_outcome':'unknown','device_validation':'unverified','interruption':retained,
                'visual_review':'pending_review','missing':['packet.json','actual_device_receipts'],'errors':[],
                'authenticity':'not_established_by_hashes','checker_device_operations':0}
    try:
        if packet_path.is_symlink(): raise Invalid('packet symlink refused')
        packet=loads(packet_path.read_bytes())
        return Checker(root,plan,digest(plan_bytes),synthetic).check(packet)
    except (ValueError,TypeError,KeyError,OSError) as e:
        return {'status':'unverified','receipt_binding':'invalid','device_validation':'unverified','visual_review':'pending_review','errors':[str(e)],'missing':[],'checker_device_operations':0}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--receipts',type=Path,required=True);p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--synthetic',action='store_true');a=p.parse_args()
    result=check_directory(a.receipts,a.plan,a.synthetic)
    print(json.dumps(result,indent=2,allow_nan=False))
    return 0 if result['receipt_binding']=='internally_consistent' else 2

if __name__=='__main__':
    raise SystemExit(main())
