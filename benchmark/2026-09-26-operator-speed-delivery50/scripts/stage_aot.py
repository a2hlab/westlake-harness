from pathlib import Path
import sys,json
p=Path(__file__).with_name('board_api.py');sys.argv=[str(p),'deployment','inspect'];x={'__file__':str(p)};exec(p.read_text(),x);r=x['r'];r.mkdir(exist_ok=True);dev=x['dev'];rt=x['rt'];bundle=Path.home()/'a2hlab/ws/out-speed-delivery50/speed-clamp';record=json.loads((bundle/'build.json').read_text());off=rt+'/operator-speed50-oat'
(r/'disk-before.txt').write_text(dev('df -k '+rt,5));dev('mkdir -p '+off,5)
for n,v in record['artifacts'].items():
 x['hdc'](['file','send',n,off+'/'+n],bundle,55)
 out=dev('sha256sum '+off+'/'+n,30);assert out.split()[0]==v['sha256'];print(out,flush=True)
s=dev('chown -R 20010053:20010053 '+off+'; chmod 755 '+off+'; chmod 644 '+off+'/*; chcon -R u:object_r:data_app_el2_file:s0 '+off+'; sha256sum '+off+'/*; ls -lZ '+off,15);(r/'staged.txt').write_text(s)
