#!/usr/bin/env python3
"""Validate public evidence and optionally rehash durable local originals; no device I/O."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parent
ORIGINAL='51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5'
CANDIDATE='7c24bd11190b0728b81ecd958519f01c688efb2533ef26c9b7ae4eefc82151db'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(name):return json.loads((ROOT/name).read_text())
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--original-root',type=Path);a=p.parse_args()
    manifest=read('public-sha256.json')
    for name,digest in manifest.items():
        assert sha(ROOT/name)==digest,('public hash drift',name)
        assert not re.search(r'/(?:Users|home)/[A-Za-z0-9_.-]+/',(ROOT/name).read_text()),('personal path',name)
    indexes={}
    for f in sorted((ROOT/'original-index').glob('*.jsonl')):
        for line in f.read_text().splitlines():
            row=json.loads(line);assert row['alias'] not in indexes;indexes[row['alias']]=row
            assert re.fullmatch('[a-f0-9]{64}',row['sha256']) and row['bytes']>=0
            if a.original_root:
                source=a.original_root/row['alias'].removeprefix('$G13_PRIVATE/')
                assert source.stat().st_size==row['bytes'] and sha(source)==row['sha256'],('original drift',row['alias'])
    result=read('results.json');assert len(indexes)==result['original_files_indexed']==3407
    for row in read('provenance.json'):
        assert row['source'] in indexes and row['source_sha256']==indexes[row['source']]['sha256']
        assert row['path'] in manifest
        if row.get('selected_lines'):assert row['selected_lines']==sorted(set(row['selected_lines']))
    rec=read('evidence/genshin-record.json')
    assert rec['install']['return_code']==0 and rec['install']['success_text'] is True
    assert rec['bms']['queryable'] is True and rec['bms']['uid']==20011077
    assert rec['screenshots']==[] and rec['clicked'] is False and rec['status']=='installed_launch_not_tested'
    assert (ROOT/'evidence/genshin-install.txt').read_text().strip()=='install bundle successfully.'
    bundle=(ROOT/'evidence/genshin-bundle.txt').read_text();data=json.loads(bundle[bundle.index('{'):])
    assert 'com.miHoYo.Yuanshen' in bundle and '20011077' in bundle and isinstance(data,dict)
    assert read('evidence/original-loader-failure.json')['status']=='unobserved-or-mismatch'
    loaded=(ROOT/'evidence/candidate-loaded-excerpt.txt').read_text()
    stats=[s for s in loaded.splitlines() if s.startswith('7798 (installs)')];assert len(stats)==2
    ids=[(s[:s.index(' ')],s[s.rfind(')')+2:].split()[1],s[s.rfind(')')+2:].split()[19]) for s in stats]
    assert ids[0]==ids[1]==('7798','1','303100')
    assert re.search(r'^Uid:\s+3060\s+3060\s+3060\s+3060$',loaded,re.M)
    assert '/system/bin/sa_main' in loaded and '66336:5547' in loaded and CANDIDATE+'  /proc/7798/root/system/lib64/libinstalls.z.so' in loaded
    maps=[s for s in loaded.splitlines() if re.match('[0-9a-f]+-[0-9a-f]+ ',s)];assert maps and all(s.split()[3:5]==['103:20','5547'] for s in maps)
    final=(ROOT/'evidence/final-read-excerpt.txt').read_text();assert final.count(ORIGINAL)==2 and ' / ext4 ro,' in final and 'Current State: SLEEP' in final and 'Timeout=30000ms  OverrideTimeout=10000ms' in final and '__G13_FINAL_RC=0' in final
    assert read('evidence/restore.receipt.json')['rc']==0
    closure=read('evidence/closure.json');assert closure['lock_released'] and closure['package_retained'] and closure['game_screenshots']==0 and closure['uid']==20011077
    assert read('evidence/g06-restore-result.json')['status']=='RESTORED_PACKAGE_RETAINED'
    assert read('evidence/loader-restored.json')['status']=='unobserved-demand-idle'
    facts=(ROOT/'evidence/genshin-facts.txt').read_text();assert 'screenshots_captured=0/0' in facts and 'alive_unknown=1' in facts
    assert result['status']=='INSTALL_ACCEPTED_GAME_NOT_STARTED' and not result['first_launch']['attempted']
    print(json.dumps(dict(status='PASS',public_files=len(manifest),originals_indexed=len(indexes),originals_rehashed=bool(a.original_root),install_success=True,game_started=False,device_operations=0)))
if __name__=='__main__':main()
