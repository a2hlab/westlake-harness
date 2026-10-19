exec(open('/tmp/t4_finish_r4.py').read().split("pins=json.loads")[0])
pins=json.loads((P/'source-pins.json').read_text());rows={x['path']:x for x in pins['files']}
def add(f):
 v={'path':('$HOME/'+str(f.relative_to(Path.home()))) if f.is_relative_to(S) else '$WORKSPACES/'+str(f.relative_to(R.parent)),'sha256':h(f),'bytes':f.stat().st_size};rows[v['path']]=v
for f,rel in [(M/'benchmark/2026-10-19-toutiao-rea-methods/video-1919-r4-review/window-archive.json','archive/window-archive.json'),(M/'benchmark/2026-10-19-toutiao-rea-methods/video-1919-r4-review/persistent-artifacts.json','archive/build-artifacts-receipt.json'),(M/'benchmark/2026-10-19-toutiao-rea-methods/video-1919-r4-review/results.json','archive/static-build-review.json'),(S/'video_probe_r3.py','historical-recipes/video_probe_r3.py')]:
 out=P/rel;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(f.read_bytes());add(f)
# Remove unused inherited probe from the draft: actual r4 archive identifies r3.
(P/'historical-recipes/video_probe_r2.py').unlink();rows.pop('$HOME/.local/share/westlake/toutiao-resume-20261019/video_probe_r2.py',None)
priv=S/'video-r4-window-archive/receipt.json';add(priv)
a=json.loads((P/'archive/window-archive.json').read_text());b=json.loads(priv.read_text());assert (a['sha256'],a['size'])==(b['sha256'],b['size'])==('5247bf079bcbc4d5ccb4ac0ac36b880b6bef86e270fb4ba8a7bd5667d069c987',14884299)
r=json.loads((P/'results.json').read_text());r.update(frozen=True,final_manifest='SHA256SUMS + freeze.json',archive={'status':'REMOTE_ARCHIVE_VERIFIED_BY_OUTER_RECEIPT','receipt':'archive/window-archive.json','sha256':a['sha256'],'bytes':a['size'],'reviewer_network_calls':0});w(P/'results.json',r)
pins['files']=list(rows.values());w(P/'source-pins.json',pins)
s=(P/'README.md').read_text().replace('Archive receipt and final whole-packet manifest are pending. The evidence-content listing freezes the current images/facts; it is not API capability freezing.','The outer [archive receipt](archive/window-archive.json) verifies14,884,299 bytes, SHA `5247bf079bcbc4d5ccb4ac0ac36b880b6bef86e270fb4ba8a7bd5667d069c987`. It agrees with the private receipt; this reviewer did not repeat remote transfer/checks. The final manifest freezes evidence, not API capability.')
(P/'README.md').write_text(s)
s=(P/'ACK-final.md').read_text().replace('Evidence content is closed; remote archive binding/final package manifest pending.','Evidence is closed with the outer remote archive receipt bound; final exact landing/SHA manifests accompany this packet.');(P/'ACK-final.md').write_text(s)
# Preserve original draft ACK as history without letting it serve as final token.
(P/'historical-recipes/README.md').write_text((P/'historical-recipes/README.md').read_text()+'\nThe r4 archive identifies `video_probe_r3.py` as the actual basic probe (two IID slots plus player cache slot); `video_probe_swipe_r4.py` is the additional swipe group. Original probe unknown values are retained; the later reread is separate.\n')
print('closed evidence',len([f for f in P.rglob('*') if f.is_file()]))
