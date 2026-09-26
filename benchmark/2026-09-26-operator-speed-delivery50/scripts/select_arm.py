from pathlib import Path
import sys
arm=sys.argv[1];assert arm in ('base','speed');p=Path(__file__).with_name('board_api.py');sys.argv=[str(p),'deployment','inspect'];x={'__file__':str(p)};exec(p.read_text(),x);r=x['r'];r.mkdir(exist_ok=True);dev=x['dev'];rt=x['rt'];F='/data/local/tmp/operator45/selfheal48'
assert not dev('pidof com.ss.android.article.news appspawn-x',5).strip();assert 'STOPPED' in dev('test -f '+F+'/stop && test ! -d '+F+'/lock && echo STOPPED',5)
if arm=='speed':cmd='test ! -e '+rt+'/oat/arm64 && mkdir -p '+rt+'/oat && mv '+rt+'/operator-speed50-oat '+rt+'/oat/arm64'
else:cmd='if [ -e '+rt+'/oat/arm64 ]; then test ! -e '+rt+'/operator-speed50-oat && mv '+rt+'/oat/arm64 '+rt+'/operator-speed50-oat; fi'
out=dev(cmd+'; echo STATE; ls -ld '+rt+'/oat/arm64 '+rt+'/operator-speed50-oat; cat /proc/uptime',10);(r/('select-'+arm+'-'+str(__import__('time').time())+'.txt')).write_text(out);print(out)
