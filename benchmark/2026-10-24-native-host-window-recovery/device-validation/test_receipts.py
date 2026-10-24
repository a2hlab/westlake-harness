#!/usr/bin/env python3
"""Explicit synthetic JSON observations only; creates no device commands."""
import copy
import json
from pathlib import Path
import unittest
import uuid
from check_receipts import Checker, digest, check_directory, SERIAL, UI

HERE=Path(__file__).resolve().parent
RUN=HERE/'.private'/('synthetic-'+uuid.uuid4().hex)
RUN.mkdir(parents=True)
PNG=b'\x89PNG\r\n\x1a\nSYNTHETIC-NOT-A-REAL-IMAGE'


class Fixture:
    def __init__(self):
        self.root=RUN/uuid.uuid4().hex; self.root.mkdir()
        self.n=0
        self.meta={'uid':20011206,'gid':20011206,'mode':'0644','selinux':'u:object_r:appdat:s0'}
        c=self.file(b'SYNTHETIC-CANDIDATE');b=self.file(b'SYNTHETIC-BASELINE')
        m=self.file(b'SYNTHETIC-MANIFEST');v=self.file(b'SYNTHETIC-REVIEW')
        self.plan={'serial':SERIAL,'candidate_sha256':c['sha256'],'rollback_sha256':b['sha256'],
            'review02_manifest_sha256':m['sha256'],'callback_review_sha256':v['sha256'],
            'target':'/data/app/el2/100/base/org.westlake.imehost/files/SYNTHETIC/liboh_adapter_bridge.so',
            'target_metadata':self.meta,'preimage_device':66352,'preimage_inode':560578,'non_target_system_sha256':'a'*64}
        self.plan_path=self.root/'synthetic-plan.json';self.plan_path.write_text(json.dumps(self.plan))
        self.packet={'schema':'native-validation-receipts/v1','origin':'synthetic','run_id':'SYNTHETIC-RUN','clock_id':'SYNTHETIC-MONOTONIC','serial':SERIAL,'plan_sha256':digest(self.plan_path.read_bytes()),'receipts':[]}
        self.data={};self.receipts={};self.commands={};self.clicks={}
        def identity(boot,host,child):
            return {k:{'boot':boot,'pid':p,'birth':p*100,'uid':20011206} for k,p in [('host',host),('parent',50),('child',child)]}
        ids0=identity('SYNTHETIC-BOOT0',10,20);ids1=identity('SYNTHETIC-BOOT1',11,21);ids2=identity('SYNTHETIC-BOOT2',13,22)
        non={'system_bridge':'a'*64,'other_library':'b'*64}
        self.add('lock',0,1,'SYNTHETIC-BOOT0',{'owner':'SYNTHETIC-OWNER','token':'SYNTHETIC-LOCK','held_before_rc':1,'held_before_stdout':'','acquire_rc':0})
        self.add('preflight',1,2,'SYNTHETIC-BOOT0',{**ids0,'mapping':self.mapping(ids0['child'],b['sha256'],560578),
            'candidate_file':c,'rollback_file':b,'review02_manifest':m,'callback_review':v,
            'frozen_gate':self.jsonfile({'checked':1,'violations':[]}), 'non_target':non,'power':{'base':30000,'override':10000},'screen':'SYNTHETIC-SCREEN'})
        self.add('publish',2,3,'SYNTHETIC-BOOT0',{'target':self.plan['target'],'sha256':c['sha256'],'metadata':self.meta,
            'method':'same-filesystem-atomic-rename','staged_device':66352,'device':66352,'inode':560579,
            'staged_path':str(Path(self.plan['target']).parent/'SYNTHETIC-STAGED'),'non_target':non})
        self.add('activation',3,20,'SYNTHETIC-BOOT1',{**ids1,'mapping':self.mapping(ids1['child'],c['sha256'],560579),'observation_end':20})
        self.clicks['activation']=self.command('activation-icon','SYNTHETIC-BOOT1',4,5,'icon')
        self.commands['activation'].append(self.clicks['activation'])
        for index,kind in enumerate(UI):
            start=4 if index==0 else 20+index*140;ids=copy.deepcopy(ids1)
            if index==2:ids['host']={'boot':'SYNTHETIC-BOOT1','pid':12,'birth':1200,'uid':20011206}
            self.add(kind,start,start+121,'SYNTHETIC-BOOT1',{**ids,'child_after':ids['child'],'mapping':self.mapping(ids['child'],c['sha256'],560579),
                'observation_end':start+121,'host_window_id':62 if index==2 else 32,
                'screenshots':[{'at':start+1+t,'file':self.file(PNG)} for t in (5,30,60,120)],
                'outcome':'review_pending','touch':[{'kind':'scroll','after_image':self.file(PNG)}],
                'association':{'logical_before':53,'logical_after':53,'actual_before':53,'actual_after':63,'parent_before':32,'parent_after':62}})
            self.clicks[kind]=self.clicks['activation'] if index==0 else self.command(kind+'-icon','SYNTHETIC-BOOT1',start,start+1,'icon')
            self.commands[kind].append(self.clicks[kind])
            self.commands[kind].append(self.command(kind+'-touch','SYNTHETIC-BOOT1',start+100,start+101,'touch'))
        self.add('rollback',500,510,'SYNTHETIC-BOOT1',{'target':self.plan['target'],'sha256':b['sha256'],'metadata':self.meta})
        self.add('final',510,520,'SYNTHETIC-BOOT2',{**ids2,'mapping':self.mapping(ids2['child'],b['sha256'],560580),
            'non_target':non,'power':{'base':30000,'override':10000},'screen':'SYNTHETIC-SCREEN','screenshot':self.file(PNG)})
        self.add('unlock',520,521,'SYNTHETIC-BOOT2',{'owner':'SYNTHETIC-OWNER','token':'SYNTHETIC-LOCK','release_rc':0,'held_after_rc':1,'held_after_stdout':''})

    def file(self, data):
        self.n+=1;p=self.root/(f'synthetic-{self.n:04}.raw');p.write_bytes(data)
        return {'path':p.name,'sha256':digest(data)}

    def jsonfile(self,x):return self.file(json.dumps(x).encode())

    def mapping(self,child,sha,inode):
        return {'child_before':copy.deepcopy(child),'child_after':copy.deepcopy(child),'mapped_path':'/data/local/tmp/asx/liboh_adapter_bridge.so',
            'backing_path':self.plan['target'],'mount_namespace':'mnt:SYNTHETIC-'+child['boot'],'device':66352,'inode':inode,'sha256':sha,
            'process_root_stat':{'mount_namespace':'mnt:SYNTHETIC-'+child['boot'],'device':66352,'inode':inode,'sha256':sha,'metadata':copy.deepcopy(self.meta)}}

    def add(self,kind,start,end,boot,data):
        identity={k:self.packet[k] for k in ('origin','run_id','clock_id','serial')}
        self.data[kind]={**identity,'kind':kind,'boot':boot,'body_errors':[],**copy.deepcopy(data)}
        self.receipts[kind]={**identity,'kind':kind,'boot':boot,'phase_start':start,'phase_end':end}
        role=kind if kind in ('publish','rollback') else 'read'
        self.commands[kind]=[self.command(kind+'-observation',boot,end-0.5,end,role)]

    def command(self,name,boot,start,end,role):
        return {**{k:self.packet[k] for k in ('origin','run_id','clock_id','serial')},'boot':boot,
            'command_id':'SYNTHETIC-'+name,'start':start,'end':end,'role':role,'write':role!='read',
            'argv':['SYNTHETIC-OBSERVATION-NOT-EXECUTABLE',name],'transport_rc':0,'remote_rc':0,'body_errors':[],
            'stdout':self.file(b'SYNTHETIC raw bytes, not HDC output'), 'stderr':self.file(b'')}

    def shift(self,kind,delta):
        self.receipts[kind]['phase_start']+=delta;self.receipts[kind]['phase_end']+=delta
        for c in self.commands[kind]:c['start']+=delta;c['end']+=delta
        d=self.data[kind]
        if 'observation_end' in d:d['observation_end']+=delta
        for shot in d.get('screenshots',[]):shot['at']+=delta

    def check(self):
        self.packet['receipts']=[];cache={}
        def ref(c):
            if id(c) not in cache:cache[id(c)]=self.jsonfile(c)
            return cache[id(c)]
        for k,r in self.receipts.items():
            r['commands']=[ref(c) for c in self.commands[k]]
            d=copy.deepcopy(self.data[k])
            if k in self.clicks:d['click']=ref(self.clicks[k])
            for t in d.get('touch',[]):
                t['command']=ref(next(c for c in self.commands[k] if c['role']=='touch'))
            r['observations']=self.jsonfile(d);self.packet['receipts'].append(self.jsonfile(r))
        (self.root/'packet.json').write_text(json.dumps(self.packet))
        return check_directory(self.root,self.plan_path,synthetic=True)


