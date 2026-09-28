#!/usr/bin/env python3
"""Auto-fix OH build: repeatedly build, detect errors, fix config, retry."""
import json, subprocess, re, os, glob, sys, time

CONFIG = '/root/oh/vendor/hihope/dayu210/config.json'
OH_ROOT = '/root/oh'
BUILD_LOG = '/root/oh_build.log'
MAX_ATTEMPTS = 30

def load_config():
    with open(CONFIG) as f:
        return json.load(f)

def save_config(d):
    with open(CONFIG, 'w') as f:
        json.dump(d, f, indent=2)

def remove_comp(name):
    d = load_config()
    for s in d['subsystems']:
        s['components'] = [c for c in s['components'] if (c['component'] if isinstance(c,dict) else c) != name]
    d['subsystems'] = [s for s in d['subsystems'] if s['components']]
    save_config(d)

def add_comp(name, subsys):
    d = load_config()
    found = False
    for s in d['subsystems']:
        if s['subsystem'] == subsys:
            existing = {c['component'] if isinstance(c,dict) else c for c in s['components']}
            if name not in existing:
                s['components'].append({'component': name, 'features': []})
            found = True
            break
    if not found:
        d['subsystems'].append({'subsystem': subsys, 'components': [{'component': name, 'features': []}]})
    save_config(d)

def comp_count():
    d = load_config()
    return sum(len(s['components']) for s in d['subsystems'])

def find_comp_info(name):
    for bj in glob.glob(os.path.join(OH_ROOT, '**', 'bundle.json'), recursive=True):
        if '/out/' in bj:
            continue
        try:
            with open(bj) as f:
                bd = json.load(f)
            comp = bd.get('component', {})
            if comp.get('name') == name:
                subsys = comp.get('subsystem', '')
                dest = bd.get('segment', {}).get('destPath', '')
                adapted = comp.get('adapted_system_type', [])
                full = os.path.join(OH_ROOT, dest) if dest else os.path.dirname(bj)
                is_standard = not adapted or 'standard' in adapted
                return {'subsystem': subsys, 'exists': os.path.isdir(full), 'standard': is_standard}
        except:
            pass
    return None

def run_build():
    # Force clean with find to handle permission issues
    os.system('find {0}/out/rk3588 -delete 2>/dev/null; rm -rf {0}/out/rk3588 {0}/out/preloader 2>/dev/null; mkdir -p {0}/out/rk3588'.format(OH_ROOT))
    ret = os.system('cd {} && ./build.sh --product-name dayu210 --ccache --gn-args allow_sanitize_debug=true --build-target abilityms --build-target appmgr --build-target wms --build-target bms > {} 2>&1'.format(OH_ROOT, BUILD_LOG))
    return ret

def check_result():
    with open(BUILD_LOG) as f:
        log = f.read()

    if re.search(r'\[\d+/\d+\]', log):
        matches = re.findall(r'\[(\d+)/(\d+)\]', log)
        return 'ninja', matches[-1] if matches else ('?','?')

    err = ''
    try:
        with open(os.path.join(OH_ROOT, 'out/rk3588/error.log')) as f:
            err = f.read()
    except:
        pass

    m = re.search(r'OHOS component : \((\w+)\) not found', err)
    if m:
        return 'comp_missing', m.group(1)

    m = re.search(r'Unable to load "([^"]+)"', err)
    if m:
        return 'file_missing', m.group(1)

    if 'Assertion failed' in err:
        return 'assertion', err[:500]

    m = re.search(r'find component (\w+) failed', log)
    if m:
        return 'load_fail', m.group(1)

    if 'Script returned non-zero' in err:
        m2 = re.search(r'ERROR at (//\S+)', err)
        return 'script_error', m2.group(1) if m2 else 'unknown'

    if 'Undefined identifier' in err:
        m2 = re.search(r'ERROR at (//\S+)', err)
        return 'undefined_id', m2.group(1) if m2 else 'unknown'

    # Also check for BUILD Failed with component errors in error.log
    m = re.search(r'BUILD Failed', log)
    if m and err:
        m2 = re.search(r'OHOS component : \((\w+)\) not found', err)
        if m2:
            return 'comp_missing', m2.group(1)
        m3 = re.search(r'OHOS innerapi: \((\w+)\) not found', err)
        if m3:
            return 'innerapi_missing', m3.group(1)

    return 'unknown', log[-500:]

def find_owning_comp(gn_path):
    path = gn_path.replace('//', OH_ROOT + '/').split(':')[0]
    dir_path = os.path.dirname(path) if not os.path.isdir(path) else path
    while dir_path and dir_path != OH_ROOT and len(dir_path) > len(OH_ROOT):
        bj = os.path.join(dir_path, 'bundle.json')
        if os.path.exists(bj):
            try:
                with open(bj) as f:
                    return json.load(f).get('component', {}).get('name', '')
            except:
                pass
        dir_path = os.path.dirname(dir_path)
    return None

def get_error_source():
    try:
        with open(os.path.join(OH_ROOT, 'out/rk3588/error.log')) as f:
            err = f.read()
        m = re.search(r'ERROR at (//\S+)', err)
        return m.group(1) if m else None
    except:
        return None

print('Starting auto-fix build loop. Components: {}'.format(comp_count()))
sys.stdout.flush()

for attempt in range(1, MAX_ATTEMPTS + 1):
    print('\n=== Attempt {}/{} (comps: {}) ==='.format(attempt, MAX_ATTEMPTS, comp_count()))
    sys.stdout.flush()

    run_build()
    kind, data = check_result()

    if kind == 'ninja':
        print('SUCCESS! GN passed. Ninja progress: [{}/{}]'.format(data[0], data[1]))
        sys.stdout.flush()
        break

    elif kind == 'comp_missing':
        missing = data
        info = find_comp_info(missing)
        if info and info['exists'] and info['standard']:
            add_comp(missing, info['subsystem'])
            print('  Added missing component: {} -> {}'.format(missing, info['subsystem']))
        else:
            src = get_error_source()
            if src:
                owner = find_owning_comp(src)
                if owner:
                    remove_comp(owner)
                    print('  Removed component {} (depends on unavailable {})'.format(owner, missing))
                else:
                    print('  Cannot find owner of {}, manual fix needed'.format(src))
                    break
            else:
                print('  Cannot parse error for {}'.format(missing))
                break

    elif kind == 'load_fail':
        remove_comp(data)
        print('  Removed unresolvable component: {}'.format(data))

    elif kind == 'file_missing':
        src = get_error_source()
        if src:
            owner = find_owning_comp(src)
            if owner:
                remove_comp(owner)
                print('  Removed component {} (missing file: {})'.format(owner, data))
            else:
                print('  Cannot find owner for {}'.format(src))
                break
        else:
            break

    elif kind == 'innerapi_missing':
        # An inner_kit is missing - find and remove the referencing component
        src = get_error_source()
        if src:
            owner = find_owning_comp(src)
            if owner:
                remove_comp(owner)
                print('  Removed component {} (missing innerapi: {})'.format(owner, data))
            else:
                print('  Cannot find owner for {}'.format(src))
                break
        else:
            break

    elif kind == 'script_error' or kind == 'undefined_id':
        owner = find_owning_comp(data) if data != 'unknown' else None
        if owner:
            remove_comp(owner)
            print('  Removed component {} ({} at {})'.format(owner, kind, data))
        else:
            print('  {} at {}, cannot auto-fix'.format(kind, data))
            break

    else:
        print('  Unknown error: {}'.format(str(data)[:200]))
        break

    sys.stdout.flush()

print('\nFinal component count: {}'.format(comp_count()))
sys.stdout.flush()
