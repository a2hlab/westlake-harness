"""Offline theme and constructor contracts; callsite absence is not safety proof."""

from collections import deque
import re

FAMILY = re.compile(r'^Landroid/graphics/\w*(?:MaskFilter|PathEffect|Shader|Gradient|ColorFilter);$')
NATIVE_FAMILY = re.compile(r'^android/graphics/\w*(?:MaskFilter|PathEffect|Shader|Gradient|ColorFilter)\.native')
COMPAT = {'Landroidx/appcompat/app/AppCompatActivity;', 'Landroidx/appcompat/app/AppCompatDelegate;',
          'Landroidx/appcompat/app/AppCompatDelegateImpl;', 'Landroid/support/v7/app/AppCompatActivity;',
          'Landroid/support/v7/app/AppCompatDelegate;', 'Landroid/support/v7/app/AppCompatDelegateImpl;'}
LIFECYCLE = [('<init>', None), ('<clinit>', '()V'), ('onCreate', '(Landroid/os/Bundle;)V'),
             ('onCreate', '(Landroid/os/Bundle;Landroid/os/PersistableBundle;)V'),
             ('onPostCreate', '(Landroid/os/Bundle;)V'),
             ('onPostCreate', '(Landroid/os/Bundle;Landroid/os/PersistableBundle;)V'),
             ('onStart', '()V'), ('onResume', '()V'), ('onPostResume', '()V')]


def ancestors(owner, classes):
    seen=[]
    while owner and owner not in seen:
        seen.append(owner)
        owner=classes.get(owner)
    return seen


def resolve(identifier, classes, methods):
    owner, signature=identifier.split('->',1)
    return next((candidate for parent in ancestors(owner,classes) if (candidate:=parent+'->'+signature) in methods),None)


def actionbar(call, classes):
    return call['name']=='setSupportActionBar' and bool(set(ancestors(call['owner'],classes)) & COMPAT)


def constructor(call):
    return bool(FAMILY.match(call['owner'])) and (call['name']=='<init>' or call['name'].startswith('native'))


def roots(activity, classes, methods):
    owner='L'+activity.replace('.','/')+';'
    output=[]
    for name, descriptor in LIFECYCLE:
        if descriptor is None:
            output.extend(identifier for identifier,method in methods.items() if method['owner']==owner and method['name']==name)
        elif found:=resolve(owner+'->'+name+descriptor,classes,methods):
            output.append(found)
    return sorted(set(output))


def reach(start, classes, methods, depth_limit=8):
    pending=deque((identifier,[identifier],False) for identifier in start)
    visited={}
    capped=False
    while pending:
        identifier,path,conditional=pending.popleft()
        if identifier in visited:
            continue
        method=methods[identifier]
        conditional=conditional or bool(method['branches'])
        visited[identifier]=dict(path=path,conditional=conditional)
        if len(path)>depth_limit:
            capped=capped or bool(method['callees'])
            continue
        for target in sorted(method['callees']):
            if resolved:=resolve(target,classes,methods):
                pending.append((resolved,path+[resolved],conditional))
    return visited,capped


def parse_styles(text):
    styles={}
    current=variant=None
    for number,line in enumerate(text.splitlines(),1):
        header=re.match(r'\s*resource (0x[0-9a-f]+) ([\w:]+)/(\S+)',line)
        if header:
            current=header[1] if header[2].split(':')[-1]=='style' else None
            variant=None
            if current:
                styles[current]=dict(name=header[3],line=number,variants=[])
            continue
        if current is None:
            continue
        value=re.match(r'\s*\(([^)]*)\) \(style\) size=\d+(?: parent=.+?\((0x[0-9a-f]+)\))?',line)
        if value:
            variant=dict(config=value[1],parent=value[2],line=number,flags={},evidence=[])
            styles[current]['variants'].append(variant)
            continue
        flag=re.match(r'\s*((?:android:)?window(?:ActionBar|NoTitle))\(0x[0-9a-f]+\)=(true|false)',line)
        if flag and variant is not None:
            variant['flags'][flag[1]]=flag[2]=='true'
            variant['evidence'].append(dict(line=number,text=line.strip()))
    return styles


def theme(style, styles, seen=()):
    style=style.removeprefix('@') if style else None
    if not style or style not in styles or style in seen:
        return dict(reference=style,status='unknown-external-missing-or-cyclic-style',flags={},evidence=[])
    node=styles[style]
    configurations=[]
    evidence=[dict(reference=style,name=node['name'],line=node['line'])]
    for variant in node['variants']:
        parent=theme(variant['parent'],styles,seen+(style,)) if variant['parent'] else dict(flags={},evidence=[])
        flags={**parent['flags'],**variant['flags']}
        configurations.append(flags)
        evidence.extend(parent['evidence'])
        evidence.append(dict(reference=style,config=variant['config'],parent=variant['parent'],line=variant['line'],values=variant['evidence']))
    names={'windowActionBar','windowNoTitle','android:windowActionBar','android:windowNoTitle'}
    flags={}
    for name in sorted(names):
        values={variant.get(name) for variant in configurations}
        if len(values)==1 and None not in values:
            flags[name]=next(iter(values))
    no_action_bar=flags.get('windowActionBar') is False or flags.get('android:windowActionBar') is False
    distinct=list({json_key(item):item for item in evidence}.values())
    return dict(reference=style,name=node['name'],status='no-actionbar-explicit-in-all-local-variants' if no_action_bar else 'actionbar-or-variant-parent-unknown',
                flags=flags,evidence=distinct,
                limits='Local style-parent variants only; Android and AppCompat attribute namespaces separate; unresolved external parents/config selection not guessed')


def json_key(value):
    import json
    return json.dumps(value,sort_keys=True)


def throw_class(instructions):
    calls=[row for row in instructions if re.search(r'\b(?:bl|b)\b',row['text']) and re.search(r'doThrow|ThrowIAE|jniThrow|throwException|throwIllegal',row['text'],re.I)]
    if not calls:
        return dict(status='no-direct-throw-witness',calls=[],limits='Transitive callees arguments allocation and Java validation can still throw')
    first=calls[0]['address']
    branch=any(row['address']<first and re.search(r'\b(?:cbz|cbnz|tbz|tbnz|b\.[a-z]+)\b',row['text']) for row in instructions)
    return dict(status='conditional-direct-throw' if branch else 'unconditional-normal-path-direct-throw',calls=calls,
                limits='Disassembly path classification only; helper exceptions/unwinding and caller argument validity remain separate')
