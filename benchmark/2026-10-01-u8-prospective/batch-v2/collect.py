"""Collect batch-list evidence without building, deploying or restoring inputs."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def git(tree, *args):
    return subprocess.check_output(['git', '-C', str(tree), *args])


def collect(searches):
    workspaces = Path(os.environ.get('WORKSPACES', ROOT.parent))
    prefix = 'benchmark/2026-10-01-u7-death-clusters/'
    cluster_bytes = git(ROOT, 'show', '0944217a4:' + prefix + 'clusters.json')
    original = json.loads(cluster_bytes)
    prior = json.loads(git(ROOT, 'show', '0944217a4:' + prefix + 'evidence/sources.json'))
    sources = prior['sources']
    for source in sources.values():
        tree = workspaces / prior['repositories'][source['repository']]['path']
        payload = git(tree, 'show', source['commit'] + ':' + source['path'])
        if sha(payload) != source['sha256']:
            raise ValueError('source mismatch: ' + source['id'])
        source['excerpt'] = source['excerpt'][:14]
    additions = [
        ('bridge-loaded-object-idiom', 'real-work', 'tools/task70-critfix/wl_critfix.c', [(96,110),(130,142),(161,165),(731,739)],
         'cc-t3 33feb0ac8 reports prior DAYU600 verification of this idiom; not a verified bridge repair, and first basename match cannot select between two existing copies.'),
        ('bridge-namespace-idiom', '00.Workspace', 'code/games/02.unity.cardwords/adapter/framework/app-native-loader/src/app_native_loader.c', [(233,250),(276,284)],
         'Existing named-namespace loading/sharing implementation; actual JNI owner namespace and duplicate runtime still require identification.'),
        ('theme-probe-reference', '00.Workspace', 'code/adapter/westlake-piercing/test-fixtures/dayu600-apk-probe/Dayu600ApkStageProbe.java', [(2003,2017),(9111,9133)],
         'Probe-only app theme and shared app/framework asset context; not a verified fd-api or VLC production repair. Do not copy fixed probe resource IDs.'),
        ('mediandk-error-stub', 'real-work', 'archive/scripts-history/task68-gles/mediandk_stub.c', [(1,18),(29,34)],
         'Explicit non-implementation with null/error media returns. Rejected as a real media API donor.'),
    ]
    for identifier, repository, path, ranges, note in additions:
        tree = workspaces / prior['repositories'][repository]['path']
        commit = searches['repositories'][repository]['commit']
        payload = git(tree, 'show', commit + ':' + path)
        lines = payload.decode().splitlines()
        sources[identifier] = dict(id=identifier, repository=repository, path=path, commit=commit,
                                  last_change_commit=git(tree,'log','-1','--format=%H',commit,'--',path).decode().strip(),
                                  sha256=sha(payload), note=note, status='source-verified-applicability-conditional',
                                  excerpt=[dict(line=index+1,text=line) for index,line in enumerate(lines)
                                           if any(start<=index+1<=end for start,end in ranges)])
    board = (workspaces / 'westlake-harness/.octos/boards/app-lighting.md').read_text(errors='replace').splitlines()
    quotes = []
    for stamp in ['08:21:00','08:23:13','08:25:38','08:27:45','08:28:40']:
        index = next(index for index,line in enumerate(board) if line.startswith(('ACK(', 'PROGRESS(')) and 'T'+stamp in line)
        end = next((end for end in range(index+1,len(board)) if board[end].startswith(('ACK(', 'PROGRESS(', 'LOCK(', 'UNLOCK('))),len(board))
        quote = '\n'.join(board[index:end]).rstrip()
        if '\ufffd' in quote:
            raise ValueError('invalid authority quote')
        quotes.append(dict(board_line=index+1,timestamp=stamp,text=quote,sha256=sha(quote.encode())))
    inputs = []
    for key in ['fd-seal','toutiao']:
        folder = Path.home() / 'a2hlab/app-inputs' / key
        active = sorted((folder/'lib/arm64-v8a').glob('*.so'))
        isolated = sorted(folder.with_name(key+'-quarantine').glob('*.so'))
        inputs.append(dict(key=key,root='HOME/a2hlab/app-inputs',active_count=len(active),
                           metadata_sha256=sha((folder/'app-input.json').read_bytes()),
                           quarantine=[dict(name=path.name,sha256=sha(path.read_bytes()),bytes=path.stat().st_size) for path in isolated],
                           restored_by_this_lane=False,post_restore_resolve=None))
    marker_path = 'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'
    marker_commit = git(ROOT,'rev-parse','597c827b5').decode().strip()
    marker = git(ROOT,'show',marker_commit+':'+marker_path)
    package = workspaces/'westlake-generation-n8-private-zlib/package.json'
    package_sha = sha(package.read_bytes())
    if package_sha != '3dd48299b599c2adebe8cc574649a31d84fabae53b77d5a7df704f4f380b993e':
        raise ValueError('N8 package changed')
    clusters = [dict(id=cluster['id'],wall=cluster['wall'],layer=cluster['layer'],source_ids=cluster['source_ids'],
                     apps=[{field:app[field] for field in ['key','visual','evidence','hilog_sha256','terminal_status','root_status']} for app in cluster['apps']])
                for cluster in original['clusters']]
    return dict(schema_version=1,status='unfrozen-batch-intake',clusters_commit=git(ROOT,'rev-parse','0944217a4').decode().strip(),
                clusters_sha256=sha(cluster_bytes),clusters=clusters,sources=sources,searches=searches,authority=quotes,
                remote_search='a2hlab/hw248 not searched in this offline local batch-list pass; none is bounded, not global absence',
                bridge_candidate=dict(commit=git(ROOT,'rev-parse','33feb0ac8').decode().strip(),
                                      path='benchmark/2026-09-30-u4-sweep/COMPOSE-WALL.md',line=1042,status='diff-only-not-built'),
                n8=dict(manifest_sha256=package_sha,path='WORKSPACES/westlake-generation-n8-private-zlib/package.json',
                        native_only=True,old_embedded_jar_must_not_ship=True),
                payload=dict(commit=marker_commit,path=marker_path,sha256=sha(marker),tests_commit=git(ROOT,'rev-parse','a62f48ed1').decode().strip(),
                             status='source-and-tests-only-not-restored',inputs=inputs))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--searches', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(collect(json.loads(args.searches.read_text())),ensure_ascii=False,sort_keys=True,indent=2))
