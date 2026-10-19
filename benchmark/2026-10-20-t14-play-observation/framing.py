"""HDC merged stdout/stderr byte framing. No device execution."""
import re
import shlex


def script(path, offset, size, token, scratch, guard):
    if not (type(offset) is int and offset >= 0 and type(size) is int and 0 <= size <= 65536):
        raise ValueError('bounded byte range')
    if not re.fullmatch('[0-9a-f]{32}', token) or not guard.strip():
        raise ValueError('token/guard')
    p, err = shlex.quote(path), shlex.quote(scratch)
    return (f'(set -eu; {guard}; printf "T14_BEGIN_{token}:{size}\\n"; '
            f'set +e; dd if={p} bs=1 skip={offset} count={size} 2>{err}; rc=$?; set -e; '
            f'printf "\\nT14_END_{token}:%s\\n" "$rc"; cat {err}; '
            f'{guard}; printf "\\nT14_POST_{token}\\n")')


def decode(raw, size, token, host_rc, timeout=False):
    start = f'T14_BEGIN_{token}:{size}\n'.encode()
    end = f'\nT14_END_{token}:0\n'.encode()
    post = f'\nT14_POST_{token}\n'.encode()
    ok = (not timeout and host_rc == 0 and raw.startswith(start)
          and raw[len(start)+size:].startswith(end) and raw.endswith(post))
    return {'status': 'BOUNDED_BYTES_COMPLETE' if ok else 'PARTIAL_UNVERIFIED',
            'payload': raw[len(start):len(start)+size] if raw.startswith(start) else b'',
            'whole_window': False, 'player_verdict': 'unknown'}
