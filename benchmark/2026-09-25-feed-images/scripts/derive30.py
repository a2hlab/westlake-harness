from common30 import *
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[3]/'harness'))
from westlake_gap.gapmap import shadowed_libraries
rows=json.loads((R/'elf-and-errors.json').read_text())
scan={'inventory':{'elfs':[{'name':x['library'],'needed':x['needed']} for x in rows]}}
shadowed,reach=shadowed_libraries(scan,['/system/lib64/libc++_shared.so'])
profile=json.loads((pathlib.Path(__file__).parents[1]/'targets.json').read_text())
checks={x:x in reach for x in profile['additional_targets']}
result={'tool':'#19 shadowed_libraries DT_NEEDED reverse closure','shadowed':shadowed,'all_reaching_libcxx':reach,'additional_target_membership':checks,'note':'Closure is a static superset, not proof every library is reached by this UI run. Selected full profile uses observed #26 failures plus HEIF dependency.'}
(R/'target-derivation.json').write_text(json.dumps(result,indent=2)+'\n');print('closure',len(reach),'additional checks',checks)
