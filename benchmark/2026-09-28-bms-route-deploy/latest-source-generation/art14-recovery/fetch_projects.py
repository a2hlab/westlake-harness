"""Run on hw248 via stdin. Downloads only named AOSP projects; never builds."""
import concurrent.futures
import argparse
import json
import subprocess
from pathlib import Path
TAG = 'android-14.0.0_r1'
parser = argparse.ArgumentParser()
parser.add_argument('--root', required=True, type=Path,
                    help='Authorized versioned download directory on the source host')
ROOT = parser.parse_args().root
PROJECTS = ['art', 'external/cpu_features', 'external/dlmalloc', 'external/fmtlib',
            'external/googletest', 'external/lz4', 'external/lzma', 'external/tinyxml2',
            'external/vixl', 'external/zlib', 'frameworks/native', 'libnativehelper',
            'system/core', 'system/extras', 'system/libbase', 'system/libziparchive',
            'system/logging', 'system/unwinding']
ROOT.mkdir(parents=True, exist_ok=True)
def fetch(project):
    dest = ROOT / project
    url = 'https://mirrors.tuna.tsinghua.edu.cn/git/AOSP/platform/' + project
    if dest.exists():
        return {'project': project, 'status': 'preexisting-not-modified', 'path': str(dest)}
    dest.parent.mkdir(parents=True, exist_ok=True)
    args = ['git', 'clone', '--depth', '1', '--single-branch', '--branch', TAG, url, str(dest)]
    p = subprocess.run(args, capture_output=True, text=True)
    result = {'project': project, 'path': str(dest), 'tag': TAG, 'url': url, 'exit_code': p.returncode}
    if p.returncode:
        result['error'] = p.stderr[-2000:]
    else:
        result['commit'] = subprocess.check_output(['git', '-C', str(dest), 'rev-parse', 'HEAD'], text=True).strip()
    return result
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    for result in executor.map(fetch, PROJECTS):
        print(json.dumps(result), flush=True)
