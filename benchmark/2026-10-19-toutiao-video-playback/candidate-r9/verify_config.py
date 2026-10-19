"""Offline exact configuration and reused-artifact check; never accesses a board."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    old = BASE / 'candidate-r3/deploy-inputs/run.sh'
    new = HERE / 'run.sh'
    assert sha(old) == '79275cf9f9a72be72beb551b978ee5f2faaed84129980aa5c79d2f51acd040d5'
    assert sha(new) == 'b5625757fcd812a64106a43897525b685216c7f61af5e9312969998c9485ee8a'
    before, after = old.read_text().splitlines(), new.read_text().splitlines()
    assert len(before) == len(after)
    differences = [(a, b) for a, b in zip(before, after) if a != b]
    assert len(differences) == 2
    assert differences[0] == ('export WESTLAKE_ANDROID_NATIVE_NET_TARGETS=libsscronet.so',
                               'export WESTLAKE_ANDROID_NATIVE_NET_TARGETS=libsscronet.so:libmffmpeg.so')
    assert differences[1][0].startswith('export WESTLAKE_ANDROID_NATIVE_INHERIT=')
    assert differences[1][1] == differences[1][0] + ':libandroid_native_network_compat.so'
    pins = {
        'candidate-r3/deploy-inputs/libmffmpeg.so': 'd2882303bf5dc34e297a404e4b57a214d9c30ddaf0f496eb2ef9f7dcac09c4b4',
        'candidate-r8/deploy-inputs/libttmplayer.so': '0b4d95c5f9d96826a95ede998df20be037299eaf6fbfcd1cd2afa39793ba9471',
        'candidate-r8/deploy-inputs/libopensles_android_compat.so': '6e83e924aae709f0c90ba2a966910febb63471b7a9a6294c6dee585a73ff3b4b',
    }
    for name, digest in pins.items():
        assert sha(BASE / name) == digest, name
    print(json.dumps({'configuration': 'exact two-line delta', 'reused_binaries': len(pins),
                      'device_calls': 0, 'actual_network_bindings': 'NOT_CHECKED',
                      'playback': 'NOT_PASSED'}))

if __name__ == '__main__':
    main()
