#!/usr/bin/env python3
"""Offline readout: file views and maps identity, never a symbol-winner claim."""
import argparse,json,re
from pathlib import Path

def decode(text,rc):
    complete=text.rstrip().endswith('CANDIDATE_VIEW_END_IDENTITY_MATCH')
    errors=[line for line in text.splitlines() if line.startswith(('CV_FILE_ERROR|','UNKNOWN_'))]
    observations=[line for line in text.splitlines() if line.startswith(('CV_FILE','CV_RUN_WID'))]
    files={}
    for line in text.splitlines():
        if line.startswith('CV_FILE|'):
            _,role,rel,stat,sha=line.split('|');assert (role,rel) not in files
            files[role,rel]={'stat':stat,'sha256':sha}
    report={}
    for (role,rel),f in files.items():
        if role=='physical':continue
        physical=files.get(('physical',rel))
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
        report[role+':'+rel]={'physical_same_sha':physical['sha256']==f['sha256'] if physical else None,'physical_same_devinode':physical['stat'].split(':')[:2]==f['stat'].split(':')[:2] if physical else None,'maps_rows':rows,'mapping_status':'FILE_IDENTITY_MATCH' if rows and all(x['same_file_identity'] for x in rows) else ('MAPPING_IDENTITY_MISMATCH' if rows else 'UNKNOWN_NOT_MAPPED_AT_EXACT_PATH')}
    counts={role:len([x for x in files if x[0]==role]) for role in ['physical','parent','child']}
    sufficient=counts['physical']==6 and counts['parent']==6 and ('CHILD_UNKNOWN_NOT_SELECTED' in text or counts['child']==6)
    remote_rows=[line for line in text.splitlines() if line.startswith('CV_REMOTE_RC|')]
    remote_ok=remote_rows==['CV_REMOTE_RC|0']
    ok=rc==0 and remote_ok and complete and sufficient and not errors
    return {'status':'COLLECTED_IDENTITY_GUARDED' if ok else 'INCOMPLETE_OR_REJECTED','rc':rc,'remote_rc_lines':remote_rows,'remote_rc_zero_unique':remote_ok,'final_identity_marker':complete,'observed_lines':observations,'errors':errors,'counts':counts,'file_views':report,'child':'UNKNOWN_NOT_SELECTED' if 'CHILD_UNKNOWN_NOT_SELECTED' in text else ('EXPLICIT_IDENTITY_COLLECTED' if counts['child']==6 else 'UNKNOWN_INCOMPLETE'),'loaded_winner':'UNKNOWN; maps identity is not a dynamic symbol binding'}
def main():
    a=argparse.ArgumentParser();a.add_argument('--stdout',type=Path,required=True);a.add_argument('--rc',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a=a.parse_args()
    a.out.write_text(json.dumps(decode(a.stdout.read_text(),int(a.rc.read_text())),indent=2)+'\n')
if __name__=='__main__':main()
