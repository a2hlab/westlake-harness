#!/usr/bin/env python3
"""Offline r8 checkpoint extraction. No transport imports or device commands."""
import argparse,hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();b=a.base;out=a.out;out.mkdir(parents=True,exist_ok=False)
 play=b/'video-r8-play1';binding=b/'video-r8-binding';native=b/'video-r8-native-after'
 rec=json.loads((play/'record.json').read_text());n=rec['stderr_baseline_lines'];data=(play/'child-full.stderr').read_text(errors='replace');lines=data.splitlines()
 assert (play/'stderr-delta.txt').read_text()=='\n'.join(lines[n:])+'\n'
 mirrors=[(i+1,line) for i,line in enumerate(lines) if '[WL-TTLOG' in line]
 assert n==218014 and len(mirrors)==256 and all(i>n for i,line in mirrors)
 nd=(native/'child.stderr').read_text(errors='replace').splitlines();nm=[(i+1,line) for i,line in enumerate(nd) if '[WL-TTLOG' in line];assert nm==mirrors
 ids={}
 for directory,names in [(play,['child-before.stat','child-after.stat','parent-before.stat']),(native,['before-child.stat','after-child.stat','before-parent.stat','after-parent.stat'])]:
  for name in names:
   text=(directory/name).read_text();fields=text.rsplit(') ',1)[1].split();v={'pid':int(text.split()[0]),'state':fields[0],'ppid':int(fields[1]),'birth':int(fields[19])};ids[directory.name+'/'+name]=v
   assert (v['pid'],v['birth'])==((5079,8470) if 'parent' in name else (14946,22868))
   if 'child' in name:assert v['ppid']==5079
   assert v['state'] not in ['Z','X']
 br=json.loads((binding/'reads.json').read_text());assert br['boot']==rec['boot_id']=='e2de7300-2192-43be-bda0-9d3ca7ac8a53'
 assert (br['parent'],br['parent_birth'],br['child'],br['child_birth'])==(5079,8470,14946,22868)
 v={r['label']:int(r['value'],16) for r in br['reads']};bias={k:int(v,16) for k,v in br['biases'].items()}
 assert v['player_mirror_GOT']==bias['libopensles_android_compat.so']+0x1aac
 assert v['compat_vprint_GOT']==bias['liblog.so']+0x7450
 assert all(x['match'] for x in br['binding_checks'].values()) and br['identity_after_reads']
 mapped={}
 for name,pin in [('libttmplayer.so','0b4d95c5f9d96826a95ede998df20be037299eaf6fbfcd1cd2afa39793ba9471'),('libopensles_android_compat.so','6e83e924aae709f0c90ba2a966910febb63471b7a9a6294c6dee585a73ff3b4b'),('liblog.so','d8ad176b41b820a4868b74394188429ad2dc69025661d320d0986dd713048ca4')]:
  before=(binding/('before-'+name+'-identity.txt')).read_text();after=(binding/('after-'+name+'-identity.txt')).read_text();assert before==after and before.split()[0]==pin
  ident=before.splitlines()[1];dev,ino=map(int,ident.split(':'));major=((dev>>8)&0xfff)|((dev>>32)&~0xfff);minor=(dev&0xff)|((dev>>12)&~0xff)
  path=before.splitlines()[0].split()[1].split('/root',1)[1]
  arows=[l for l in (binding/'maps-before.txt').read_text().splitlines() if l.split()[-1]==path];brows=[l for l in (binding/'maps-after.txt').read_text().splitlines() if l.split()[-1]==path];assert arows and arows==brows
  assert all(tuple(int(x,16) for x in l.split()[3].split(':'))==(major,minor) and int(l.split()[4])==ino for l in arows)
  mapped[name]={'sha256':pin,'device_inode':ident,'relevant_maps_before_after_equal':True}
 copied=out/'facts-layout'/'video-r8-play1';copied.mkdir(parents=True)
 sanitized=json.loads(json.dumps(rec))
 for shot in sanitized['screenshots']:
  f=play/Path(shot['path']).name;assert sha(f)==shot['sha256'];shutil.copyfile(f,copied/f.name);shot['path']=f.name
 (copied/'record.json').write_text(json.dumps(sanitized,indent=2)+'\n')
 facts=subprocess.run([sys.executable,str(a.repo/'scripts/lab/run_facts.py'),str(out/'facts-layout')],capture_output=True);assert facts.returncode==0
 (out/'facts.txt').write_bytes(facts.stdout);(out/'facts-run.json').write_text(json.dumps({'rc':facts.returncode,'stderr':facts.stderr.decode(),'record_transformation':'Only screenshot paths replaced by basename; original record SHA retained in inputs manifest. No status, process table or counts invented.'},indent=2)+'\n')
 assert len({x['sha256'] for x in rec['screenshots'][1:]})==1
 excerpt_lines=[218240,218241,218301,218307,218310,218385,218386,218392,218398,218400,218402,218404]
 # Deliberate allowlist: never publish URLs, IP addresses, signed query strings.
 excerpt=''.join(str(i)+': '+lines[i-1]+'\n' for i in excerpt_lines)
 assert '://' not in excerpt and 'main_url' not in excerpt and 'mime_type=' not in excerpt
 (out/'player-excerpt.txt').write_text(excerpt)
 first_priority6=next((i,line) for i,line in mirrors if '[WL-TTLOG p=6 ' in line);assert first_priority6[0]==218398
 first_codec=next((i,line) for i,line in mirrors if 'open codec fail' in line);assert first_codec[0]==218392
 (out/'binding-read.json').write_bytes((binding/'reads.json').read_bytes())
 source_files=[]
 for directory in [play,binding,native]:
  for path in sorted(directory.rglob('*')):
   if path.is_file():source_files.append({'path':'BASE/'+path.relative_to(b).as_posix(),'sha256':sha(path),'bytes':path.stat().st_size,'publish_raw':False})
 (out/'source-files.json').write_text(json.dumps(source_files,indent=2)+'\n')
 results={'token':'video-1919-r8-live-review','status':'BOUNDED_OBSERVATION_COMPLETE_WINDOW_RESTORE_PENDING','playback':'NOT_PASSED','audio':'UNKNOWN','device_calls':0,'boot':rec['boot_id'],'parent':5079,'parent_birth':8470,'child':14946,'child_birth':22868,'identities':ids,'binding':{'both_matches':True,'final_identity_present':True,'objects':mapped},'mirror':{'whole_log_records':len(mirrors),'pre_baseline_records':0,'post_baseline_records':len(mirrors),'baseline_lines':n,'first_line':mirrors[0][0],'last_line':mirrors[-1][0],'skipped_format_records':sum('skipped-format' in l for i,l in mirrors),'limit':256,'coverage':'saturated; absence after cap is not evidence of no later error','native_after_same_256_records':True,'native_log_property_consumed':'log enabled by prop at line 218240; verbose slot=1'},'reached':[{'operation':'setDataSource','line':218301},{'operation':'prepare_l','line':218307},{'operation':'prepare','line':218310}],'first_observed_failures':{'earlier_codec_warning':{'line':218385,'text':'non hardware codecname match the codec type'},'codec_open_failure':{'line':218392,'text':'open codec fail,errReason:0','context':'adjacent codecType video/hevc'},'first_priority6_mirror_error':{'line':218398,'text':'ff_listen_connect2 ret:-97 neterrno:-97 default error'},'network_propagation_lines':[218400,218402,218404],'ordering_scope':'stderr file order of concurrent subsystems, not a proven single fatal causal chain'},'data_source':{'wrapper_observed':'mem://bash','embedded_url_ipv6_literal_present':True,'private_url_not_published':True,'network_function_provider':'UNKNOWN','errno_translation_origin':'UNKNOWN','shim_root_cause':'NOT_ESTABLISHED'},'visual':{'reviewed_actual_files':['t0.jpeg','t5.jpeg','t10.jpeg','t20.jpeg','t25.jpeg'],'t0':'post-click feed with a video card; not a pre-tap baseline','t5_to_t25':'same stationary cover on the video-detail screen, byte-identical four JPEGs','identical_sha256':rec['screenshots'][1]['sha256'],'no_dynamic_or_audio_claim':True},'scope_limits':['No device calls; no API update.','Native-after collection bookends match same child/parent; no claim of continuous per-frame liveness. Standard run_facts liveness remains unknown without its process tables.','Binding is actual for this observation; it does not establish full namespace loading or playback.','No socket/connect provider probe or exact error-translation chain is present; -97 and an IPv6 literal alone do not identify a shim cause.','Restoration, final feed and unlock are not reviewed in this checkpoint.']}
 (out/'results.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps({'mirror_count':len(mirrors),'binding':True,'playback':results['playback'],'first_codec_line':218392,'first_priority6_line':218398,'source_files':len(source_files),'facts':facts.stdout.decode()},indent=2))
if __name__=='__main__':main()
