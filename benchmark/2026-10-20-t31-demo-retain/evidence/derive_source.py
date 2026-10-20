from pathlib import Path
import hashlib,json,difflib
root=Path.cwd(); main=root.parent/'westlake-harness'; out=root/'benchmark/2026-10-20-t31-demo-retain'; r=out/'recovery';r.mkdir(exist_ok=True)
d=main/'benchmark/2026-10-20-t30-request-recovery/deployment/final-01';h=d.parent/'helpers'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pins={x.relative_to(d).as_posix():sha(x) for x in d.rglob('*') if x.is_file() and '__pycache__' not in x.parts}
(r/'origin-data-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
s=(d/'executor.py').read_text(); t=s
# Exact limited successor, no business transaction redesign.
t=t.replace('choices=[\'preflight\',\'apply\',\'rollback\']',"choices=['rollback']")
t=t.replace("p.add_argument('--start',type=float);", "p.add_argument('--origin-data',type=Path);p.add_argument('--origin-admission',type=Path);p.add_argument('--start',type=float);")
t=t.replace("assert all([a.boot,a.hdc,a.holder,a.out,a.repo,a.inputs,a.admission,a.start]),'explicit inputs'", "assert all([a.boot,a.hdc,a.holder,a.out,a.repo,a.inputs,a.admission,a.start,a.origin_data,a.origin_admission,a.apply_plan]),'explicit recovery inputs'\nassert not a.recovery_no_parent,'T31 requires live identity; no new physical-only authority'")
t=t.replace('here=Path(__file__).resolve().parent', "here=a.origin_data.resolve()\nfrom recovery_policy import validate_origin, validate_window, validate_sources\norigin_plan,origin_admission=validate_origin(here,a.apply_plan,a.origin_admission)\nrecovery_ad=json.loads(a.admission.read_text())\nvalidate_window(recovery_ad,origin_plan,a.holder,a.start,a.boot,time.time())\nvalidate_sources(recovery_ad)\nassert recovery_ad['origin_apply_admission_sha256']==sha_file(a.origin_admission)\nassert recovery_ad['origin_apply_plan_sha256']==sha_file(a.apply_plan)")
t=t.replace("assert apply_plan['executor_sha256']==sha_file(Path(__file__)) and apply_plan['holder']==a.holder and apply_plan['start']==a.start,'same execution window/source'", "assert apply_plan==origin_plan,'origin plan changed during recovery'\n assert apply_plan['executor_sha256']==origin_admission['executor_sha256'] and apply_plan['holder']==origin_admission['holder'] and apply_plan['start']==origin_admission['window_start'],'immutable origin window/source'")
t=t.replace(' if dso_present:pre+=pathguard(absence_backup)', ' pre+=pathguard(absence_backup)')
t=t.replace("  if present:pre+=fg(back,digest,fmeta,flabel)\n  else:assert current==digest,'missing backup for changed target'", "  assert present,'missing durable origin backup'\n  pre+=fg(back,digest,fmeta,flabel)")
t=t.replace("plan['origin_apply_wid']=origin_wid", "plan['origin_apply_wid']=origin_wid;plan['origin_holder']=apply_plan['holder'];plan['origin_start']=apply_plan['start'];plan['origin_apply_admission_sha256']=sha_file(a.origin_admission)")
assert t!=s
(r/'recovery.py').write_text(t)
(r/'executor.delta.patch').write_text(''.join(difflib.unified_diff(s.splitlines(True),t.splitlines(True),fromfile='T30/executor.py',tofile='T31/recovery.py')))
s=(h/'rollback_core.py').read_text();t=s.replace('def fill(repo, context, held, raw, now, plan):\n    from window_paths import deploy\n    d = deploy()', 'def fill(repo, context, held, raw, now, plan, original, d):\n    d = Path(d).resolve()')
t=t.replace('plan["holder"] == holder and\n            plan["start"] == start', 'plan["holder"] == original["holder"] and\n            plan["start"] == original["window_start"]')
(r/'recovery_core.py').write_text(t)
(r/'core.delta.patch').write_text(''.join(difflib.unified_diff(s.splitlines(True),t.splitlines(True),fromfile='T30/rollback_core.py',tofile='T31/recovery_core.py')))
(out/'donors.json').write_text(json.dumps({'executor':{'path':str((d/'executor.py').relative_to(main)),'sha256':sha(d/'executor.py')},'core':{'path':str((h/'rollback_core.py').relative_to(main)),'sha256':sha(h/'rollback_core.py')},'pins_sha256':sha(r/'origin-data-pins.json')},indent=2)+'\n')
