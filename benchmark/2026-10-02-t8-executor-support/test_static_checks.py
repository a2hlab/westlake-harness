"""Known rejection paths at composition/preflight, without boards or binary tools."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/lab'))
import generation_static_checks as s
import u7_executor as u


def site(pc='0x1000',namespace='caller-default'):
    return dict(function='Open',callee='dlopen_ns',namespace=[namespace],path=['libx.so'],flags=['NOW'],tail_call=False,pc=pc)


class StaticChecks(unittest.TestCase):
    def test_relinked_pcs_do_not_hide_or_invent_sites(self):
        self.assertEqual(s.site_delta([site()],[site('0x2000')]),dict(added=[],removed=[]))
        changed=s.site_delta([site()],[site('0x2000','sealed')])
        self.assertEqual(len(changed['added']),1);self.assertEqual(len(changed['removed']),1)
        self.assertEqual(len(s.site_delta([site()],[site(),site()])['added']),1)

    def roots(self,td,suffix,payload):
        base,new=Path(td)/'base',Path(td)/'new'
        base.mkdir();new.mkdir()
        (base/'member').write_bytes(payload);(new/'member').write_bytes(payload+b'new')
        for root in (base,new):(root/'bundle.json').write_text('{}')
        target='/system/android/framework/a.jar' if suffix=='.jar' else '/system/bin/appspawn-x'
        # File suffix is significant for JAR dispatch.
        for root in (base,new):(root/'member').rename(root/('member'+suffix))
        old={target:dict(source='member'+suffix,target=target,sha256=s.bundle.sha(base/('member'+suffix)))}
        changed={target:dict(source='member'+suffix,target=target,sha256=s.bundle.sha(new/('member'+suffix)))}
        return base,new,target,old,changed

    def test_changed_jar_uses_explicit_deployed_and_frozen(self):
        with tempfile.TemporaryDirectory() as td:
            base,new,target,a,b=self.roots(td,'.jar',b'jar')
            commands=[]
            def run(argv):commands.append(argv);return dict(exit_code=1,stdout='FROZEN missing',stderr='')
            with patch.object(s,'effective',side_effect=[a,b]),patch.object(s,'command',side_effect=run),patch('deployed_class_diff.classes',return_value={'Lx;':('LObject;',())}):
                report=s.check(new,base)
            self.assertEqual(report['status'],'REJECT')
            self.assertIn('--frozen',commands[0]);self.assertIn('--deployed',commands[0])
            self.assertEqual(commands[0][commands[0].index('--deployed')+1],str((base/'member.jar').resolve()))

    def test_drop_approval_requires_exact_pair_and_descriptors(self):
        with tempfile.TemporaryDirectory() as td:
            base,new,target,a,b=self.roots(td,'.jar',b'jar')
            grant=dict(allow_drop=['Ladapter/activity/J10eWebView$WlCookieManager;'],
                       candidate_sha256=b[target]['sha256'],deployed_sha256=a[target]['sha256'],
                       approved_by='outer(claude)',evidence=['board ACK + 8214ec53b4'])
            variants=[(grant,'PASS'),(dict(grant,candidate_sha256='0'*64),'REJECT'),
                      (dict(grant,deployed_sha256='0'*64),'REJECT'),
                      (dict(grant,allow_drop=['Ladapter/activity/J10eWebView$']),'REJECT'),
                      (dict(grant,evidence=[]),'REJECT')]
            for allowance,status in variants:
                with self.subTest(allowance=allowance),patch.object(s,'effective',side_effect=[a,b]),patch.object(s,'command',return_value=dict(exit_code=0,stdout='',stderr='')) as cmd,patch('deployed_class_diff.classes',return_value={'Lx;':('LObject;',())}):
                    self.assertEqual(s.check(new,base,{'jars':{target:allowance}})['status'],status)
                    if status=='REJECT':cmd.assert_not_called()

    def test_empty_dex_never_passes(self):
        with tempfile.TemporaryDirectory() as td:
            base,new,_,a,b=self.roots(td,'.jar',b'jar')
            with patch.object(s,'effective',side_effect=[a,b]),patch.object(s,'command',return_value=dict(exit_code=0,stdout='',stderr='')),patch('deployed_class_diff.classes',return_value={}):
                self.assertEqual(s.check(new,base)['status'],'REJECT')

    def test_new_namespace_requires_exact_review_even_if_scan_exits_zero(self):
        with tempfile.TemporaryDirectory() as td:
            base,new,target,a,b=self.roots(td,'.so',b'\x7fELF')
            scans=[dict(binaries=[dict(sites=[site()])],findings=[],namespace_api_calls={},namespace_literals=[]),
                   dict(binaries=[dict(sites=[site(namespace='sealed')])],findings=[],namespace_api_calls={},namespace_literals=[])]
            with patch.object(s,'effective',side_effect=[a,b]),patch.object(s,'scan',side_effect=scans):report=s.check(new,base)
            self.assertEqual(report['status'],'REJECT');self.assertEqual(report['members'][0]['status'],'REVIEW_REQUIRED')
            row=report['members'][0]
            approval={k:row[k] for k in ('deployed_sha256','candidate_sha256','delta_sha256')}
            approval.update(approved_by='outer(claude)',evidence=['approved site'])
            with patch.object(s,'effective',side_effect=[a,b]),patch.object(s,'scan',side_effect=scans):
                self.assertEqual(s.check(new,base,{'native':{target:approval}})['status'],'PASS')

    def test_namespace_allowlist_change_is_reported_without_new_open(self):
        with tempfile.TemporaryDirectory() as td:
            base,new,_,a,b=self.roots(td,'.so',b'\x7fELF')
            scans=[dict(binaries=[dict(sites=[])],findings=[],namespace_api_calls={},namespace_literals=['libone.so:libtwo.so']),
                   dict(binaries=[dict(sites=[])],findings=[],namespace_api_calls={},namespace_literals=['libone.so'])]
            with patch.object(s,'effective',side_effect=[a,b]),patch.object(s,'scan',side_effect=scans):report=s.check(new,base)
            self.assertEqual(report['status'],'REJECT')
            self.assertEqual(report['members'][0]['open_site_delta']['namespace_literal_changes']['removed'],['libone.so:libtwo.so'])

    def test_preflight_missing_static_gate_refuses_before_device_or_image(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'bundle.json').write_text(json.dumps({'image_gate_reference':{}}))
            with patch.object(u,'prepare',return_value={}),patch.object(u,'policy_binding',return_value='x'),patch.object(u.bundle,'image_checks') as image,patch.object(u,'DeviceIO') as device:
                with self.assertRaisesRegex(RuntimeError,'static checks'):u.preflight(root,root/'base',None)
                image.assert_not_called();device.assert_not_called()


if __name__=='__main__':unittest.main()
