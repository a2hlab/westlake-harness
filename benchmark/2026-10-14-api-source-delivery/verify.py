#!/usr/bin/env python3
"""Original315 data checks, refusal tests and physical landing simulation; offline only."""
import argparse,json,unittest
import generate as g
import publication_check as pub
import test_generate

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--request',type=g.Path)
 args=parser.parse_args()
 request_path=args.request or next(p for p in (g.HERE/'final-v3-inputs/request.json',g.HERE/'final-v2-inputs/request.json',g.HERE/'final-inputs/request.json',g.HERE/'inputs/request.json') if p.is_file())
 request=g.read(request_path)
 tests=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(test_generate))
 g.need(tests.wasSuccessful(),'source delivery refusal tests failed')
 if (g.HERE/'views/api-progress.json').is_file():
  mapping=g.HERE/request['mapping']
  result=g.check(mapping,request['mapping_sha256'],g.HERE/'views');links=pub.simulate(g.HERE/'views')
  result={k:v for k,v in result.items() if k!='known_source_build_refs'}
  result.update(physical_simulation_links_per_language=links['links_per_language'],physical_simulation_markdown_links=links['markdown_links'])
 else:result={'status':'RENDERER_GATES_VERIFIED_FINAL_VIEWS_PENDING_ALL_SOURCE_LANDED','views_checked':False,'source_delivery_complete':False,'device_calls':0,'builds_executed':0}
 result.update(test_cases=tests.testsRun,human_review='pending_review',final_source_mapping='BOUND_STABLE_MAPPING' if request.get('source_delivery_final') is True else 'pending',api_semantic_grade_changed=False)
 print(json.dumps(result,ensure_ascii=False));return 0
if __name__=='__main__':raise SystemExit(main())
