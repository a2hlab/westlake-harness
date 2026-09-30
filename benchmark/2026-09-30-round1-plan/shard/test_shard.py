import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from shard_plan import balance, historical_costs, cohort
from merge_facts import merge, format_facts, processes, validate_partition


class SplitTests(unittest.TestCase):
    def test_lpt_balances_long_and_short_jobs_with_equal_counts(self):
        costs=[{'key':chr(97+i),'estimated_seconds':v} for i,v in enumerate([9,8,7,6,5,4])]
        result=balance(costs)
        self.assertEqual([s['estimated_seconds'] for s in result],[13,13,13])
        self.assertEqual([len(s['keys']) for s in result],[2,2,2])
        self.assertEqual(balance(list(reversed(costs))),result)

    def test_exact_66_key_cover(self):
        values=[{'key':'app'+str(i),'estimated_seconds':i+1} for i in range(66)]
        shards=balance(values)
        self.assertEqual([len(s['keys']) for s in shards],[22,22,22])
        self.assertEqual(len({k for s in shards for k in s['keys']}),66)

    def test_bad_cost_and_duplicate_key_rejected(self):
        for values in [[{'key':'a','estimated_seconds':float('nan')}],
                       [{'key':'a','estimated_seconds':0}],
                       [{'key':'a','estimated_seconds':1}]*2]:
            with self.assertRaises(ValueError):balance(values)

    def test_timing_proxy_and_unmeasured_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'baseline.json').write_text('{}')
            rows=[dict(key=k,serial='s',boot_id='b',apk_sha256=k,clicked=clicked,clicked_at=start,finished_at=end)
                  for k,clicked,start,end in [('a',True,10,20),('b',True,21,30),('c',False,None,31)]]
            (p/'summary.json').write_text(json.dumps({'records':rows}))
            costs,_=historical_costs([{'key':k,'apk_sha256':k} for k in 'abc'],[p])
            self.assertEqual([r['estimated_seconds'] for r in costs],[10,10,10])
            self.assertEqual([r['basis'] for r in costs],['cohort_median_fallback','historical_completion_interval','cohort_median_fallback'])

    def test_unknown_history_and_apk_mismatch_do_not_borrow_cost(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'baseline.json').write_text('{}')
            (p/'summary.json').write_text(json.dumps({'records':[
                dict(key='z',serial='s',boot_id='b',finished_at=10),
                dict(key='a',serial='s',boot_id='b',finished_at=999,clicked=True,apk_sha256='other')]}))
            costs,_=historical_costs([{'key':'a','apk_sha256':'wanted'}],[p],fallback=55)
            self.assertEqual(costs[0]['estimated_seconds'],55)

    def test_duplicate_input_keys_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'keys.txt';p.write_text('a\na\n')
            with self.assertRaises(ValueError):cohort(p)


class MergeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.plan={'expected_keys':list('abc'),'expected_apk_sha256':{k:k*64 for k in 'abc'},
                   'shards':[{'name':k,'serial':'serial-'+k,'keys':[k]} for k in 'abc']}
        self.mapping={};self.profile={'/system/runtime.so':'a'*64}
        for key in 'abc':
            run=self.root/key;folder=run/key;folder.mkdir(parents=True);self.mapping[key]=run
            fp='a'*64+'  /system/runtime.so\n';short=hashlib.sha256(fp.strip().encode()).hexdigest()[:12]
            (run/'runtime-fingerprint.txt').write_text(fp)
            (run/'baseline.json').write_text(json.dumps({'boot_id':'boot-'+key,'runtime_fingerprint':short}))
            (run/'facts.txt').write_text('RUNTIME fingerprint='+short+' files=1 (fixture)\nFROZEN checked=4 violations=0\nTOTAL deliberately wrong fixture counts=999\n')
            record=dict(key=key,serial='serial-'+key,boot_id='boot-'+key,package='pkg.'+key,apk_sha256=key*64,
                        finished_at=10,status='done',bms={'uid':100},screenshots=[{'captured':True},{'captured':False}])
            (folder/'record.json').write_text(json.dumps(record))
            (folder/'processes-t5.txt').write_text('UID PID PPID NAME\n100 10 1 appspawn-x\n100 11 1 render-helper\n101 12 1 appspawn-x\n')
            (folder/'processes-t20.txt').write_text('UID PID PPID NAME\n100 11 1 render-helper\n')

    def change_record(self,key,**updates):
        p=self.mapping[key]/key/'record.json';r=json.loads(p.read_text());r.update(updates);p.write_text(json.dumps(r))

    def test_recounts_flags_and_tables_not_facts_totals(self):
        r,raw=merge(self.plan,self.mapping,self.profile)
        self.assertEqual(r['observed_totals'],{'captured':3,'slots':6,'alive_t5':3,'alive_t20':0})
        self.assertTrue(r['u1_same_profile_score_eligible'])
        self.assertIn('999',raw['a'])
        self.assertTrue(all(x['lit'] is None for x in r['rows']))

    def test_missing_shard_stays_unknown(self):
        r,_=merge(self.plan,{'a':self.mapping['a'],'b':self.mapping['b']},self.profile)
        self.assertEqual(r['status'],'partial');self.assertEqual(r['observed_totals']['captured'],2)
        self.assertIsNone(r['totals']['captured']);self.assertEqual(r['unknown_key_counts']['captured'],1)
        self.assertIn('captured=unknown',format_facts(r));self.assertFalse(r['u1_same_profile_score_eligible'])

    def test_bad_record_shape_and_missing_profile_are_not_accepted(self):
        (self.mapping['a']/'a/record.json').write_text('[]')
        (self.mapping['b']/'runtime-fingerprint.txt').unlink()
        r,_=merge(self.plan,self.mapping,self.profile)
        self.assertEqual(r['status'],'invalid')
        self.assertIsNone(r['rows'][0]['captured'])
        self.assertFalse(r['u1_same_profile_score_eligible'])

    def test_missing_process_table_not_dead_and_capture_flag_missing_unknown(self):
        (self.mapping['a']/'a/processes-t5.txt').unlink()
        self.change_record('b',screenshots=[{}])
        r,_=merge(self.plan,self.mapping)
        self.assertEqual(r['unknown_key_counts']['alive_t5'],1)
        self.assertEqual(r['unknown_key_counts']['captured'],1)
        self.assertIsNone(r['totals']['alive_t5'])

    def test_no_shards_yields_all_unknown(self):
        r,_=merge(self.plan,{})
        self.assertEqual(r['records_present'],0);self.assertIsNone(r['totals']['captured'])
        self.assertEqual(r['unknown_key_counts']['captured'],3)

    def test_profile_mismatch_not_combined_as_same_generation(self):
        p=self.mapping['b']/'runtime-fingerprint.txt';p.write_text('b'*64+'  /system/runtime.so\n')
        r,_=merge(self.plan,self.mapping,self.profile)
        self.assertEqual(r['status'],'invalid');self.assertFalse(r['u1_same_profile_score_eligible'])
        self.assertIn('mixed measured runtime profiles',r['errors'])

    def test_uniform_but_unbound_is_not_U1(self):
        r,_=merge(self.plan,self.mapping)
        self.assertEqual(r['status'],'complete');self.assertFalse(r['u1_same_profile_score_eligible'])

    def test_wrong_partition_and_extra_record_are_errors(self):
        p=copy.deepcopy(self.plan);p['shards'][1]['keys']=['a']
        with self.assertRaises(ValueError):validate_partition(p)
        target=self.mapping['a']/'duplicate';target.mkdir()
        (target/'record.json').write_bytes((self.mapping['a']/'a/record.json').read_bytes())
        r,_=merge(self.plan,self.mapping);self.assertEqual(r['status'],'invalid')

    def test_shard_names_cannot_escape_output_directory(self):
        p=copy.deepcopy(self.plan);p['shards'][0]['name']='../elsewhere'
        with self.assertRaises(ValueError):validate_partition(p)

    def test_wrong_boot_serial_and_apk_rejected(self):
        self.change_record('a',boot_id='old');self.change_record('b',serial='wrong');self.change_record('c',apk_sha256='wrong')
        r,_=merge(self.plan,self.mapping);self.assertEqual(r['status'],'invalid');self.assertEqual(r['records_present'],0)

    def test_in_progress_records_do_not_complete_a_run(self):
        self.change_record('a',finished_at=None)
        r,_=merge(self.plan,self.mapping);self.assertEqual(r['status'],'partial')

    def test_frozen_violation_blocks_eligibility(self):
        p=self.mapping['c']/'facts.txt';p.write_text(p.read_text().replace('violations=0','violations=1'))
        r,_=merge(self.plan,self.mapping,self.profile);self.assertFalse(r['u1_same_profile_score_eligible']);self.assertEqual(r['status'],'invalid')

    def test_process_header_order_and_missing_name(self):
        p=self.root/'ps.txt';p.write_text('PID NAME UID\n88 pkg.a:worker 100\n')
        self.assertTrue(processes(p,100,'pkg.a')['alive'])
        p.write_text('PID UID\n88 100\n');self.assertIsNone(processes(p,100,'pkg.a')['alive'])


if __name__=='__main__':unittest.main()
