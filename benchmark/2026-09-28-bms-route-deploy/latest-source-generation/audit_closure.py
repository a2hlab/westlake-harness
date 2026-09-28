"""Offline inventory gate: require every declared member and resolve every NEEDED edge.

This does not establish source provenance, namespace visibility, or live admission.
Platform members must be explicit files in the separately pinned pool.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path

def inspect(path,readelf):
    p=subprocess.run([readelf,'-W','-h','-d','-n',str(path)],text=True,capture_output=True,check=True)
    return {'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'path':str(path),
            'soname':re.findall(r'Library soname: \[(.*?)\]',p.stdout),
            'needed':re.findall(r'Shared library: \[(.*?)\]',p.stdout),
            'build_id':re.findall(r'Build ID: (\w+)',p.stdout),
            'aarch64':'Machine:                           AArch64' in p.stdout,
            'warnings':p.stderr.strip()}

def audit(root,required,platform,readelf='llvm-readelf'):
    members={};missing=[];errors=[];edges=[]
    for name in required:
        path=root/name
        if not path.is_file():missing.append(name);continue
        info=inspect(path,readelf);members[name]=info
        if not info['aarch64']:errors.append({'file':name,'error':'not aarch64'})
        if name!='appspawn-x' and info['soname']!=[name]:errors.append({'file':name,'error':'SONAME mismatch'})
        if len(info['build_id'])!=1:errors.append({'file':name,'error':'missing or ambiguous Build-ID'})
    # Walk reachable platform dependencies too; never search arbitrary host paths.
    queue=list(members)
    while queue:
        name=queue.pop();info=members[name]
        for needed in info['needed']:
            edge={'from':name,'needed':needed,'resolved':needed in members}
            if needed not in members and needed in platform:
                f=Path(platform[needed]['path'])
                if f.is_file():
                    child=inspect(f,readelf)
                    # Some stock Rust DSOs omit DT_SONAME. Admit that only
                    # when this exact file is explicitly pinned as such.
                    expected_soname=platform[needed].get('soname',[needed])
                    name_matches=(expected_soname==[needed] or
                                  (expected_soname==[] and f.name==needed))
                    if child['sha256']==platform[needed]['sha256'] and name_matches and child['soname']==expected_soname and child['aarch64']:
                        members[needed]=child;queue.append(needed);edge['resolved']=True
            edges.append(edge)
    unresolved=[e for e in edges if not e['resolved']]
    return {'passed':not(missing or errors or unresolved),'required_count':len(required),
            'missing':missing,'members':members,'errors':errors,'needed_edges':edges,'unresolved_needed':unresolved,
            'scope':'ELF inventory only; does not prove same-source build or dynamic dlopen namespace visibility'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--required',type=Path,required=True);p.add_argument('--platform',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    d=audit(a.root,json.loads(a.required.read_text()),json.loads(a.platform.read_text()) if a.platform else {})
    a.out.write_text(json.dumps(d,indent=2)+'\n');print('PASS' if d['passed'] else f"FAIL missing={len(d['missing'])}, unresolved_needed={len(d['unresolved_needed'])}, elf_errors={len(d['errors'])}")
    raise SystemExit(0 if d['passed'] else 1)
