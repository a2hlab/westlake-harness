#!/usr/bin/env python3
"""Seal public card paths and Rust selector; excludes private material and bytecode."""
import json
from pathlib import Path
from inspect_inputs import sha,save
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[2]
def main():
    paths={p for p in HERE.rglob('*') if p.is_file() and '.private' not in p.parts and '__pycache__' not in p.parts and p.name!='manifest.json'}
    paths.add(REPO/'tools/spec-checks/tests/commercial_game_gles_transaction_package.rs');paths.add(HERE/'landing-paths.txt')
    names=sorted(str(p.relative_to(REPO)) for p in paths|{HERE/'manifest.json'})
    (HERE/'landing-paths.txt').write_text('\n'.join(names)+'\n')
    save(HERE/'manifest.json',{'schema':'g20-public-handoff/v1','files':{str(p.relative_to(REPO)):sha(p) for p in sorted(paths)},'excludes':['.private/**','**/__pycache__/**'],'self_hash':'reported outside this file','execution_enabled':False})
    print(json.dumps({'paths':len(names),'manifest_sha256':sha(HERE/'manifest.json'),'landing_paths_sha256':sha(HERE/'landing-paths.txt')}))
if __name__=='__main__':main()
