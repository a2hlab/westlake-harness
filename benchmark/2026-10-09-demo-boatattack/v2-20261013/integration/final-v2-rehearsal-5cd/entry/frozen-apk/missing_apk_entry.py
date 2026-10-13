"""Missing-only derivative of t3 batch_adapter.install_one (main 3d81116a1c).

Same module API and BMS executor. No cold_stop, uninstall or replacement flag.
Both the provider and this entry confirm absence before the first write.
"""
import shlex
import time

b = None  # Set by the adapter to its independently SHA-pinned BMS module.
ABSENT = 'error: failed to get information and the parameters may be wrong.'


def install_one(board, app, root, out, remote):
    out.mkdir(parents=True)
    result = {'key': app['key'], 'package': app['package'], 'serial': board.serial,
              'status': 'started', 'screenshots': [], 'install_only': True}
    try:
        resolved = b.resolve_input(root, app)
        result.update({k: v for k, v in resolved.items() if k != 'apk'})
        rc, dump = board.shell('bm dump -n ' + shlex.quote(app['package']), required=False)
        if rc != 0 or dump.strip().lower() != ABSENT:
            raise b.AppFailure('package absence not reconfirmed; no stop or replacement allowed')
        board.shell('mkdir -p ' + shlex.quote(remote))
        apk = remote + '/original.apk'
        board.send(resolved['apk'], apk)
        _, text = board.shell('sha256sum ' + shlex.quote(apk))
        if not text.split() or text.split()[0] != resolved['apk_sha256']:
            raise b.AppFailure('staged APK SHA mismatch')
        # Deliberately no -r: concurrent creation must fail, never replace.
        rc, text = board.shell('bm install -p ' + shlex.quote(apk), required=False, timeout=180)
        (out / 'install.txt').write_text(text)
        result['install'] = {'return_code': rc, 'success_text': b.bm_success(rc, text, 'install')}
        if rc or not result['install']['success_text']:
            raise b.AppFailure('install failed: ' + text.strip())
        rc, text = board.shell('bm dump -n ' + shlex.quote(app['package']), required=False)
        (out / 'bundle.txt').write_text(text)
        result['bms'] = b.parse_bundle(text, app['package'])
        if rc or not result['bms']['queryable']:
            raise b.AppFailure('BMS readback failed')
        result['status'] = 'installed'
    except b.BatchStop:
        result['status'] = 'batch_interrupted'
        raise
    except (b.AppFailure, OSError, ValueError, KeyError) as e:
        result.update(status='app_failed', error=str(e))
    finally:
        result['finished_at'] = time.time()
        b.save(out / 'record.json', result)
    return result
