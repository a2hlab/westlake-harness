"""T123 final-image review gate. Local files only; no board or process-control API."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import os
import time
import uuid


def publish_once(path, value):
    """Complete bytes become visible atomically; an existing receipt is never replaced."""
    path = Path(path)
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex)
    try:
        with temporary.open('x') as stream:
            json.dump(value, stream, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        # link is atomic create-if-absent (unlike replace, it cannot overwrite).
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def validate_review(review, expected, clock, observed):
    if not isinstance(review, dict):
        raise ValueError('review must be an object')
    elapsed = observed - clock['monotonic']
    if not 0 <= elapsed < 120:
        raise ValueError('original review deadline expired')
    for field in ('run_id', 'serial', 'boot', 'image_sha256'):
        if review.get(field) != expected[field]:
            raise ValueError('mismatched ' + field)
    if 'initial_image_sha256' in review and review['initial_image_sha256'] != expected['image_sha256']:
        raise ValueError('conflicting image SHA alias')
    if review.get('image') != expected['image']:
        raise ValueError('mismatched image filename')
    if review.get('verdict') not in ('desktop', 'host_white', 'usable_toutiao', 'credential', 'unknown'):
        raise ValueError('invalid verdict')
    if not isinstance(review.get('reviewer'), str) or not review['reviewer'].strip():
        raise ValueError('missing reviewer')
    written = datetime.fromisoformat(review['timestamp'])
    started = datetime.fromisoformat(clock['wallclock'])
    if written.utcoffset() is None or started.utcoffset() is None:
        raise ValueError('timezone required')
    written_elapsed = (written - started).total_seconds()
    if not 0 <= written_elapsed <= elapsed or written_elapsed >= 120:
        raise ValueError('timestamp outside original review window')
    # Author-supplied elapsed is documentary, never the timeout authority.
    return review['verdict']


def wait_for_review(run, expected, clock, now=time.monotonic, sleep=time.sleep):
    run = Path(run)
    deadline = clock['monotonic'] + 120
    last_error = 'absent'
    while now() < deadline:
        if (run / 'cleanup-now').exists():
            return {'decision': 'cleanup', 'reason': 'explicit cleanup'}
        try:
            review = json.loads((run / 'outer-review.json').read_text())
            bound = expected() if callable(expected) else expected
            observed = now()
            verdict = validate_review(review, bound, clock, observed)
            image = run / bound['image']
            if hashlib.sha256(image.read_bytes()).hexdigest() != bound['image_sha256']:
                raise ValueError('image bytes changed')
            accepted = verdict in ('desktop', 'host_white')
            result = {'decision': 'continue' if accepted else 'cleanup', 'verdict': verdict,
                      'review': review, 'observed_monotonic': observed,
                      'elapsed': observed - clock['monotonic'],
                      'deadlines': {k: clock['monotonic'] + seconds for k, seconds in
                                    [('review',120),('click',180),('active',360),('total',480)]}}
            publish_once(run / 'review-consumed.json', result)
            return result
        except (FileNotFoundError, json.JSONDecodeError, ValueError, KeyError, TypeError, OSError) as error:
            # Existing consumption is not reusable authorization.
            if isinstance(error, FileExistsError):
                raise
            last_error = str(error)
        sleep(max(0, min(.25, deadline - now())))
    return {'decision': 'cleanup', 'reason': 'original review deadline', 'last_error': last_error}


def reviewed_tail(run, expected, clock, continuation, cleanup,
                  now=time.monotonic, sleep=time.sleep):
    """Component-test harness; production candidate owns its own single finally."""
    try:
        decision = wait_for_review(run, expected, clock, now, sleep)
        if decision['decision'] == 'continue':
            if now() >= decision['deadlines']['active']:
                raise TimeoutError('original active deadline expired')
            continuation(decision)
        return decision
    finally:
        cleanup()
