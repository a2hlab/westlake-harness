#!/usr/bin/env python3
import argparse,hashlib,json,re
from pathlib import Path

def need(v,m):
    if not v:raise RuntimeError(m)
def birth(line):
    m=re.match(r'^(\d+) \(.*\) (.*)$',line);need(m,'stat');return int(m[1]),int(m[2].split()[19])
def stat(line):
    f=line.split(maxsplit=8);need(len(f)==9 and f[0]=='STAT','file stat');return {'dev':int(f[1]),'inode':int(f[2]),'size':int(f[3]),'mtime':int(f[4]),'uid':int(f[5]),'gid':int(f[6]),'mode':f[7],'path':f[8]}
def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();pins=[]
    def read(q):
        b=q.read_bytes();pins.append({'path':str(q.relative_to(a.input)),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)});return b.decode()
    index=json.loads(read(a.input/'hap_corrected.json'));need(index.get('ended'),'unfinished');rows=[];times=[]
    for board,info in index['boards'].items():
        root=a.input/'raw'/board;steps=[]
        for name in ['held','fresh_ps','hap_read']:
            rc=int(read(root/(name+'.rc')).strip());need(rc==(1 if name=='held' else 0),'rc');av=json.loads(read(root/(name+'.argv')));out=read(root/(name+'.stdout'));err=read(root/(name+'.stderr'));start=float(read(root/(name+'.start')).split()[0]);end=float(read(root/(name+'.end')).split()[0]);times.extend([start,end]);steps.append({'name':name,'rc':rc,'stderr_nonempty':bool(err),'start_epoch':start,'end_epoch':end})
            if name=='held':need(not out.strip(),'holder')
            else:need(av[2]==info['serial'],'whitelist serial')
            if name=='fresh_ps':fresh=out.splitlines()
            if name=='hap_read':lines=out.splitlines();need('/proc//' not in av[-1],'empty pid')
        need(fresh[0]==info['boot'],'boot');hosts=[int(m[1]) for l in fresh if (m:=re.fullmatch(r'\s*(\d+)\s+org\.westlake\.imehost\s*',l))];need(hosts==[int(info['host_pid'])],'fresh host unique');b1=birth(lines[0]);b2=birth(lines[-1]);need(b1==b2 and b1[0]==hosts[0],'birth stable');need(str(b1[1])==info['births'][0]==info['births'][1],'record birth')
        maps=[(i,l) for i,l in enumerate(lines,1) if re.match(r'^[0-9a-f]+-[0-9a-f]+\s',l)];need(len(maps)==1,'map row');f=maps[0][1].split(maxsplit=5);major,minor=[int(v,16) for v in f[3].split(':')];device=(minor&255)|((major&4095)<<8)|((minor&~255)<<12)|((major&~4095)<<32);need(f[5]=='/data/storage/el1/bundle/entry.hap','mapped HAP path');stats=[(i,stat(l)) for i,l in enumerate(lines,1) if l.startswith('STAT ')];need(len(stats)==2 and stats[0][1]==stats[1][1],'stat stable');s=stats[0][1];need(s['dev']==device and s['inode']==int(f[4]),'map stat identity');expected=f'/proc/{b1[0]}/root/data/storage/el1/bundle/entry.hap';need(s['path']==expected,'root path');h=[(i,m[1],m[2]) for i,l in enumerate(lines,1) if (m:=re.fullmatch(r'([0-9a-f]{64})\s+(.+)',l))];need(len(h)==1 and h[0][2]==expected,'hash path');need(h[0][1]==info['sha256']=='b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0','HAP hash')
        rows.append({'board':board,'serial':info['serial'],'boot_observed_before':fresh[0],'host_pid':b1[0],'birth_before_after':list([b1[1],b2[1]]),'stat_before_after_equal':True,'map_dev_inode':[device,int(f[4])],'file_stat':s,'sha256':h[0][1],'raw_lines':{'map':maps[0][0],'stat':[v[0] for v in stats],'hash':h[0][0],'process_stat':[1,len(lines)]},'steps':steps})
    elapsed=max(times)-min(times);need(elapsed<=60,'budget');r={'task':'T106B independent HAP follow-up','status':'TWO_HOST_MAPPED_HAP_BACKING_FILES_MATCH_B189','actual_input_location':'$HOME/.local/share/westlake/cross-board-startup-inputs-20261023/cc/hap-corrected/hap_corrected.json','boards':rows,'actual_receipt_interval_epoch':[min(times),max(times)],'elapsed_from_raw_seconds':round(elapsed,6),'prior_evidence':'Initial comparison/results.json and both invalid hap_supp receipts unchanged. This is later independent evidence, not a correction of initial unknown into retrospective PASS.','limits':['Boot is observed in fresh_ps before each HAP read; no extra boot-after field is invented. Host birth is bracketed inside each read.','HAP backing-file hash does not establish Android APK identity by itself; prior18-path comparison remains separate.','9BCP JARs and active BCP order still lack cross-board proof; no timing-cause inference.'],'raw_pins':pins,'actions':{'device':0,'git':0},'author_commit':None};a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'status':r['status'],'elapsed_s':r['elapsed_from_raw_seconds'],'raw_files':len(pins)}))
if __name__=='__main__':main()
