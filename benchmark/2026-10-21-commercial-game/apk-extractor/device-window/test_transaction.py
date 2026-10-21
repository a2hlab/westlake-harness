import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from policy import TARGETS,ORIGINAL,CANDIDATE,Refuse
from transaction import transact,TransportUnknown,validate_kit
class Transactions(unittest.TestCase):
    def exercise(self,unknown):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);cfg={'bindings':dict(kit=tmp,transaction='test',holder='outer 1 time'),'expected_boot':'boot'}
            commands=[];rw=[False]
            class Board:
                def shell(self,cmd):
                    commands.append(cmd)
                    if cmd=='mount -o rw,remount /':
                        rw[0]=True
                        if not unknown:raise Refuse('known remote failure despite rw')
                    if cmd.startswith('cp -p ') and unknown:raise TransportUnknown('lost remote status during replacement')
                    if cmd=='mount -o ro,remount /':rw[0]=False
                    return 0,('/dev/x / ext4 '+('rw' if rw[0] else 'ro')+',relatime 0 0') if cmd=='cat /proc/mounts' else ''
                def send(self,*args):commands.append('send')
            class Provider:
                REMOTE=''
                @classmethod
                def backup_name(cls,p):return cls.REMOTE+'/backup/'+p.replace('/','_')
                @staticmethod
                def checked_hashes(board,paths):return {p:CANDIDATE if p.endswith('/libinstalls.z.so') and p.startswith('/data/') and '/backup/' not in p else ORIGINAL for p in paths}
            def save(p,d):Path(p).write_text(json.dumps(d))
            with patch('transaction.validate_kit',return_value={}):
                with self.assertRaises(TransportUnknown if unknown else Refuse):transact('apply',Board(),Provider,cfg,root,root,save,lambda p:ORIGINAL)
            state=json.loads((root/'g13-transaction.json').read_text())
            if unknown:
                self.assertTrue(state['transport_unknown']);self.assertNotIn('mount -o ro,remount /',commands)
                self.assertEqual(sum(x.startswith('cp -p ') for x in commands),1)
                with patch('transaction.validate_kit',return_value={}),self.assertRaises(Refuse):transact('rollback',Board(),Provider,cfg,root,root,save,lambda p:ORIGINAL)
                self.assertEqual(sum(x.startswith('cp -p ') for x in commands),1)
            else:self.assertIn('mount -o ro,remount /',commands);self.assertFalse(rw[0])
    def test_unknown_has_no_compensation_or_unreviewed_restore(self):self.exercise(True)
    def test_failed_rw_command_still_reseals(self):self.exercise(False)
    def test_kit_extra_library_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'manifest.json').write_text(json.dumps({'baseline':{'libinstalls.z.so':ORIGINAL},'candidate':{'libinstalls.z.so':CANDIDATE,'libbms.z.so':CANDIDATE}}))
            with self.assertRaises(Refuse):validate_kit(p,lambda p:CANDIDATE)
