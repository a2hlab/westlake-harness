import gzip,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import compare_maps as m
class Maps(unittest.TestCase):
 def test_same_uid_other_launch_is_excluded_and_segments_deduplicate(self):
  with tempfile.TemporaryDirectory() as td:
   h=Path(td);r=h/'runs/run'/m.SERIAL/'app';r.mkdir(parents=True)
   (r/'record.json').write_text(json.dumps(dict(clicked_at=100,finished_at=110,bms={'uid':200},observed_pids=[123])))
   obs=[]
   for time,inodes in [(1,[1,2]),(105,[3,3]),(200,[4,5])]:
    text='PID PPID UID NAME\n123 9 200 app\nMAPS_BEGIN:123\n'+''.join('100-200 r-xp 0000 08:01 '+str(i)+' /lib/liblog.so\n' for i in inodes)+'MAPS_END:123\n'
    f=str(time)+'.gz';(h/f).write_bytes(gzip.compress(text.encode()))
    libs={lib:[] for lib in m.LIBS};libs['liblog.so']=[['08:01',str(i)] for i in sorted(set(inodes))]
    obs.append(dict(time=time,file=f,processes=[dict(pid=123,libraries=libs)]))
   (h/'maps-observations.jsonl').write_text(''.join(json.dumps(o)+'\n' for o in obs))
   with patch.object(m,'H',h):result=m.collect('run','app','n8')
   self.assertEqual(len(result['samples']),1);self.assertEqual(result['counts']['liblog.so'],1)
 def test_incomplete_record_is_unknown(self):
  with tempfile.TemporaryDirectory() as td:
   h=Path(td);r=h/'runs/run'/m.SERIAL/'app';r.mkdir(parents=True);(r/'record.json').write_text('{}')
   with patch.object(m,'H',h):self.assertEqual(m.collect('run','app','n8')['status'],'unknown')
if __name__=='__main__':unittest.main()
