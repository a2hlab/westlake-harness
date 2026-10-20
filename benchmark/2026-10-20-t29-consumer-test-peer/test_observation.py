"""Validator rejection tests only; real consumer coverage comes from method-ready execution."""
import copy,unittest
import review_observation as r
ID={'state':0x10,'image':0x20,'first':0x30,'second':0x40}
def record():
    return {'self':'1','p':'2','v':format(r.STATE|r.IMAGE|r.OH|r.RAW,'x'),'state':'10','image':'20','oh':'40',
            'called':'1','raw':'0','rc':'0','det':'0/0','rel':'0/0','ref':'0/0/0','unref':'0/0/0',
            'exbranch':'0','oldw':'0','neww':'0','tex':'0'}
class Observation(unittest.TestCase):
    def test_oh_is_window_and_update_detached_unknown(self):
        source=record();r.verify('update/ok',ID,[source])
        for field,value in [('self','0'),('oh','20'),('det','1/1'),('v',format(int(source['v'],16)|r.DETACHED,'x'))]:
            bad=dict(source);bad[field]=value
            with self.subTest(field=field),self.assertRaises(AssertionError):r.verify('update/ok',ID,[bad])
    def test_invalid_and_missing_records_reject(self):
        with self.assertRaises(AssertionError):r.verify('update/null-state',ID,[record()])
        with self.assertRaises(AssertionError):r.verify('producer/field-unset',ID,[])
    def test_distinct_ref_unref_results(self):
        destroy=record();destroy.update(p='4',v=format(r.OH|r.OLD|r.UNREF,'x'),oh='30',oldw='30',unref='1/1/-31')
        create=record();create.update(p='3',v=format(r.OH|r.OLD|r.NEW|r.REF|r.UNREF,'x'),oh='40',oldw='30',neww='40',ref='1/1/-29',unref='1/1/-31')
        r.verify('producer/ref-unref-error',ID,[destroy,create])
        for which,field,value in [(0,'unref','1/1/-29'),(1,'ref','1/1/-31'),(0,'unref','1/0/0')]:
            rows=copy.deepcopy([destroy,create]);rows[which][field]=value
            with self.subTest(which=which),self.assertRaises(AssertionError):r.verify('producer/ref-unref-error',ID,rows)
if __name__=='__main__':unittest.main()
