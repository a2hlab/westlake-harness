"""One-path read-only extension; original frozen Reader remains byte-identical."""
import os,re,subprocess,uuid
from pathlib import Path
TARGET='/system/etc/init/01_westlake_u13_toutiao.cfg'
def with_absence(base):
 class Reader(base):
  def absent(self,target):
   if target!=TARGET:raise ValueError('absence path not allowed')
   # Never infer absence from sha256sum rc1, permission errors or a failed transport.
   command='set -eu; test -d /system/etc/init; test -r /system/etc/init; test -x /system/etc/init; test ! -L /system; test ! -L /system/etc; test ! -L /system/etc/init; if [ -e '+TARGET+' ] || [ -L '+TARGET+' ]; then echo PRESENT; else echo ABSENT; fi'
   marker='__BOAT_ABSENCE_RC_'+uuid.uuid4().hex+'__'
   import shlex
   script='/system/bin/sh -c '+shlex.quote(command)+'; rc=$?; printf "\\n'+marker+'%s\\n" "$rc"'
   ws=Path(os.environ.get('WORKSPACES',str(Path(__file__).resolve().parents[6])))
   r=subprocess.run(['bash',str(ws/'westlake-inputs/tools/hdc_mac.sh'),'-t',self.serial,'shell',script],capture_output=True,text=True,timeout=90)
   self.n+=1;(self.out/('absence-%03d.stdout.txt'%self.n)).write_text(r.stdout);(self.out/('absence-%03d.stderr.txt'%self.n)).write_text(r.stderr)
   return decode(r.returncode,r.stdout,r.stderr,marker)
 return Reader

def decode(rc,stdout,stderr,marker):
 m=re.search(r'\n'+re.escape(marker)+r'(\d+)\s*$',stdout)
 if rc or stderr or not m or m.group(1)!='0':raise ValueError('absence transport/status/permission failure')
 value=stdout[:m.start()].strip()
 if value not in ('ABSENT','PRESENT'):raise ValueError('unknown absence response')
 return value=='ABSENT'
