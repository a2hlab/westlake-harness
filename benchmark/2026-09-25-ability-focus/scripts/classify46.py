"""Classify bounded log windows and live duplicate mappings; no app mutation."""
from board34 import *
r=R/sys.argv[1]
def counts(s):
 lines=s.splitlines()
 return {'UnsatisfiedLinkError':s.count('UnsatisfiedLinkError'),
         'FATAL_lines':sum('FATAL' in x for x in lines if len(x)<3000),
         'fatal_banners':[x for x in lines if x.startswith('Fatal signal')],
         'getOwnCodecInfo_no_implementation':sum('No implementation' in x and 'getOwnCodecInfo' in x for x in lines),
         'video_fallback':s.count('Failed to initialize video/')}
result={p.name:counts(p.read_text(errors='replace')) for p in [r/'child.stderr',*sorted(r.glob('*-window.stderr'))]}
d=json.loads((r/'device-report.json').read_text());pid=str(d['child'])
maps=dev('cat /proc/uptime; cat /proc/'+pid+'/maps');(r/'final-maps.txt').write_text(maps)
result['live_maps_available']='r-xp' in maps
if not result['live_maps_available']:
 maps=(r/'maps-after-consent.txt').read_text()
result['mapping_source']='final-maps.txt' if result['live_maps_available'] else 'maps-after-consent.txt'
result['offset_zero_executable_images_at_mapping_capture']={lib:sum(lib in l and 'r-xp 00000000' in l for l in maps.splitlines()) for lib in ['libttcrypto.so','libttboringssl.so','libsscronet.so']}
(r/'final-live.txt').write_text(dev('cat /proc/uptime; cat /proc/'+pid+'/stat; strings /proc/'+pid+'/environ | grep WESTLAKE_ANDROID_NATIVE_TARGETS'))
late=[json.loads(x) for x in (r/'manual-actions.jsonl').read_text().splitlines() if 'libttcrypto.so' in json.loads(x)['command'] and '/maps' in json.loads(x)['command']]
if late:
 result['later_live_crypto_mapping']={'command':late[-1]['command'],'epoch':late[-1]['epoch'],'counts':{lib:sum(lib in l and 'r-xp 00000000' in l for l in late[-1]['output'].splitlines()) for lib in ['libttcrypto.so','libttboringssl.so','libsscronet.so']}}
(r/'window-classification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

s=(r/'child.stderr').read_text(errors='replace')
fatal=s[s.rfind('*** *** ***'):];(r/'fatal-tail.txt').write_text(fatal)
pc=re.findall(r'pc: 0x([0-9a-f]+)',fatal)
if pc:
 address=int(pc[-1],16)
 for line in maps.splitlines():
  m=re.match(r'([0-9a-f]+)-([0-9a-f]+) \S+ ([0-9a-f]+) .*?(/.*)',line)
  if m and int(m[1],16)<=address<int(m[2],16):
   offset=address-int(m[1],16)+int(m[3],16)
   (r/'fatal-pc-mapping.json').write_text(json.dumps({'pc':hex(address),'file_offset':hex(offset),'mapping':line,'source':result['mapping_source'],'note':'Mapping from earlier same process; function not symbolized.'},indent=2)+'\n')
