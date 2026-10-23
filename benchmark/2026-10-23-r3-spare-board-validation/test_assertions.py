import importlib.util,json,tempfile
from pathlib import Path
p=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('prep',p/'prepare.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
cases=[]
def check(name,fn,fail=False):
 try:fn();ok=not fail
 except (ValueError,OSError):ok=fail
 cases.append({'name':name,'passed':ok})
b=(p/'prepared-01/init.before.cfg').read_bytes();a=(p/'prepared-01/init.after.cfg').read_bytes()
check('actual_init_one_argv',lambda: m.derive_init(b)==a or (_ for _ in ()).throw(ValueError()))
check('init_drift',lambda:m.derive_init(b+b' '),True)
old=b"STARTUP_ENABLED='0'\nSTARTUP_APPROVED_BY='DISABLED-PENDING-OUTER'\nX='unchanged'\n";new=old.replace(b"ENABLED='0'",b"ENABLED='1'").replace(b'DISABLED-PENDING-OUTER',b'outer(codex)')
check('two_fields_allowed',lambda:m.allowed_promotion(old,new))
check('third_field_refused',lambda:m.allowed_promotion(old,new.replace(b'unchanged',b'changed')),True)
check('unchanged_not_promoted',lambda:m.allowed_promotion(old,old),True)
check('duplicate_field',lambda:m.allowed_promotion(old+ b"STARTUP_ENABLED='0'\n",new),True)
with tempfile.TemporaryDirectory() as td:
 td=str(Path(td).resolve())
 f=Path(td)/'f';f.write_bytes(b'inert');link=Path(td)/'link';link.symlink_to(f)
 check('regular_file',lambda:m.regular(f));check('symlink_refused',lambda:m.regular(link),True)
 check('traversal_refused',lambda:m.regular(Path(td)/'..'/Path(td).name/'f'),True)
print(json.dumps({'cases':cases,'passed':sum(c['passed'] for c in cases),'total':len(cases),'scope':'Synthetic promotion strings and real init config only; no promoted runtime package produced.'},indent=2));raise SystemExit(0 if all(c['passed'] for c in cases) else 1)
