"""Offline only. Validate payload identity; never emit log text."""
import argparse
import hashlib
import json
from pathlib import Path

KEYS = ('dev', 'inode', 'size', 'mtime', 'ctime')
LIMIT = 512 * 1024
PREFIX = 131072

def sha(data):
    return hashlib.sha256(data).hexdigest()

def verify(old_pre, old_post, pre, post, old_prefix, payload):
    snapshots = (old_pre, old_post, pre, post)
    if any(not isinstance(s, dict) or any(type(s.get(k)) is not int for k in KEYS) for s in snapshots):
        return {'status': 'unknown', 'reason': 'identity_field_missing_or_invalid'}
    if any(s[k] != old_pre[k] for s in snapshots for k in KEYS):
        return {'status': 'identity_mismatch', 'reason': 'stat_changed'}
    if not PREFIX <= pre['size'] <= LIMIT or len(payload) != pre['size'] or len(old_prefix) != PREFIX:
        return {'status': 'unknown', 'reason': 'size_or_capture_invalid'}
    if payload[:PREFIX] != old_prefix:
        return {'status': 'identity_mismatch', 'reason': 'prefix_changed'}
    return {'status': 'bound', 'bytes': len(payload), 'sha256': sha(payload), 'prefix_sha256': sha(old_prefix), 'prefix_match': True}

def check(raw):
    collection = json.loads((raw / 'collection.json').read_text())
    result = {'scope': 'ordinary_log_file_identity_only', 'collection_status': collection['status'], 'collection_error': collection.get('error'), 'files': []}
    for row in collection['files']:
        item = {'pid': row['pid'], 'path': row['path'], 'old_raw_sha256': row['old_raw_sha256'], 'old_prefix_sha256': row['old_prefix_sha256'], 'status': 'unknown'}
        pid = str(row['pid'])
        required = [raw / (pid + '-' + name + '.receipt.json') for name in ('pre', 'payload', 'post')]
        if all(p.exists() and json.loads(p.read_text())['rc'] == 0 for p in required):
            item.update(verify(row['old_pre'], row['old_post'], row.get('pre'), row.get('post'), (raw / ('old-' + pid + '.prefix')).read_bytes(), (raw / (pid + '-payload.stdout')).read_bytes()))
        else:
            item['reason'] = 'complete_successful_capture_unavailable'
            if row['status'] == 'identity_mismatch': item['status'] = 'identity_mismatch'
        result['files'].append(item)
    result['interpretation'] = 'No diagnosis or repair claim; current boot is not historical file birth boot.'
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('raw', type=Path)
    args = parser.parse_args()
    print(json.dumps(check(args.raw), indent=2))