class ReceiptTests(unittest.TestCase):
    def reject(self,f):
        r=f.check();self.assertNotEqual(r['receipt_binding'],'internally_consistent',r);self.assertEqual(r['device_validation'],'unverified');return r

    def test_01_complete_synthetic_is_never_device_pass(self):
        f=Fixture();r=f.check();self.assertEqual(r['status'],'synthetic_valid',r)
        self.assertEqual(r['visual_review'],'pending_review');self.assertEqual(r['device_validation'],'unverified')
        self.assertEqual(r['authenticity'],'not_established_by_hashes')

    def test_02_serial_candidate_metadata_and_backing(self):
        for target,key,value in [('packet','serial','WRONG'),('publish','sha256','0'*64),('publish','target','/wrong'),('preflight','mapping',{})]:
            with self.subTest(key=key):
                f=Fixture();(f.packet if target=='packet' else f.data[target])[key]=value;self.reject(f)
        f=Fixture();f.data['publish']['metadata']['mode']='0777';self.reject(f)
        f=Fixture();f.data['preflight']['candidate_file']['sha256']='0'*64;self.reject(f)
        f=Fixture();f.data['publish']['inode']=560578;self.reject(f)

    def test_03_activation_failed_with_complete_rollback_is_valid_not_repaired(self):
        for mutation in ('sha','inode','birth'):
            with self.subTest(mutation=mutation):
                f=Fixture();m=f.data['activation']['mapping']
                if mutation=='sha':m['sha256']=m['process_root_stat']['sha256']=f.plan['rollback_sha256']
                if mutation=='inode':m['process_root_stat']['inode']+=1
                if mutation=='birth':m['child_after']['birth']+=1
                for k in UI:del f.receipts[k]
                r=f.check();self.assertEqual(r['receipt_binding'],'internally_consistent',r);self.assertEqual(r['candidate_outcome'],'activation_failed');self.assertEqual(r['recovery'],'restoration_receipts_complete')
        f=Fixture();f.data['activation']['mapping']['sha256']='0'*64;self.reject(f)
        f=Fixture();f.data['publish']['inode']+=7
        for k in UI:del f.receipts[k]
        r=f.check();self.assertEqual(r['candidate_outcome'],'activation_failed',r)
        f=Fixture();m=f.data['same_host_return']['mapping'];m['inode']+=1;m['process_root_stat']['inode']+=1;self.reject(f)
        f=Fixture();m=f.data['same_host_return']['mapping'];m['mount_namespace']='OTHER';m['process_root_stat']['mount_namespace']='OTHER';self.reject(f)


    def test_04_rc_and_body_errors_never_hidden(self):
        for field,value in [('transport_rc',1),('remote_rc',1),('remote_rc',None),('remote_rc',True)]:
            with self.subTest(field=field,value=value):
                f=Fixture();f.commands['publish'][0][field]=value;self.reject(f)
        f=Fixture();f.commands['publish'][0]['body_errors']=['illegal'];self.reject(f)

    def test_05_missing_and_mixed_run_clock_or_birth(self):
        for field in ('run_id','clock_id','boot'):
            f=Fixture();f.receipts['activation'][field]='OTHER';self.reject(f)
        f=Fixture();del f.receipts['activation']['phase_start'];self.reject(f)
        f=Fixture();del f.data['preflight']['child']['birth'];self.reject(f)
        f=Fixture();f.data['new_host_old_child']['child_after']['birth']+=1;self.reject(f)
        f=Fixture();f.data['new_host_old_child']['child']['pid']+=1;self.reject(f)

    def test_06_same_host_vs_new_host_and_ids(self):
        f=Fixture()
        for d in f.data.values():
            if 'parent' in d:d['parent']['uid']=0
        self.assertEqual(f.check()['receipt_binding'],'internally_consistent')
        f=Fixture();f.data['new_host_old_child']['host']['pid']=11 # PID reused, birth1200 differs from1100
        self.assertEqual(f.check()['receipt_binding'],'internally_consistent')

        f=Fixture();f.data['same_host_return']['host']['pid']=99;self.reject(f)
        f=Fixture();f.data['new_host_old_child']['host']=copy.deepcopy(f.data['same_host_return']['host']);self.reject(f)
        for key in ('logical_after','parent_after'):
            f=Fixture();f.data['new_host_old_child']['association'][key]=99;self.reject(f)
        f=Fixture();f.data['new_host_old_child']['association']['actual_after']=53;self.reject(f)

    def test_07_time_120_and_finite_numeric(self):
        f=Fixture();self.assertEqual(f.check()['status'],'synthetic_valid') # exactly120 allowed
        f=Fixture();f.data['first_open']['observation_end']=126;f.receipts['first_open']['phase_end']=126;self.reject(f) #121
        for value in (float('nan'),float('inf'),True,-1):
            f=Fixture();f.commands['publish'][0]['start']=value;self.reject(f)
        f=Fixture();f.data['same_host_return']['screenshots'][0]['at']=1;self.reject(f)
        f=Fixture();other=f.command('SECOND-FIRST-CLICK','SYNTHETIC-BOOT1',6,7,'icon')
        f.commands['first_open'][1]=other;f.clicks['first_open']=other;self.reject(f)


    def test_08_window_deadlines_900_1200_1800(self):
        f=Fixture();f.shift('new_host_old_child',600)
        for k in ('rollback','final','unlock'):f.shift(k,600)
        self.reject(f)
        f=Fixture();f.shift('new_host_old_child',599)
        for k in ('rollback','final','unlock'):f.shift(k,600)
        # Touch beyond900 is separately a new command and is rejected.
        self.reject(f)
        for value,expected in [(1199,True),(1200,False)]:
            f=Fixture()
            for k in ('rollback','final','unlock'):f.shift(k,value-500)
            self.assertEqual(f.check()['receipt_binding']=='internally_consistent',expected)
        for value,expected in [(1800,True),(1800.01,False)]:
            f=Fixture();f.receipts['unlock']['phase_end']=value;self.assertEqual(f.check()['receipt_binding']=='internally_consistent',expected)

    def test_09_every_write_inside_lock_and_no_duplicates(self):
        f=Fixture();f.receipts['lock']['phase_end']=2.5;self.reject(f)
        f=Fixture();f.receipts['unlock']['phase_start']=505;self.reject(f)
        f=Fixture();f.commands['publish'][0]['write']=False;self.reject(f)
        f=Fixture();r=f.check();f.packet['receipts'].append(f.packet['receipts'][2]);self.assertNotEqual(Checker(f.root,f.plan,f.packet['plan_sha256'],True).check(f.packet)['receipt_binding'],'internally_consistent')

    def test_10_full_rollback_chain_required(self):
        for field in ('mapping','non_target','power','screenshot','screen'):
            f=Fixture();del f.data['final'][field];self.reject(f)
        f=Fixture();f.data['final']['mapping']['sha256']=f.plan['candidate_sha256'];self.reject(f)
        f=Fixture();f.data['final']['mapping']['child_after']['birth']+=1;self.reject(f)
        f=Fixture();f.data['final']['power']['override']+=1;self.reject(f)
        f=Fixture();f.data['final']['non_target']['system_bridge']='0'*64;self.reject(f)
        f=Fixture();f.data['unlock']['held_after_rc']=0;self.reject(f)
        f=Fixture();f.data['unlock']['held_after_rc']=True;self.reject(f)
        f=Fixture();del f.receipts['rollback'];self.assertIn('rollback',self.reject(f)['missing'])

    def test_11_references_and_boolean_pass_are_insufficient(self):
        f=Fixture();f.data['final']['screenshot']['sha256']='0'*64;self.reject(f)
        f=Fixture();f.data['final']['screenshot']={'path':'../outside','sha256':'0'*64};self.reject(f)
        f=Fixture();(f.root/'link.raw').symlink_to(f.root/f.data['final']['screenshot']['path']);f.data['final']['screenshot']['path']='link.raw';self.reject(f)
        f=Fixture();f.data['first_open']['outcome']='PASS';self.reject(f)
        f=Fixture();f.data['first_open']['screenshots']=[];f.data['first_open']['PASS']=True;self.reject(f)
        f=Fixture();f.data['preflight']['frozen_gate']=f.jsonfile({'checked':0,'violations':[]});self.reject(f)

    def test_12_failed_observation_and_missing_actual(self):
        f=Fixture();f.data['first_open']['outcome']='failed'
        for k in UI[1:]:del f.receipts[k]
        r=f.check();self.assertEqual(r['receipt_binding'],'internally_consistent',r);self.assertEqual(r['candidate_outcome'],'failed_observation')
        f=Fixture();(f.root/'execution-interruption-01.json').write_text('{"status":"SYNTHETIC_INTERRUPTED"}')
        r=check_directory(f.root,f.plan_path,True);self.assertEqual(r['status'],'pending_missing');self.assertEqual(r['device_validation'],'unverified');self.assertIsNotNone(r['interruption'])
        f=Fixture();f.packet['receipts']=[];r=Checker(f.root,f.plan,f.packet['plan_sha256'],True).check(f.packet);self.assertIn('activation',r['missing'])


if __name__=='__main__':
    print('SYNTHETIC ONLY: '+str(RUN),flush=True)
    unittest.main(verbosity=2)
