from board25 import *
r=R/('control-'+sys.argv[1]);name=sys.argv[2]+'.jpeg'
remote='/data/local/tmp/pkg28-'+name
dev('snapshot_display -f '+remote+' >/dev/null');recv(remote,r/name)
# Host-visible preview, also archived by export28.py later.
p=pathlib.Path(__file__).resolve().parents[1]/name;p.write_bytes((r/name).read_bytes());print(p)
