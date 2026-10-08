#!/usr/bin/env python3
"""Validate catalogue coverage, provenance and honest unknowns without executing any lab tool."""
import collections
import copy
import hashlib
import json
import subprocess
import unittest
from functools import lru_cache
from pathlib import Path

from build_inventory import ROOT, HERE, SNAPSHOT, scoped, git, redact, references


@lru_cache(maxsize=None)
def source(path):
    return subprocess.check_output(['git', 'show', SNAPSHOT+':'+path], cwd=ROOT, stderr=subprocess.PIPE)


def evidence_errors(data):
    errors = []
    def walk(obj):
        if isinstance(obj, dict):
            if 'path' in obj and 'line' in obj:
                p,n = obj['path'],obj['line']
                try:
                    lines = source(p).decode('utf-8','replace').splitlines()
                    if not isinstance(n,int) or n < 1 or n > len(lines):
                        errors.append('invalid evidence line: '+p)
                    elif 'excerpt' in obj and obj['excerpt'] != redact(lines[n-1].strip())[:380]:
                        errors.append('changed evidence excerpt: '+p)
                except subprocess.CalledProcessError:
                    errors.append('missing evidence path: '+p)
            for v in obj.values():
                walk(v)
        elif isinstance(obj,list):
            for v in obj:
                walk(v)
    for row in data['tools']:
        try:
            if hashlib.sha256(source(row['path'])).hexdigest() != row['sha256']:
                errors.append('changed source hash: '+row['path'])
        except subprocess.CalledProcessError:
            errors.append('missing tool: '+row['path'])
    walk(data)
    return errors


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((HERE/'tools.json').read_text())


class CoverageTests(Base):
    def test_exact_scope_once(self):
        expected = scoped(git('ls-tree','-r','--name-only',SNAPSHOT).splitlines())
        actual = [r['path'] for r in self.data['tools']]
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual),len(set(actual)))
        self.assertEqual(len(actual),259)
        self.assertEqual(self.data['scope']['top_level_olp_shell'],[])

    def test_counts_dates_and_growth(self):
        rows=self.data['tools'];s=self.data['summary']
        self.assertEqual(dict(collections.Counter(t['category'] for t in rows)),s['category_counts'])
        self.assertEqual(sum(s['category_counts'].values()),s['total'])
        self.assertEqual(sum(w['added'] for w in self.data['weekly_growth']),s['total'])
        self.assertEqual(self.data['weekly_growth'][-1]['cumulative'],s['total'])
        for t in rows:
            for key in ('purpose','purpose_evidence','category','first_commit','birth_reason','called_by_gate_or_executor','tests'):
                self.assertIn(key,t)
            self.assertEqual(t['first_commit']['date'],t['first_commit']['author_date'][:10])
        self.assertTrue((HERE/'growth.svg').read_text().startswith('<svg'))
        self.assertEqual(len((HERE/'weekly-growth.csv').read_text().splitlines()),len(self.data['weekly_growth'])+1)

    def test_five_chains_and_complete_markdown(self):
        self.assertEqual(len(self.data['incident_chains']),5)
        md=(HERE/'README.md').read_text()
        for t in self.data['tools']:
            self.assertIn(f'[`{t["path"]}`:',md)
        self.assertIn('terminal experts',md)
        self.assertIn('bulk import',md)

    def test_known_first_add_and_bulk_import(self):
        rows={t['path']:t for t in self.data['tools']}
        self.assertEqual(rows['scripts/lab/run_facts.py']['first_commit']['commit'],'83ab7bb87867cb05f180cbe4d1d1c0a72854bb0d')
        self.assertEqual(rows['scripts/lab/run_facts.py']['first_commit']['date'],'2026-09-29')
        self.assertEqual(sum(t['first_commit']['commit'].startswith('1a2bb87234da') for t in rows.values()),59)


class HonestyTests(Base):
    def test_no_runtime_or_legacy_execution_claim(self):
        for t in self.data['tools']:
            self.assertFalse(t['callers']['runtime_verified'])
            self.assertFalse(t['tests']['tests_executed_by_this_inventory'])
            if t['birth_reason']['status']=='origin_not_established':
                self.assertTrue(t['birth_reason']['incident_rule'].startswith('unknown:'))
            if not t['called_by_gate_or_executor']['callers']:
                self.assertEqual(t['called_by_gate_or_executor']['status'],'not_observed_in_static_scan')

    def test_header_fallback_and_language_are_explicit(self):
        rows={t['path']:t for t in self.data['tools']}
        self.assertEqual(rows['scripts/lab/adhoc/oatver.py']['header_status'],'absent')
        self.assertEqual(rows['scripts/lab/adhoc/oatver.py']['purpose_evidence']['kind'],'inspected_body_no_header')
        self.assertEqual(rows['scripts/lab/lane_watch.sh']['language'],'python')
        self.assertEqual(rows['scripts/lab/lane_watch.sh']['header_status'],'module_docstring')

    def test_documented_cause_not_name_guess(self):
        rows={t['path']:t for t in self.data['tools']}
        self.assertIn('FLAW-008',rows['scripts/lab/compare_runs.py']['birth_reason']['incident_rule'])
        self.assertTrue(rows['scripts/lab/compare_runs.py']['birth_reason']['digest_runbook_references'])
        self.assertTrue(any(x['path'].endswith('bms_batch.py') for x in rows['scripts/lab/run_facts.py']['called_by_gate_or_executor']['callers']))
        self.assertTrue(any(x['path'].endswith('test_land.py') for x in rows['scripts/lab/land.py']['tests']['evidence']))

    def test_filename_substring_and_prose_are_not_calls(self):
        contents={'scripts/lab/run_facts.py':'"""Counts facts."""\n',
                  'example.py':'import subprocess\n# run_facts.py documentation\nsubprocess.run(["python3", "test_run_facts.py"])\n',
                  'actual.py':'import subprocess\nTOOL = "run_facts.py"\nsubprocess.run(["python3", TOOL])\n'}
        calls,_=references(contents,['scripts/lab/run_facts.py'])
        self.assertEqual([c['path'] for c in calls['scripts/lab/run_facts.py']],['actual.py'])


class EvidenceTests(Base):
    def test_all_pinned_source_lines_resolve(self):
        self.assertEqual(evidence_errors(self.data),[])

    def test_bad_hash_missing_path_or_changed_line_reject(self):
        for field,value in [('sha256','0'*64),('path','scripts/lab/no-such-inventory-tool.py')]:
            bad=copy.deepcopy(self.data)
            bad['tools'][0][field]=value
            self.assertTrue(evidence_errors(bad))
        bad=copy.deepcopy(self.data)
        bad['tools'][0]['purpose_evidence']['excerpt']='fabricated'
        self.assertTrue(evidence_errors(bad))
        bad=copy.deepcopy(self.data)
        bad['tools'][0]['purpose_evidence']['line']=999999
        self.assertTrue(evidence_errors(bad))

    def test_local_scope_matches_pinned_bytes(self):
        for t in self.data['tools']:
            self.assertEqual((ROOT/t['path']).read_bytes(),source(t['path']))


if __name__=='__main__':
    unittest.main(verbosity=2)
