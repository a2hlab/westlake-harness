#!/usr/bin/env python3
"""Check portable source/replay evidence without a device or private input requirement."""
import argparse
import hashlib
import json
from pathlib import Path

D=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name):return json.loads((D/name).read_text())

def check():
    manifest=load('manifest.json')
    repo=D.parents[2]
    for row in manifest['files']:
        p=repo/row['path'];assert p.is_file(),row['path']
        assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes'],row['path']
    r=load('results.json');receipt=load(r['replay']);audit=load(r['zip_layout'])
    assert r['game_runtime']=='NOT_STARTED' and r['device_install']=='NOT_TESTED_WITH_PATCH'
    assert audit['sha256']==receipt['apk_sha256']==r['input_sha256']
    assert audit['bytes']==513290344 and audit['eocd_offset']==513290303
    assert audit['eocd']['commentLength']==19 and audit['eocd']['numDisk']==0
    assert audit['legacy_fields']['numDisk']==44712 and audit['legacy_read_offset']==513290322
    assert audit['central_and_local_checked']==1567
    for name,digest in receipt['source_pins'].items():assert sha(D/name)==digest,name
    for name,digest in load('evidence/producer-pins.json').items():assert sha(D/name)==digest,name
    assert sha(D/'sources/zip_file.comment-compatible.cpp')==r['candidate_source_sha256']
    for row in load('source-index.json')['files']:assert sha(D/row['copy'])==row['sha256']
    for row in load('evidence/contract-sources.json'):assert sha(D/row['snapshot'])==row['sha256']
    original=(D/'sources/zip_file.cpp').read_text();candidate=(D/'sources/zip_file.comment-compatible.cpp').read_text()
    marker='bool ZipFile::ParseAllEntries()'
    assert original.split(marker,1)[1]==candidate.split(marker,1)[1], 'non-EOCD implementation drift'
    assert original.split('bool ZipFile::CheckEndDir',1)[0]==candidate.split('bool ZipFile::CheckEndDir',1)[0]
    for step in receipt['steps']:
        assert step['rc']==step['expected_rc']
        assert int((D/'evidence'/('replay-03--'+step['tag']+'.rc')).read_text())==step['rc']
    for tag,rc,count in [('original-genshin',2,0),('compatible-genshin',0,1567),
                         ('original-notes',0,None),('compatible-notes',0,None),
                         ('original-truncated',2,0),('compatible-truncated',2,0)]:
        out=load('evidence/replay-03--'+tag+'.stdout.txt')
        assert out['open']==(rc==0)
        if count is not None:assert out['entries']==count
    assert 'endDir.numDisk != 0' in (D/'evidence/replay-03--original-genshin.stderr.txt').read_text()
    boundary=load(r['boundaries']);assert len(boundary)==16
    for row in boundary:
        stem='evidence/boundaries-03--'+row['tag']
        assert int((D/(stem+'.rc')).read_text())==row['rc']
        assert (D/(stem+'.stdout.txt')).read_text()==row['stdout']
        if row['tag'].startswith('candidate-'):assert row['rc']==row['candidate_expected_rc']
    cases={x['tag']:x for x in boundary}
    assert cases['candidate-central-in-comment-padded']['rc']==2
    assert cases['candidate-valid-comment-fake-eocd']['rc']==0
    assert cases['candidate-central-overflow']['rc']==2
    first=load(r['first_error']);line={x['line']:x['text'] for x in first['lines']}
    assert 'CheckEndDir:71' in line[281] and 'endDir.numDisk != 0' in line[281]
    assert 'APK_RESOURCES_HAP) OK' in line[280] and '8519936' in line[285]
    rea=load(r['rea']);assert len(rea['files'])==6
    assert sum(x.get('subject_sha256')==r['deployment_library_sha256'] for x in rea['files'])>=2
    for row in load('evidence/sanitization-index.json'):
        assert sha(D/'evidence'/row['path'])==row['public_sha256']
    print(json.dumps({'status':'PASS','manifest_files':len(manifest['files']),
                      'host_open_calls':6,'boundary_calls':16,'deployment':'NOT_TESTED'}))

if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args();check()
