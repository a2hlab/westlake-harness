"""New publication seam only; does not repeat core generation/consumer tests."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import verify_physical_links as physical

class PhysicalLinkTests(unittest.TestCase):
 def test_actual_main_baseline_read_only(self):
  result=physical.verify(physical.BASELINE,final=False)
  self.assertEqual(result['canonical_rows'],315)
  self.assertEqual(result['links_each_language'],142)
  self.assertFalse(result['actual_final61b_checked']);self.assertFalse(result['fixed_origin_used'])
  if (physical.FINAL/'api-progress.json').is_file():
   final=physical.verify(physical.FINAL,final=True)
   self.assertTrue(final['actual_final61b_checked'])
 def test_extra_directory_rejected(self):
  with tempfile.TemporaryDirectory(prefix='wrong-depth-',dir=physical.HERE) as tmp:
   with self.assertRaisesRegex(ValueError,'directory'):physical.verify(tmp,final=False)
 def test_rendered_href_wrong_level_rejected_from_real_main_parent(self):
  original=Path.read_text;target=physical.BASELINE/'index.html'
  def substituted(path,*args,**kwargs):
   text=original(path,*args,**kwargs)
   if path==target:
    marker='const evidenceLinks=';prefix,rest=text.split(marker,1);encoded,last=rest.split(';\nfunction link(',1)
    mappings=json.loads(encoded);key=next(iter(mappings));mappings[key]='../'+mappings[key]
    return prefix+marker+json.dumps(mappings,ensure_ascii=False)+';\nfunction link('+last
   return text
  with patch.object(Path,'read_text',substituted):
   with self.assertRaises((ValueError,OSError)):physical.verify(physical.BASELINE,final=False)
 def test_pending_mapping_and_core_sha_unchanged(self):
  pending=physical.read(physical.HERE/'publication.pending.json')
  self.assertIsNone(pending['actual_main_physical_link_receipt']);self.assertIsNone(pending['actual_view_files'])
  core=physical.HERE.parent/'2026-10-14-api-progress-final61b'
  freeze=physical.read(core/'freeze.json')
  repo=physical.HERE.parents[1]
  for ref in freeze['files']:self.assertEqual(physical.sha(repo/ref['path']),ref['sha256'])

if __name__=='__main__':unittest.main()
