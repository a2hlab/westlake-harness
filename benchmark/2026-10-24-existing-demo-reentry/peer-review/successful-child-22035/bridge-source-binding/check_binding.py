"""Read-only replay of archived source/object/link identities; no build or device call."""
import argparse, hashlib, json, tarfile
from pathlib import Path

S = '1844e81ba3183430040717e3fca7bffadf0d9a9724e55a543da1480aaf667a5e'
O = 'f91b354ffa408fed7ff3002e1ed24a786b65621fd9b985c37db9b0fab461b8ed'
A = '5db328cf263ba1575401d096b5afe3f5cecb3298066b14811a85a3d6570e223b'
B = 'b0e5602a97133ebb1dca12972a8931a86528322685a211bb1a7a0a2185fefbd4'
L = 'e960b1d1c12776cf6deceac1792abb0a60f3fb43d1de74eb935b88bd14d619cb'
SRC = 'westlake-ability38/framework/window/jni/oh_window_manager_client.cpp'
OBJ = 'out-ability38/native-policy/oh_window_manager_client.o'

def require(ok, message):
    if not ok:
        raise ValueError(message)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--main', required=True, type=Path)
    p.add_argument('--t4', required=True, type=Path)
    a = p.parse_args()
    archive = a.t4 / 'benchmark/2026-10-20-t18-build-evidence/source-closure/.private/archive-02/window.tar.gz'
    with tarfile.open(archive) as t:
        def get(name):
            key = 'ORB_WS/' + name
            require(t.getnames().count(key) == 1, 'duplicate/missing archive member: ' + key)
            return t.extractfile(key).read()
        art_bytes = get('out-ability38/native-policy/artifacts.json')
        require(sha(art_bytes) == A, 'original artifacts SHA drift')
        art = json.loads(art_bytes)
        require(sha(get(SRC)) == S == art['source_sha256'], 'source mismatch')
        require(sha(get(OBJ)) == O, 'archived object mismatch')
        compile_rows = [c for c in art['commands'] if c['label'] == 'compile-window-manager']
        require(len(compile_rows) == 1 and compile_rows[0]['rc'] == 0, 'compile receipt')
        cmd = compile_rows[0]['command']
        require(cmd[cmd.index('-c')+1].endswith('/'+SRC), 'compile source argv')
        require(cmd[cmd.index('-o')+1].endswith('/'+OBJ), 'compile output argv')
        rows = [(k,v) for k,v in art['reused_objects'].items() if k.endswith('/'+OBJ)]
        require(len(rows) == 1 and rows[0][1] == O, 'producer object index')
    snapshot = a.main / 'sources/api-implementations/bridge-d4fa-source-snapshot/ability38/framework/window/jni/oh_window_manager_client.cpp'
    require(sha(snapshot.read_bytes()) == S, 'tracked snapshot mismatch')
    run = a.t4 / 'benchmark/2026-10-20-t29-window-observation/.private/production-01'
    argv_bytes = (run/'raw/13-bridge-candidate.argv.json').read_bytes()
    require(sha(argv_bytes) == L, 'T29 original argv mismatch')
    argv = json.loads(argv_bytes)
    require(len([x for x in argv if x.endswith('/'+OBJ)]) == 1, 'object missing/duplicated in T29 link')
    require((run/'raw/13-bridge-candidate.rc').read_text().strip() == '0', 'T29 link failed')
    receipt_path = a.main/'benchmark/2026-10-20-t29-window-observation/production-01/receipt.public.json'
    receipt = json.loads(receipt_path.read_text())
    require(receipt['inputs']['$BRIDGE_INPUTS/'+OBJ]['sha256'] == O, 'T29 input pin')
    require(receipt['outputs']['bridge.so']['sha256'] == B == sha((run/'bridge.so').read_bytes()), 'T29 ELF output')
    require(any(c['name'] == '13-bridge-candidate' and c['rc'] == 0 for c in receipt['commands']), 'public link rc')
    print(json.dumps({'status':'ARCHIVED_SOURCE_OBJECT_T29_LINK_CHAIN_VERIFIED', 'source_sha256':S, 'object_sha256':O, 'original_artifacts_sha256':A, 't29_original_link_argv_sha256':L, 'bridge_sha256':B, 'compile_rc':0, 'link_rc':0, 'runtime_actions':0, 'limits':['Original archived records and bytes verified, not a rebuild.', 'Does not prove current session53 parent or diagnose white screen.']},indent=2))

if __name__ == '__main__':
    main()
