#!/usr/bin/env python3
import hashlib, json, os, shutil, subprocess, tempfile, unittest, zipfile, zlib
from pathlib import Path
from prepare import HERE, ROOT, OH, REL, sha, current_function, candidate_function

class Walls(unittest.TestCase):
    def test_inputs(self):
        expected={'fd-seal':'7070a3d4f079046912b4b8dde4edc8d1ef6eade3c9c98b02bfcaba3669c11d98',
                  'x':'5e9c8e4bbb525a2140292f8f96ab6cc0af403dfcd07667b8678aebb44fb52354',
                  'toutiao':'a1112a0c941f865847c2fab9138cf815735268fbfcd41d697412fb80992c7395'}
        for x in json.loads((HERE/'evidence/inputs.json').read_text()):
            self.assertEqual(sha(x['path']),expected[x['key']])
        logs=ROOT/'benchmark/2026-09-28-bms-label-resolve/evidence/b3-onboard'
        for key,size in [('x',99625),('toutiao',242663)]:
            text=(logs/(key+'-hilog.txt')).read_text()
            self.assertIn(f'JSON output ({size} bytes) exceeds buffer (65536 bytes)',text)
            self.assertTrue(any('-2005' in line and 'manifest' in line for line in text.splitlines()))
        self.assertIn('ec=8519936',(logs/'fd-seal-hilog.txt').read_text())
        rows=json.loads((HERE/'evidence/seal-payloads.json').read_text())
        self.assertEqual(len(rows),9)
        self.assertEqual([Path(x['entry']).name for x in rows if x['magic'].startswith('504b')],
                         ['libaria2c.zip.so','libffmpeg.zip.so','libpython.zip.so'])
        for r in rows:
            if 'inner_entry_count' in r:self.assertIsNone(r['inner_bad_crc_entry'])

    def test_candidate(self):
        original=current_function()
        exceptions=json.loads((HERE/'native-data-exceptions.json').read_text())
        candidate=candidate_function(original,exceptions)
        lambdas=candidate[candidate.index('    auto checkElf ='):candidate.index('\n    ExtractParam fileParam')]
        with tempfile.TemporaryDirectory(prefix='b77-regression-') as tmp:
            td=Path(tmp);cpp=td/'predicate.cpp';exe=td/'predicate'
            cpp.write_text((HERE/'host_prefix.cpp').read_text()+lambdas+
                '\n bool ok=mode=="old" ? checkElf(path) : verifyOutput(path,entry,name);\n'
                ' std::cout<<(ok ? "accept" : "reject")<<"\\n";return ok?0:1;\n}\n')
            subprocess.run(['c++','-std=c++17','-Wno-deprecated-declarations',str(cpp),'-lz','-o',str(exe)],check=True,capture_output=True)
            cases=[]
            def check(data,name,ok,mode='new',bundle='com.junkfood.seal',abi='arm64-v8a',
                      size=None,crc=None,uid=0,gid=0,perm=0o755,symlink=False):
                path=td/name;path.unlink(missing_ok=True);path.write_bytes(data);path.chmod(perm)
                tested=path
                if symlink:
                    tested=td/'link';tested.unlink(missing_ok=True);tested.symlink_to(path)
                args=[str(exe),mode,str(tested),name,bundle,abi,str(len(data) if size is None else size),
                      str(zlib.crc32(data) if crc is None else crc),str(uid),str(gid)]
                p=subprocess.run(args,capture_output=True,text=True)
                self.assertIn(p.returncode,[0,1],p.stderr);self.assertEqual(p.returncode==0,ok,args)
                cases.append({'name':name,'mode':mode,'expected_accept':ok,'actual':p.stdout.strip(),
                    'abi':abi,'bundle':bundle,'uid':uid,'gid':gid,'mode_bits':oct(perm),
                    'size_override':size,'crc_override':crc,'symlink':symlink})
            seal=Path(json.loads((HERE/'evidence/inputs.json').read_text())[0]['path'])
            with zipfile.ZipFile(seal) as z:
                payloads={Path(i.filename).name:z.read(i) for i in z.infolist()
                          if i.filename.startswith('lib/arm64-v8a/') and i.filename.endswith('.so')}
            for name,data in sorted(payloads.items()):
                check(data,name,not name.endswith('.zip.so'),'old')
                check(data,name,True)
            name='libaria2c.zip.so';data=payloads[name]
            check(data[:-1]+bytes([data[-1]^1]),name,False) # CRC recomputed: SHA exception must reject
            check(data[:100],name,False)
            check(data,'libunknown.zip.so',False)
            check(data,name,False,bundle='different.app')
            check(data,name,False,abi='armeabi-v7a')
            for kw in [{'size':len(data)+1},{'crc':0},{'uid':1000},{'gid':1000},{'perm':0o644},{'symlink':True}]:
                check(data,name,False,**kw)
            elf=payloads['libaria2c.so']
            for off,value in [(4,1),(5,2),(6,3),(16,2),(18,62),(20,2)]:
                bad=bytearray(elf);bad[off]=value;check(bytes(bad),'libbad.so',False)
            zero=bytearray(elf);zero[6]=0;check(bytes(zero),'libvendor.so',True)
            toutiao=Path(json.loads((HERE/'evidence/inputs.json').read_text())[2]['path'])
            with zipfile.ZipFile(toutiao) as z:arm32=z.read('lib/arm64-v8a/libcvt.so')
            check(arm32,'libcvt.so',False,'old',bundle='com.ss.android.article.news')
            check(arm32,'libcvt.so',True,bundle='com.ss.android.article.news')
            check(arm32,'libcvt.so',False,bundle='different.app')
            check(arm32[:-1]+bytes([arm32[-1]^1]),'libcvt.so',False,bundle='com.ss.android.article.news')
            # Exercise the producer's exact capacity expression including its terminating NUL.
            producer=(ROOT/'bms/src/adapter/framework/package-manager/jni/oh_adapter_install_apk_c_entry.cpp').read_text()
            self.assertIn('static_cast<int>(jsonText.size()) + 1 > outJsonBufSize',producer)
            capsrc=td/'cap.cpp'
            capsrc.write_text('#include <string>\nint main(int argc,char** argv){ std::string jsonText(std::stoul(argv[1]),\'x\'); int outJsonBufSize=std::stoi(argv[2]);return static_cast<int>(jsonText.size()) + 1 > outJsonBufSize ? 1:0;}\n')
            subprocess.run(['c++',str(capsrc),'-o',str(td/'cap')],check=True,capture_output=True)
            caps=[]
            for cap in [65536,1048576]:
                for n in [2245,99625,242663,cap-1,cap,cap+1]:
                    p=subprocess.run([str(td/'cap'),str(n),str(cap)])
                    self.assertEqual(p.returncode,int(n+1>cap));caps.append({'json_bytes':n,'capacity':cap,'accepted':p.returncode==0})
            # Apply the actual deliverable patches to temporary files. No source tree writes.
            for relative,content,patch in [
                (REL/'base_bundle_installer.cpp',(OH/REL/'base_bundle_installer.cpp').read_text(),'0001-reuse-manifest-1mib.patch'),
                (REL/'installd/installd_operator.cpp',original,'0002-native-exact-payloads.patch')]:
                p=td/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)
                q=subprocess.run(['patch','--batch','-p1','-i',str(HERE/'patches'/patch)],cwd=td,capture_output=True,text=True)
                self.assertEqual(q.returncode,0,q.stdout+q.stderr)
                if 'installd/' in str(relative):self.assertEqual(p.read_text(),candidate)
                else:self.assertIn('constexpr int kJsonBufSize = 1024 * 1024;',p.read_text())
            (HERE/'evidence/host-regressions.json').write_text(json.dumps({
                'platform':'Darwin host, real candidate lambdas; uid/gid fixture injection only',
                'compiler':subprocess.check_output(['c++','--version'],text=True).splitlines()[0],
                'candidate_cases':cases,'capacity_cases':caps,
                'native_case_count':len(cases),'capacity_case_count':len(caps),
                'limitations':['Full OH service not linked','OH ownership, SELinux and fsync not executed',
                    'No installation, process or screen success claimed']},indent=2)+'\n')

    def test_impact(self):
        scan=json.loads((HERE/'evidence/apk-scan.json').read_text())
        by={x['key']:x for x in scan['apps']}
        self.assertGreaterEqual(len(by),23)
        self.assertEqual(len(by['fd-seal']['strict_rejected']),3)
        self.assertEqual(by['fd-seal']['candidate_rejected'],[])
        self.assertEqual(by['toutiao']['candidate_rejected'],[])
        for key in ['x','toutiao']:
            self.assertEqual(by[key]['manifest_old_capacity'],'reject')
            self.assertEqual(by[key]['manifest_new_capacity'],'fit')
        for r in by.values():self.assertEqual(r['install_after_patch'],'unverified')
        source=(ROOT/'bms/src/adapter/ohos_patches'/REL/'base_bundle_installer.cpp.patch').read_text()
        self.assertIn('constexpr int kJsonBufSize = 1024 * 1024;',source)
        old=Path('/Users/zhaoyue/orca/00.Workspace/src/adapter/framework/package-manager/jni/apk_installer.cpp').read_text()
        extraction=old[old.index('bool ApkInstaller::ExtractNativeLibs'):old.index('bool ApkInstaller::ExtractNativeLibs')+7000]
        self.assertIn('chmod',extraction)
        staging=(ROOT/'benchmark/2026-09-27-device-provisioning/provision_toutiao.sh').read_text()
        self.assertIn('source-host.hap',staging);self.assertIn('tt-rt.tar',staging)
        for e in json.loads((HERE/'native-data-exceptions.json').read_text()):
            self.assertEqual(e['status'],'draft');self.assertIsNone(e['approved_by'])

if __name__=='__main__':unittest.main()
