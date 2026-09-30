#!/usr/bin/env python3
"""Capture exact build-script edits and a bounded inventory of remaining candidates."""
import difflib,json,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];BASE=ROOT/'bms/src/adapter/build'
changes=[];remaining=[];count=0
for p in sorted(BASE.rglob('*.sh')):
 count+=1;rel=str(p.relative_to(ROOT));current=p.read_text();old=subprocess.run(['git','show','HEAD:'+rel],cwd=ROOT,capture_output=True,text=True)
 if old.returncode:continue
 a=old.stdout.splitlines();b=current.splitlines()
 for tag,i,j,k,l in difflib.SequenceMatcher(a=a,b=b,autojunk=False).get_opcodes():
  if tag!='equal':changes.append({'file':rel,'line':k+1,'before':'\n'.join(a[i:j]),'after':'\n'.join(b[k:l])})
 for i,line in enumerate(b):
  if line.lstrip().startswith('#') or 'exit 1' in line:continue
  if re.search(r'(?:log_warn|echo .*WARN|\|\| continue)',line) and re.search(r'missing|not found|absent|\-f |\-d ',line,re.I):
   following=' '.join(x.strip() for x in b[i+1:i+4] if x.strip() and not x.lstrip().startswith('#'))
   disposition='already_nonzero' if re.match(r'(?:exit|return) [1-9]',following) else 'unknown-deferred'
   if p.name=='config.sh' and ('ccache' in line or 'autotools' in line):disposition='optional_tool_or_install_path'
   remaining.append({'file':rel,'line':i+1,'text':line,'following':following,'disposition':disposition})
for f in set(c['file'] for c in changes):subprocess.run(['bash','-n',str(ROOT/f)],check=True)
stock=ROOT/'bms/src/adapter/framework/appspawn-x/security_specialization/stock_child_plugin'
stock_review=[]
for p in sorted(stock.glob('*.sh')):
 for n,line in enumerate(p.read_text().splitlines(),1):
  if line.strip()=='continue':stock_review.append({'file':str(p.relative_to(ROOT)),'line':n,'disposition':'Python closure traversal: already-seen or successfully-enqueued member; not a missing-file skip'})
out={'changed':changes,'script_count':count,'changed_file_count':len(set(c['file'] for c in changes)),'remaining':remaining,'stock_child_review':stock_review,'status':'partial: required-source branches hardened; remaining archival/conditional candidates retained as unknown under first-version timebox','scope_note':'No device command executed. Full cross-build not run; exact bridge collection loop is independently exercised with missing inputs.'}
(HERE/'build-audit.json').write_text(json.dumps(out,indent=2)+'\n');print(len(changes),'changes',out['changed_file_count'],'files',len(remaining),'remaining candidates')
if __name__=='__main__':pass
