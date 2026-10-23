#!/usr/bin/env python3
"""Independently parse saved proc/maps/stat/hash receipts; no device calls."""
import argparse,hashlib,json,re,collections
from pathlib import Path

def need(v,m):
    if not v:raise RuntimeError(m)
def st(line):
    m=re.match(r'^(\d+) \(.*\) (.*)$',line);need(m,'proc stat');f=m[2].split();return {'pid':int(m[1]),'ppid':int(f[1]),'birth':int(f[19])}
def fs(line):
    f=line.split(maxsplit=8);need(len(f)==9 and f[0]=='STAT','file stat');return dict(zip(['dev','inode','size','mtime','uid','gid','mode'],map(int,f[1:8])),path=f[8])
def dev(v):
    a,b=[int(x,16) for x in v.split(':')];return (b&255)|((a&4095)<<8)|((b&~255)<<12)|((a&~4095)<<32)
def ps(lines,name):
    rows=[]
    for l in lines:
        f=l.split(maxsplit=3)
        if len(f)==4 and all(x.isdigit() for x in f[:3]) and f[3]==name:rows.append({'pid':int(f[0]),'ppid':int(f[1]),'uid':int(f[2]),'name':f[3]})
    return rows

def main():
    a=argparse.ArgumentParser();a.add_argument('--raw',type=Path,required=True);a.add_argument('--plan-files',type=Path,required=True);a.add_argument('--output',type=Path,required=True);x=a.parse_args();pins=[]
    def read(p):
        b=p.read_bytes();pins.append({'path':str(p.relative_to(x.raw)),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)});return b.decode()
    index=json.loads(read(x.raw/'index.json'));need(index.get('ended'),'index not terminal');plan=json.loads(x.plan_files.read_text());boards={};mapped={};extras=[];rcs=[]
    for board,info in index['boards'].items():
        root=x.raw/'raw'/board
        for step in info['steps']:
            if str(step['rc']).startswith('NOT_RUN'):
                rcs.append({'board':board,'step':step['name'],'status':'NOT_RUN','reason':step['rc']});continue
            name=step['name'];rc=int(read(root/(name+'.rc')).strip());need(rc==(1 if name=='held' else 0),'step rc '+board+name);need(rc==int(step['rc']),'index rc');argv=json.loads(read(root/(name+'.argv')));start=read(root/(name+'.start'));end=read(root/(name+'.end'));stderr=read(root/(name+'.stderr'));stdout=read(root/(name+'.stdout'));rcs.append({'board':board,'step':name,'rc':rc,'stderr_nonempty':bool(stderr),'start':start.strip(),'end':end.strip()})
            if name=='held':need(not stdout.strip(),'holder present')
            else:need(argv[2]==info['serial'],'serial mismatch')
        first=read(root/'fresh_identity.stdout').splitlines();final=read(root/'final_identity.stdout').splitlines();need(first[0]==final[0]==info['boot'],'boot changed');ident={};proc_maps={}
        for tag,name in [('child','com.ss.android.article.news'),('host','org.westlake.imehost')]:
            initial=ps(first,name);last=ps(final,name);need(len(initial)==len(last)==1 and initial==last,'target ps identity');p=read(root/('proc_'+tag+'.stdout')).splitlines();before,after=st(p[0]),st(p[-1]);fin=[st(l) for l in final if re.match(r'^'+str(before['pid'])+r' \(',l)];need(before==after and fin==[before] and before['pid']==initial[0]['pid'],'birth bracket')
            rows=[];hexparts=[]
            for n,l in enumerate(p[2:-1],3):
                if re.fullmatch(r'\s*(?:[0-9a-f]{2}\s*)+',l):hexparts.extend(l.split());continue
                m=re.match(r'^[0-9a-f]+-[0-9a-f]+\s+\S+\s+[0-9a-f]+\s+(\S+)\s+(\d+)\s*(.*)$',l)
                if m:rows.append({'line':n,'dev':m[1],'inode':int(m[2]),'path':m[3].strip()})
            cmd=bytes.fromhex(' '.join(hexparts)).split(b'\0')[0].decode();need(cmd==name,'cmdline identity');ident[tag]={**before,'uid':initial[0]['uid'],'exe':p[1],'cmdline0':cmd,'process_stat_stable':True,'final_birth_same':True};proc_maps[tag]=rows
        selected=[]
        for item in info['mapped_selected']:
            name=item['rec'];p=read(root/(name+'.stdout')).splitlines();need(len(p)==3,'map output');before,after=fs(p[0]),fs(p[2]);need(before==after,'map file changed');h=re.fullmatch(r'([0-9a-f]{64})\s+(.+)',p[1]);need(h and h[2]==before['path'],'hash path');pid=ident[item['tag']]['pid'];prefix=f'/proc/{pid}/root';need(before['path'].startswith(prefix+'/'),'process root path');path=before['path'][len(prefix):];matches=[v for v in proc_maps[item['tag']] if v['path']==path];need(matches and all(dev(v['dev'])==before['dev'] and v['inode']==before['inode'] for v in matches),'maps stat identity');need(h[1]==item['sha256'] and path==item['path'],'index disagreement')
            selected.append({'role':item['role'],'logical_relative_path':path.removeprefix('/data/local/tmp/asx/'),'observed_path':path,'process_tag':item['tag'],'pid':pid,'birth':ident[item['tag']]['birth'],'sha256':h[1],'stat':before,'maps_lines':[v['line'] for v in matches],'mapping_segments':len(matches),'dev_inode_match':True,'stat_before_after_equal':True,'receipt':f'raw/{board}/{name}.stdout'})
        need(len(selected)==18,'mapped count');mapped[board]=selected
        haps=[v for v in proc_maps['host'] if v['path'].endswith('/entry.hap')];disk=[]
        if (root/'exact_61b_disk.stdout').exists():
            ls=read(root/'exact_61b_disk.stdout').splitlines();need(len(ls)==54,'disk27 actual rows')
            for i in range(0,len(ls),2):
                f=fs(ls[i]);h=re.fullmatch(r'([0-9a-f]{64})\s+(.+)',ls[i+1]);need(h and h[2]==f['path'],'disk hash path');disk.append({'path':f['path'],'sha256':h[1],'stat':f,'stat_samples':1,'view':'physical disk only unless independently joined to mapping'})
        if (root/'hap_supp.argv').exists():
            av=json.loads(read(root/'hap_supp.argv'));rc=read(root/'hap_supp.rc').strip();out=read(root/'hap_supp.stdout');err=read(root/'hap_supp.stderr');read(root/'hap_supp.start');read(root/'hap_supp.end');extras.append({'board':board,'name':'hap_supp','outside_index_steps':True,'rc':rc,'invalid_serial_argument':av[2],'contains_empty_pid_path':'/proc//' in av[-1],'has_hap_sha':bool(re.search(r'^[0-9a-f]{64}\s+.*entry.hap$',out,re.M)),'status':'REJECTED_AS_HAP_EVIDENCE','reason':'Serial and PID combined; empty PID paths; CPU statistics are not HAP stat/hash. Aggregate rc cannot certify component success.'})
        boards[board]={'serial':info['serial'],'boot':first[0],'uptime_before_after':[float(first[1].split()[0]),float(final[1].split()[0])],'uptime_elapsed_s':round(float(final[1].split()[0])-float(first[1].split()[0]),2),'identities':ident,'mapped_files_actual':len(selected),'disk_files_actual':len(disk),'disk_files':disk,'host_hap_maps_identity_only':haps,'uncovered_planned_roles':[z['logical_relative_path'] or z['61b_historical_physical_path'] for z in plan['files'] if (z['logical_relative_path'] or z['61b_historical_physical_path']) not in {s['logical_relative_path'] for s in selected}],'namespace_limit':'Proc-root path and maps backing-file identity proven for that PID; linker namespace labels and live-memory bytes not inspected.'}
    left={v['logical_relative_path']:v for v in mapped['61b']};right={v['logical_relative_path']:v for v in mapped['5cd']};comparison=[]
    for key in sorted(left.keys()|right.keys()):
        l=left.get(key);r=right.get(key);comparison.append({'logical_relative_path':key,'role':(l or r)['role'],'61b_sha256':l['sha256'] if l else None,'5cd_sha256':r['sha256'] if r else None,'status':'MATCH' if l and r and l['sha256']==r['sha256'] else 'DIFFERENT' if l and r else 'UNKNOWN'})
    result={'status':'CURRENT_CORE18_MATCH_NO_VERSION_SWAP_BASIS_PARTIAL_COVERAGE','index_ended':index['ended'],'boards':boards,'mapped_observations':mapped,'cross_board':comparison,'matching_count':sum(z['status']=='MATCH' for z in comparison),'receipt_rcs':rcs,'supplemental_rejected':extras,'duplicate_basename':'Both children map two distinct libandroid.so backing objects: asx/libandroid.so and asx/webview-t-lib/libandroid.so, different hashes/inodes within each board. Compare full relative paths, not basename. Both variants match cross-board. Multiple map segments are not independently counted as multiple runtime instances.','conclusion':'No version difference in these18 mapped core backing files supports swapping packages. This does not prove equal startup conditions, BCP order, configuration, data/cache state, timing or causes.','coverage':'9BCP JARs and HAP lack comparable two-board hashes.61b disk27 is extra physical evidence, not27 mappings or27 cross-board matches.','actions':{'device':0,'frozen_changes':0,'REA':0,'git':0},'raw_pins':list({z['path']:z for z in pins}.values())}
    need(result['matching_count']==18,'not all core match');x.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'matched':result['matching_count'],'indexed_receipts':len(rcs),'extra_rejected':len(extras),'boards':{k:{'boot':v['boot'],'identity':v['identities'],'mapped':v['mapped_files_actual'],'disk':v['disk_files_actual']} for k,v in boards.items()}}))
if __name__=='__main__':main()
