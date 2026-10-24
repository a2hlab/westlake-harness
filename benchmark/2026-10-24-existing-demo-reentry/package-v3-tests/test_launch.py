import hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
PACKAGE=HERE.parent/'launch-package-v3'
SUMMARIES=[]
class LaunchTests(unittest.TestCase):
    def test_01_offline_verification_and_bad_pin(self):
        pin=hashlib.sha256((PACKAGE/'manifest.json').read_bytes()).hexdigest()
        r=subprocess.run([sys.executable,str(PACKAGE/'start.py'),'--manifest-sha',pin],capture_output=True,text=True,timeout=15)
        self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout)['status'],'OFFLINE_PACKAGE_VERIFIED_NO_DEVICE_CALLS')
        r=subprocess.run([sys.executable,str(PACKAGE/'start.py'),'--manifest-sha','0'*64],capture_output=True,text=True,timeout=15)
        self.assertNotEqual(r.returncode,0);self.assertIn('manifest SHA mismatch',r.stderr)
    def test_02_actual_entry_paths(self):
        (HERE/'.fixtures').mkdir(exist_ok=True)
        for mode in ('feed','delayed_feed','usable','white','failure_home_error','child','identity_change','reserve','absent','invalid','busy','bad_hash'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory(dir=HERE/'.fixtures') as root:
                home=Path(root)/'home'
                r=subprocess.run([sys.executable,str(HERE/'fixture_entry.py'),str(home),mode],capture_output=True,text=True,timeout=20)
                self.assertEqual(r.returncode,0,r.stderr+'\n'+r.stdout[-3000:])
                facts=json.loads((home/'fixture-result.json').read_text());calls=facts['calls'];labels=[x['label'] for x in calls];run=Path(facts['run'])
                self.assertEqual(facts['device_calls'],0);self.assertEqual({x['pid'] for x in calls},{facts['pid']})
                self.assertEqual(labels[:4],['00-held','01-identity','02-power','03-hashes'] if mode!='busy' else labels[:4])
                if mode in ('busy','bad_hash'):
                    self.assertNotIn('04-lock',labels);self.assertNotIn('home',labels);self.assertEqual(facts['launcher_rc'],2)
                else:
                    self.assertEqual(labels.count('cleanup-restore'),1);self.assertEqual(labels.count('cleanup-unlock'),1);self.assertTrue(facts['released'])
                    result=json.loads((run/'owner-result.json').read_text());self.assertTrue(result['cleanup']['restored']);self.assertTrue(result['cleanup']['lock_released'])
                    self.assertEqual(result['cleanup']['power_after'],{'base':30000,'override':10000})
                    if mode in ('white','failure_home_error','child'):
                        self.assertEqual(labels.count('home'),1);self.assertEqual(labels.count('click-once'),1);self.assertEqual(labels.count('failure-home-once'),1)
                        self.assertEqual(len([x for x in labels if x.startswith('s') and x.endswith('-shot')]),5)
                        self.assertLess(next(x['at'] for x in calls if x['label']=='failure-home-once'),360)
                        if mode=='failure_home_error':self.assertIn('error',result['cleanup']['failure_home'])
                        if mode=='child':self.assertIn('com.ss.android.article.news',(run/'failure-home-identity.stdout').read_text())
                    elif mode in ('feed','delayed_feed'):
                        self.assertEqual(labels.count('home'),1);self.assertEqual(labels.count('click-once'),1);self.assertNotIn('failure-home-once',labels);self.assertTrue((run/'feed-review-consumed.json').is_file())
                        if mode=='delayed_feed':
                            self.assertEqual(len([x for x in labels if x.startswith('s') and x.endswith('-shot')]),5)
                            feed=json.loads((run/'feed-review-consumed.json').read_text());self.assertEqual(feed['review']['image'],'s120.jpeg')
                            published=json.loads((run/'s120-recv.json').read_text())['end_monotonic'];self.assertGreaterEqual(feed['observed_monotonic']-published,5);self.assertLessEqual(feed['observed_monotonic']-published,15)
                    elif mode in ('usable','absent','invalid'):
                        self.assertNotIn('home',labels);self.assertNotIn('click-once',labels);self.assertNotIn('failure-home-once',labels)
                    else:self.assertNotIn('failure-home-once',labels)
                    if mode not in ('absent','invalid'):
                        review=json.loads((run/'review-consumed.json').read_text());self.assertEqual(review['review']['image'],'unlocked.jpeg');self.assertLess(review['elapsed'],67)
                    self.assertLess(facts['elapsed'],480)
                SUMMARIES.append({'case':mode,'same_owner_pid':facts['pid'],'actual_device_calls':0,'launcher_rc':facts['launcher_rc'],'elapsed':facts['elapsed'],'home':labels.count('home'),'click':labels.count('click-once'),'failure_home':labels.count('failure-home-once'),'restore':labels.count('cleanup-restore'),'unlock':labels.count('cleanup-unlock'),'sample_images':len([x for x in labels if x.startswith('s') and x.endswith('-shot')]),'passed':True})
if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LaunchTests))
    dest=HERE/('cases-'+__import__('datetime').datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
    with dest.open('x') as f:json.dump({'successful':result.wasSuccessful(),'cases':SUMMARIES},f,indent=2)
    print(dest)
    raise SystemExit(0 if result.wasSuccessful() else 1)
