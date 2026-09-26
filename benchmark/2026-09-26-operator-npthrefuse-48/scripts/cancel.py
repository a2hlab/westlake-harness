from pathlib import Path
import sys,json,time
name=sys.argv[1];p=Path(__file__).with_name('warm48.py');sys.argv=[str(p),name,'inspect'];x={'__file__':str(p)};exec(p.read_text().split('if op in (')[0],x)
d=json.loads((x['r']/'instance.json').read_text());(x['r']/'cancelled.json').write_text(json.dumps({'reason':'User superseded refusal test with direct npth patch', 'epoch':time.time()}));print(x['cleanup'](d['parent'],d['child']))
