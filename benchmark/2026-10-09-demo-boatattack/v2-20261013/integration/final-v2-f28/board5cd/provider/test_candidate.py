"""Real candidate derivation with explicitly synthetic capture; all transport replaced or forbidden."""
import copy,contextlib,importlib.util,io,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
os.environ.setdefault('WORKSPACES',str(next(p for p in HERE.parents if (p/'scripts/lab/lab_paths.py').is_file()).parent))
import candidate_contract as c
import prepare,installer,boat_provider as provider
import boat_identity

class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        _,_,_,old=c.sources();self.old=old
        self.boot='11111111-1111-1111-1111-111111111111'
        raw=self.root/'synthetic-raw.txt';raw.write_text('SYNTHETIC metadata fixture; NOT a device receipt\n')
        baseline=c.read(c.pinned(old['baseline319']))
        baseline.update(serial=c.SERIAL,boot_before=self.boot,boot_after=self.boot,actual=baseline['expected'],complete=True,synthetic=True)
        bp=self.root/'baseline.json';prepare.save(bp,baseline)
        from source_5cd import validate_sources
        sources=validate_sources()
        files={target:dict(exists=True,sha256=h,**sources['metadata'][target]) for target,h in c.protected().items()}
        files[c.BOAT_APK]=dict(exists=True,sha256=c.BOAT_SHA,mode='644',uid=0,gid=0,label='u:object_r:data_app_el1_file:s0')
        files.update({r['target']:copy.deepcopy(r['before']) for r in old['binds']})
        b=copy.deepcopy(old['members'][-1]['before']);source=b.pop('source');files[c.CFG]=b
        cap=dict(schema='boat-5cd-capture/v1',serial=c.SERIAL,complete=True,synthetic=True,boot_before=self.boot,boot_after=self.boot,
                 boat_package=old['boat_package'],boat_uid=20019001,raw=[c.pin(raw)],files=files,
                 cfg_source={'path':source,'sha256':b['sha256']},baseline319=c.pin(bp),root_absent={'target':c.ROOT,'exists':False},
                 route_b_directories={t:dict(mode='755',uid=20011300,gid=20011300,label='u:object_r:appdat:s0') for t in c.ROUTE_DIRS},
                 directory_after={d['target']:d['after'] for d in old['directories']})
        def raw_triplet(name,command,body,t):
            import shlex
            marker='__CAPTURE_RC_abc__';prefix=self.root/name
            receipt=prefix.with_suffix('.json');stdout=prefix.with_suffix('.stdout');stderr=prefix.with_suffix('.stderr')
            prepare.save(receipt,dict(argv=['hdc','-t',c.SERIAL,'shell','/system/bin/sh -c '+shlex.quote(command)+'; capture_rc=$?; printf "\\n'+marker+'%s\\n" "$capture_rc"'],rc=0,started=t,finished=t+1))
            stdout.write_text(body+'\n'+marker+'0\n');stderr.write_text('')
            return dict(receipt=c.pin(receipt),stdout=c.pin(stdout),stderr=c.pin(stderr))
        bundle={'name':boat_identity.PACKAGE,'uid':20019001,'applicationInfo':{'name':boat_identity.PACKAGE,'uid':20019001},'userInfo':[{'bundleName':boat_identity.PACKAGE,'uid':20019001,'bundleUserInfo':{'userId':100}}],'versionCode':1,'versionName':'0.9'}
        cap['boat_identity']=dict(boot_before=raw_triplet('id-before',boat_identity.BOOT,self.boot,1),bundle=raw_triplet('id-bundle',boat_identity.DUMP,boat_identity.PACKAGE+':\n'+json.dumps(bundle),3),boot_after=raw_triplet('id-after',boat_identity.BOOT,self.boot,5))
        self.cap=self.root/'capture.json';prepare.save(self.cap,cap)
        self.out=self.root/'package';self.plan=prepare.build(self.cap,self.out)
    def tearDown(self):self.tmp.cleanup()
    def validate(self,p):installer.validate(p,installer.core_for(p))
    def test_real_compiler_disabled_preview(self):
        self.validate(self.plan)
        self.assertEqual((len(self.plan['members']),len(self.plan['binds']),len(self.plan['preserved'])),(11,7,496))
        self.assertFalse(self.plan['execution_enabled']);self.assertEqual(self.plan['boat_uid'],20019001)
        preview=subprocess.run([sys.executable,str(HERE/'installer.py'),'--plan',str(self.out/'plan.disabled.json')],capture_output=True,text=True)
        self.assertEqual(preview.returncode,0,preview.stderr);self.assertEqual(json.loads(preview.stdout)['device_calls'],0)
        self.assertEqual((self.out/'recover-v3-boat.sh').read_bytes(),(c.pinned(c.sources()[0]['r4_plan']).parent/'recover-v3-boat.sh').read_bytes())
    def test_routeb_omission_or_absence_rejects(self):
        for mutation in ('missing','absent','metadata'):
            with self.subTest(mutation=mutation):
                p=copy.deepcopy(self.plan)
                if mutation=='missing':p['preserved'].pop(0)
                elif mutation=='absent':p['preserved'][0]['before']={'exists':False}
                else:p['preserved'][0]['before']['uid']=0
                with self.assertRaises((ValueError,KeyError)):self.validate(p)
    def test_wrong_serial_boot_and_stock_reject(self):
        for key,value in [('serial',self.old['serial']),('boot_id',self.old['boot_id']),('boat_uid',1)]:
            p=copy.deepcopy(self.plan);p[key]=value
            with self.assertRaises(ValueError):self.validate(p)
        p=copy.deepcopy(self.plan);p['binds'][0]['before']['sha256']='a'*64
        with self.assertRaises(ValueError):self.validate(p)
    def test_319_reduction_rejects(self):
        cap=c.read(self.cap);bp=c.pinned(cap['baseline319']);b=c.read(bp);b['expected'].pop(next(iter(b['expected'])));prepare.save(bp,b)
        cap['baseline319']=c.pin(bp);prepare.save(self.cap,cap)
        p=copy.deepcopy(self.plan);p['capture']=c.pin(self.cap);p['baseline319']=cap['baseline319']
        with self.assertRaises(ValueError):self.validate(p)
    def test_provider_standard_argv_preview_and_synthetic_block(self):
        p=c.read(self.out/'provider.json');dep={'schema':'demo-restore-deployment/v1','execution_enabled':False,'providers':[p]}
        expected={r['target']:r['sha256'] for r in self.plan['members']+self.plan['binds']}
        seal={'schema':'demo-seal/v1','seal_stage':'v2','serial':c.SERIAL,'synthetic':True,'files':{'overlays':expected},
              'overlay_deployments':[{'id':'boatattack','state':'active','files':[dict(target=t,sha256=h) for t,h in expected.items()]}]}
        sp=self.root/'seal.json';dp=self.root/'deployment.json';prepare.save(sp,seal);prepare.save(dp,dep)
        args=['boat_provider.py','--seal',str(sp),'--serial',c.SERIAL,'--deployment',str(dp),'--out',str(self.root/'execution')]
        with patch.object(sys,'argv',args),patch('subprocess.run',side_effect=AssertionError('NO TRANSPORT')),contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(provider.main(),0)
        self.assertEqual(json.loads(stdout.getvalue())['status'],'DISABLED_PREVIEW')
        dep['execution_enabled']=True;prepare.save(dp,dep)
        with patch.object(sys,'argv',args),patch('subprocess.run',side_effect=AssertionError('NO TRANSPORT')),contextlib.redirect_stderr(io.StringIO()):self.assertEqual(provider.main(),2)
        self.assertFalse((self.root/'execution').exists())
    def test_actual_dispatch_and_complete_receipts_required(self):
        # Fake subprocess boundary only. The real standard-argv provider and
        # its real transaction checks run; no device or real admission exists.
        for fault in ('none','member-sha','transaction','protection','rc','timeout'):
            with self.subTest(fault=fault):
                plan=copy.deepcopy(self.plan);plan['execution_enabled']=True
                pp=self.root/('plan-'+fault+'.json');prepare.save(pp,plan)
                p=c.read(self.out/'provider.json');p['prepared']=c.pin(pp)
                auth=self.root/('auth-'+fault+'.json');prepare.save(auth,{'synthetic':True});p['authorization']=c.pin(auth)
                expected={r['target']:r['sha256'] for r in plan['members']+plan['binds']}
                seal={'schema':'demo-seal/v1','seal_stage':'v2','serial':c.SERIAL,'files':{'overlays':expected},
                      'overlay_deployments':[{'id':'boatattack','state':'active','files':[dict(target=t,sha256=h) for t,h in expected.items()]}]}
                sp=self.root/('seal-'+fault+'.json');prepare.save(sp,seal)
                dp=self.root/('dep-'+fault+'.json');prepare.save(dp,{'schema':'demo-restore-deployment/v1','execution_enabled':True,'providers':[p]})
                out=self.root/('run-'+fault)
                def fake_run(argv,**kw):
                    import subprocess
                    self.assertEqual(kw['timeout'],2700)
                    self.assertEqual(argv[argv.index('--authorization-sha256')+1],c.sha(auth))
                    self.assertEqual(argv[argv.index('--action')+1],'apply')
                    if fault=='timeout':raise subprocess.TimeoutExpired(argv,2700,output=b'partial',stderr=b'timeout')
                    txn=Path(argv[argv.index('--out')+1]);txn.mkdir()
                    backups=[dict(target=r['target'],before=r['before'],backup='backup-%03d'%n if r['before']['exists'] else None,candidate_sha256=r['sha256']) for n,r in enumerate(plan['members'])]
                    prepare.save(txn/'transaction.json',dict(plan_sha256='0'*64 if fault=='transaction' else c.sha(pp),serial=c.SERIAL,boot_id=plan['boot_id'],backups=backups))
                    prepare.save(txn/'placed.json',{'state':'PLACED_ONLY','ui_accepted':False,'seal_signed':False,'reboots':0})
                    prepare.save(txn/'preserved-verified.json',dict(plan_sha256=c.sha(pp),serial=c.SERIAL,boot_id=plan['boot_id'],count=0 if fault=='protection' else len(plan['preserved']),success=True))
                    for n,r in enumerate(plan['members']):prepare.save(txn/('placed-%03d.json'%n),dict(target=r['target'],sha256='0'*64 if fault=='member-sha' and n==0 else r['sha256']))
                    return subprocess.CompletedProcess(argv,3 if fault=='rc' else 0,b'fake executor',b'')
                args=['boat_provider.py','--seal',str(sp),'--serial',c.SERIAL,'--deployment',str(dp),'--out',str(out)]
                with patch.object(sys,'argv',args),patch('subprocess.run',side_effect=fake_run):
                    self.assertEqual(provider.main(),0 if fault=='none' else 124 if fault=='timeout' else 2)
                receipt=c.read(out/'receipt.json');self.assertFalse(receipt['restored']);self.assertEqual(receipt['reboots'],0)
                if fault=='none':self.assertEqual(receipt['status'],'PLACED_PENDING_AUTHORIZED_SINGLE_BOOT')

    def test_dedicated_bms_serial_boot_and_remote_status(self):
        original=c.read(self.cap)
        for fault in ('serial','command','rc','stderr','marker','boot','time'):
            with self.subTest(fault=fault):
                cap=copy.deepcopy(original);identity=cap['boat_identity'];ref=identity['bundle']
                if fault=='boot':ref=identity['boot_after']
                receipt=c.read(c.pinned(ref['receipt']));stdout=c.pinned(ref['stdout']).read_text();stderr=''
                if fault=='serial':receipt['argv'][2]=self.old['serial']
                if fault=='command':receipt['argv'][4]=receipt['argv'][4].replace('bm dump -n','bm dump -a')
                if fault=='rc':receipt['rc']=1
                if fault=='stderr':stderr='Connect server failed'
                if fault=='marker':stdout=stdout.replace('__CAPTURE_RC_abc__0','__CAPTURE_RC_abc__1')
                if fault=='boot':stdout=stdout.replace(self.boot,self.old['boot_id'])
                if fault=='time':receipt['started']=0;receipt['finished']=1
                for key,value in [('receipt',receipt),('stdout',stdout),('stderr',stderr)]:
                    f=self.root/('uid-'+fault+'-'+key)
                    if key=='receipt':prepare.save(f,value)
                    else:f.write_text(value)
                    ref[key]=c.pin(f)
                prepare.save(self.cap,cap);plan=copy.deepcopy(self.plan);plan['capture']=c.pin(self.cap)
                with self.assertRaises(ValueError):self.validate(plan)
        prepare.save(self.cap,original)

    def test_bms_uid_one_and_live_drift_rejected(self):
        cap=c.read(self.cap);cap['boat_uid']=1;prepare.save(self.cap,cap)
        p=copy.deepcopy(self.plan);p['boat_uid']=1;p['capture']=c.pin(self.cap)
        with self.assertRaises(ValueError):self.validate(p)
        class Fake:
            def shell(_,name,command):
                if command==boat_identity.BOOT:return self.boot
                return boat_identity.PACKAGE+':'+json.dumps({'name':boat_identity.PACKAGE,'uid':1})
        with self.assertRaises(ValueError):boat_identity.fresh(self.plan,Fake())

    def test_rollback_guards_byte_preserved(self):
        old_source=(c.pinned(c.sources()[0]['r4_plan']).parent/'installer.py').read_text();new=(HERE/'installer.py').read_text()
        for name,end in [('rollback_preflight','rollback'),('rollback','main'),('no_consumers','audit_rows')]:
            start='def '+name+'(';stop='\ndef '+end+'('
            self.assertEqual(old_source.split(start)[1].split(stop)[0],new.split(start)[1].split(stop)[0])

    def test_f28_exact_runtime_rejects_old947(self):
        row=next(r for r in self.plan['binds'] if r['target']=='/system/android/lib64/liboh_android_runtime.so')
        self.assertEqual(row['sha256'],'f28bd1b3d44e2944f77911c2ad71376869f7f3ebc6dcd8434dfea869f4056db0')
        self.assertEqual(row['before']['sha256'],'18763dd4b3a48aefaaf80c9f9630b849e282175eea8da04f7918d6d2cfa3fbae')
        p=copy.deepcopy(self.plan)
        next(r for r in p['binds'] if r['target']==row['target'])['sha256']='94718e0d0b617a0f9a860e0b50b879b0d7d4639f32e8230b1f90f8e26e2c1354'
        with self.assertRaises(ValueError):self.validate(p)

    def test_unknown_worker_bytes_reject_even_rehashed(self):
        worker=self.out/'worker.sh';worker.write_text(worker.read_text()+'# foreign\n')
        p=copy.deepcopy(self.plan);next(r for r in p['members'] if r['target'].endswith('/worker.sh'))['sha256']=c.sha(worker)
        with self.assertRaises(ValueError):self.validate(p)

if __name__=='__main__':unittest.main(verbosity=2)
