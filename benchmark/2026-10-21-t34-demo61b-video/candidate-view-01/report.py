#!/usr/bin/env python3
"""Offline readout: file views and maps identity, never a symbol-winner claim."""
import argparse,json,re
from pathlib import Path

def decode(text,rc):
    if rc!=0 or not text.rstrip().endswith('CANDIDATE_VIEW_END_IDENTITY_MATCH'):
        return {'status':'INCOMPLETE_OR_REJECTED','rc':rc,'loaded_winner':'UNKNOWN'}
    files={}
    for line in text.splitlines():
        if line.startswith('CV_FILE|'):
            _,role,rel,stat,sha=line.split('|');assert (role,rel) not in files
            files[role,rel]={'stat':stat,'sha256':sha}
    report={}
    for (role,rel),f in files.items():
        if role=='physical':continue
        physical=files.get(('physical',rel));assert physical
        dev,ino,*_=f['stat'].split(':');dev=int(dev)
        major=((dev>>8)&0xfff)|((dev>>32)&0xfffff000)
        minor=(dev&0xff)|((dev>>12)&0xffffff00)
        block=re.search(r'^MAPS_BEGIN_'+role+r'\n(.*?)^MAPS_END_'+role+r'$',text,re.M|re.S)
        rows=[]
        if block:
            for l in block.group(1).splitlines():
                a=l.split(None,5)
                if len(a)==6 and a[5]=='/data/local/tmp/asx/'+rel:
                    md=tuple(int(x,16) for x in a[3].split(':'))
                    rows.append({'range':a[0],'offset':a[2],'same_file_identity':md==(major,minor) and a[4]==ino})
        report[role+':'+rel]={'physical_same_sha':physical['sha256']==f['sha256'],'physical_same_devinode':physical['stat'].split(':')[:2]==f['stat'].split(':')[:2],'maps_rows':rows,'mapping_status':'FILE_IDENTITY_MATCH' if rows and all(x['same_file_identity'] for x in rows) else ('MAPPING_IDENTITY_MISMATCH' if rows else 'UNKNOWN_NOT_MAPPED_AT_EXACT_PATH')}
    assert len([x for x in files if x[0]=='physical'])==6
    assert len([x for x in files if x[0]=='parent'])==6
    return {'status':'COLLECTED_IDENTITY_GUARDED','file_views':report,'child':'UNKNOWN_NOT_SELECTED' if 'CHILD_UNKNOWN_NOT_SELECTED' in text else 'EXPLICIT_IDENTITY_COLLECTED','loaded_winner':'UNKNOWN; maps identity is not a dynamic symbol binding'}
def main():
    a=argparse.ArgumentParser();a.add_argument('--stdout',type=Path,required=True);a.add_argument('--rc',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a=a.parse_args()
    a.out.write_text(json.dumps(decode(a.stdout.read_text(),int(a.rc.read_text())),indent=2)+'\n')
if __name__=='__main__':main()
