"""Whole-DEX 166-key scan with compact call graph, Activity resources and JNI consumers."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

import rules

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

CALL=re.compile(r'(L[^ ;]+;)\.([^\s:]+):(\([^ ]*\).+)\s+// method@')


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def manifest(text):
    stack=[]
    nodes=[]
    for number,line in enumerate(text.splitlines(),1):
        stripped=line.lstrip()
        depth=len(line)-len(stripped)
        if stripped.startswith('E: '):
            while stack and stack[-1]['depth']>=depth:
                stack.pop()
            node=dict(tag=stripped.split()[1],depth=depth,attrs={},children=[],line=number)
            (stack[-1]['children'] if stack else nodes).append(node)
            stack.append(node)
        elif stripped.startswith('A: ') and stack:
            field,value=stripped[3:].split('=',1)
            name=field.split('(')[0].rsplit(':',1)[-1]
            stack[-1]['attrs'][name]=value.split('"')[1] if value.startswith('"') else value.split()[0]
    root=next(node for node in nodes if node['tag']=='manifest')
    package=root['attrs']['package']
    app=next(node for node in root['children'] if node['tag']=='application')
    qualified=lambda name: package+name if name.startswith('.') else name if '.' in name else package+'.'+name
    activities=[]
    launchers=[]
    for node in app['children']:
        if node['tag'] not in {'activity','activity-alias'}:
            continue
        entry=dict(name=qualified(node['attrs']['name']),target=qualified(node['attrs'].get('targetActivity',node['attrs']['name'])),
                   theme=node['attrs'].get('theme',app['attrs'].get('theme')),line=node['line'],alias=node['tag']=='activity-alias',
                   enabled=node['attrs'].get('enabled','true') not in {'false','0','0x00000000'})
        activities.append(entry)
        for child in node['children']:
            actions={desc['attrs'].get('name') for desc in child['children'] if desc['tag']=='action'}
            categories={desc['attrs'].get('name') for desc in child['children'] if desc['tag']=='category'}
            if 'android.intent.action.MAIN' in actions and 'android.intent.category.LAUNCHER' in categories and entry['enabled']:
                launchers.append(entry['target'])
    early=[qualified(app['attrs']['name'])] if app['attrs'].get('name') else []
    early.extend(qualified(node['attrs']['name']) for node in app['children'] if node['tag']=='provider' and node['attrs'].get('name'))
    return dict(package=package,activities=activities,launchers=sorted(set(launchers)),early_owners=early)


def parse_dex(lines, dex):
    classes={}
    methods={}
    owner=name=current=None
    in_methods=False
    for number,line in enumerate(lines,1):
        if "Class descriptor  : '" in line:
            owner=line.split("'")[1]
            classes[owner]=None
            current=None
            in_methods=False
        elif line.startswith('  Superclass'):
            classes[owner]=line.split("'")[1] if "'" in line else None
        elif line.startswith(('  Direct methods','  Virtual methods')):
            in_methods=True
        elif in_methods and re.match(r'    #\d+\s+: \(in ',line):
            current=name=None
        elif in_methods and line.startswith('      name'):
            name=line.split("'")[1]
        elif in_methods and name and line.startswith('      type'):
            descriptor=line.split("'")[1]
            current=dict(owner=owner,name=name,descriptor=descriptor,dex=dex,line=number,branches=0,callees=set(),sites=[],class_constants=[])
            methods[owner+'->'+name+descriptor]=current
        elif current is not None:
            instruction=re.search(r'\|([0-9a-f]{4,}): (.+)',line)
            if not instruction:
                continue
            offset,body=instruction.groups()
            opcode=body.split()[0]
            current['branches']+=int(opcode.startswith(('if-','packed-switch','sparse-switch')))
            call=CALL.search(body) if opcode.startswith('invoke-') else None
            if call:
                target_owner,target_name,descriptor=call.groups()
                target=target_owner+'->'+target_name+descriptor
                current['callees'].add(target)
                if target_name in {'setSupportActionBar','setTheme','startActivity','startActivityForResult'} or rules.constructor(dict(owner=target_owner,name=target_name)):
                    current['sites'].append(dict(owner=target_owner,name=target_name,descriptor=descriptor,target=target,
                                                line=number,offset=offset,instruction=body))
            elif opcode=='const-class':
                match=re.search(r', (L[^ ;]+;)',body)
                if match:
                    current['class_constants'].append(dict(owner=match[1],line=number,offset=offset))
    return classes,methods


def inspect(entry, args):
    apk=Path(entry['path'])
    payload=apk.read_bytes()
    if digest(payload)!=entry['apk_sha256']:
        raise ValueError('APK hash mismatch: '+entry['key'])
    xml=subprocess.check_output([args['aapt2'],'dump','xmltree',str(apk),'--file','AndroidManifest.xml'],text=True)
    declared=manifest(xml)
    if declared['package']!=entry['package']:
        raise ValueError('Manifest package mismatch: '+entry['key'])
    resource=subprocess.check_output([args['aapt2'],'dump','resources',str(apk)],text=True,errors='replace')
    styles=rules.parse_styles(resource)
    classes={}
    methods={}
    inventory=[]
    with zipfile.ZipFile(apk) as archive,tempfile.TemporaryDirectory(prefix='b10-theme-dex-') as temporary:
        for member in sorted(archive.namelist()):
            if not re.fullmatch(r'classes\d*\.dex',member):
                continue
            data=archive.read(member)
            path=Path(temporary)/member
            path.write_bytes(data)
            with tempfile.TemporaryFile() as errors:
                process=subprocess.Popen([args['dexdump'],'-d',str(path)],stdout=subprocess.PIPE,stderr=errors,text=True,errors='replace')
                parsed_classes,parsed_methods=parse_dex(process.stdout,member)
                process.stdout.close()
                if process.wait():
                    raise ValueError('DEX tool failed: '+entry['key'])
            if set(classes)&set(parsed_classes):
                raise ValueError('Duplicate DEX class: '+entry['key'])
            classes.update(parsed_classes)
            methods.update(parsed_methods)
            inventory.append(dict(member=member,sha256=digest(data)))
    actual_launchers=set(declared['launchers'])
    if entry.get('launch_activity'):
        actual_launchers={entry['launch_activity']}
    contexts={}
    caps={}
    for activity in sorted(actual_launchers|{node['target'] for node in declared['activities'] if node['enabled']}|set(declared['early_owners'])):
        contexts[activity],caps[activity]=rules.reach(rules.roots(activity,classes,methods),classes,methods)
    startup_contexts=actual_launchers|set(declared['early_owners'])
    bar=[]
    graphics=[]
    transitions=[]
    dynamic_themes=[]
    for identifier,method in methods.items():
        for site in method['sites']:
            witness=dict(method=identifier,dex=method['dex'],**site)
            contexts_here=[dict(activity=activity,tier='startup-chain' if activity in startup_contexts else 'later-activity-lifecycle',**reached[identifier])
                           for activity,reached in contexts.items() if identifier in reached]
            witness['contexts']=contexts_here
            witness['scope']='whole-DEX reference; no lifecycle path' if not contexts_here else 'bounded eight-edge exact-owner call graph; branches/callbacks/dispatch remain conditional'
            if rules.actionbar(site,classes):
                witness['library_caller']=method['owner'].startswith(('Landroidx/','Landroid/support/'))
                bar.append(witness)
            if rules.constructor(site):
                graphics.append(witness)
            if site['name'].startswith('startActivity') and contexts_here:
                transitions.append(dict(witness,class_constants=method['class_constants']))
            if site['name']=='setTheme':
                dynamic_themes.append(witness)
    themed=[]
    for activity in declared['activities']:
        themed.append({**activity,'resolved_theme':rules.theme(activity['theme'],styles)})
    return dict(key=entry['key'],package=entry['package'],apk_sha256=entry['apk_sha256'],cohort=entry['cohort'],
        dex=inventory,manifest_sha256=digest(xml.encode()),resource_dump_sha256=digest(resource.encode()),
        manifest=dict(launchers=sorted(actual_launchers),activities=themed,early_owners=declared['early_owners']),
        actionbar_calls=bar,graphics_calls=graphics,transitions=transitions,set_theme_calls=dynamic_themes,
        counts=dict(classes=len(classes),methods=len(methods),dex=len(inventory),actionbar_calls=len(bar),graphics_calls=len(graphics)),
        reachability=dict(depth=8,capped_contexts=sorted(activity for activity,capped in caps.items() if capped),
            limitation='Non-reached references are not proved post-frame calls; Activity transitions use literal class witnesses only, no branch or Intent argument inference'))


def inputs(workspaces):
    frozen=json.loads((ROOT/'benchmark/2026-10-01-u7-prospective/v1/inputs.json').read_text())['apps']
    legacy=json.loads((ROOT/'benchmark/2026-09-28-bms-route-deploy/batch/apps.json').read_text())['apps']
    if {row['key'] for row in frozen}!={row['key'] for row in legacy}:
        raise ValueError('Old corpus key mismatch')
    rows=[dict(key=row['key'],package=row['package'],apk_sha256=row['apk_sha256'],launch_activity=row.get('launch_activity'),
               path=str(Path.home()/'a2hlab/app-inputs'/row['key']/row['selected_apk']),cohort='u7-66') for row in frozen]
    selection=json.loads((ROOT/'benchmark/2026-10-01-corpus-v2/results.json').read_text())['rows']
    manifest_rows=json.loads((ROOT/'benchmark/2026-10-01-cv2-scoring/run-evidence.json').read_text())['rows']
    by_package={row['package']:row for row in manifest_rows}
    rows.extend(dict(key=by_package[row['package']]['key'],package=row['package'],apk_sha256=row['sha256'],launch_activity=None,
                     path=str(workspaces/'westlake-inputs/corpus-v2/apks'/Path(row['apk_url']).name),cohort='cv2-100') for row in selection)
    if len(rows)!=166 or len({row['key'] for row in rows})!=166:
        raise ValueError('Incomplete/duplicate 166 cohort')
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspaces',type=Path,default=Path(os.environ.get('WORKSPACES',ROOT.parent)))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--keys',nargs='*')
    args=parser.parse_args()
    entries=inputs(args.workspaces)
    if args.keys:
        entries=[entry for entry in entries if entry['key'] in args.keys]
    tools={name:str(Path.home()/'Library/Android/sdk/build-tools/37.0.0'/name) for name in ['aapt2','dexdump']}
    with ProcessPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(inspect,entry,tools) for entry in entries]
        apps=[]
        for future in futures:
            app=future.result()
            apps.append(app)
            print('scanned',len(apps),app['key'],app['counts'],flush=True)
    result=dict(schema='b10-theme-graphics-facts-v1',apps=apps,tools={name:digest(Path(path).read_bytes()) for name,path in tools.items()},
                scanner_dependencies={str(path.relative_to(ROOT)):digest(path.read_bytes()) for path in [Path(__file__),HERE/'rules.py']})
    args.output.write_text(json.dumps(result,sort_keys=True)+'\n')


if __name__=='__main__':
    main()
