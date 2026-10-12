#!/usr/bin/env python3
"""Print a disabled recovery/rollback recipe; there is deliberately no executor."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re


def validate_authorization(context, approval, now):
    fields = ('serial', 'boot_id', 'base_plan_sha256', 'new_plan_sha256', 'candidate_sha256')
    for field in fields:
        if not context.get(field) or approval.get(field) != context[field]:
            raise ValueError('authorization identity mismatch: ' + field)
    for field in ('base_plan_sha256', 'new_plan_sha256', 'candidate_sha256'):
        if not re.fullmatch('[a-f0-9]{64}', context[field]):
            raise ValueError('unpinned identity: ' + field)
    issued = datetime.fromisoformat(approval['issued_at'])
    expires = datetime.fromisoformat(approval['expires_at'])
    if issued.tzinfo is None or expires.tzinfo is None or not issued <= now < expires:
        raise ValueError('authorization expired/not yet valid')
    if approval.get('approved_by') != 'outer(codex)' or approval.get('scope') != 'reviewed-route-b-only':
        raise ValueError('wrong authority/scope')
    if approval.get('data_preserving') is not True or approval.get('automatic_consent') is not False:
        raise ValueError('data/consent boundary mismatch')


def preview(context, approval=None, now=None, action='preview'):
    if action != 'preview':
        raise ValueError('execution disabled: new outer window and reviewed executor required')
    if approval is not None:
        validate_authorization(context, approval, now or datetime.now(timezone.utc))
    return {'execution_enabled': False, 'board_commands_executed': 0,
            'authorization': 'checked for preview only' if approval else 'pending',
            'context': context,
            'steps': [
                {'phase': 'preflight', 'operation': 'future read-only serial/boot/lock, guardian identity, stop hash, data manifest and parent scope capture',
                 'criterion': 'fresh exact identities; captured old PID is not live ownership; no valid foreign lock takeover'},
                {'phase': 'backup', 'operation': 'future archive exact control script bytes plus immutable/reconcile/placement metadata to NEW attempt, never move app data',
                 'criterion': 'two deployed aliases and readback hashes independently pinned; preserve original evidence and stop'},
                {'phase': 'change', 'operation': 'future replace only reviewed Route B watchdog aliases and explicitly approved dependencies',
                 'criterion': 'candidate SHA+behavior review, new placement/plan/authorization; no overlay restart, no installer, no labels/permissions/system spawner'},
                {'phase': 'arm', 'operation': 'pending t1 interface and separate explicit operator-stop policy; no concrete start command issued',
                 'criterion': 'stop not automatically cleared; reuse/current Route B child policy independently reviewed; no automatic privacy or login touch'},
                {'phase': 'verify', 'operation': 'future human desktop click; observe PID/birth, snapshot degraded state, user refresh and article',
                 'criterion': 'no-mac-repair/reboot validity requires NEW plan and autonomy proof if control bytes changed; screenshots outer only'},
                {'phase': 'rollback', 'operation': 'future identify candidate guardian by boot/PID/birth/UID/exe/script and stop it only under separately reviewed ownership guard; restore backed-up control bytes/metadata',
                 'criterion': 'no root U13/foreign signal, retain stop and user data; old unsafe watchdog not automatically restarted; revalidate on identity drift'},
            ], 'pending': ['actual t1 candidate interface and behavior receipts', 'fresh owner/stop decision',
                           'new plan/placement/authorization', 'signed autonomy/UI/refresh/article proof'],
            'ui_signed': False, 'seal_signed': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--context', type=Path, default=Path(__file__).with_name('context.json'))
    parser.add_argument('--authorization', type=Path)
    parser.add_argument('--action', choices=('preview', 'execute'), default='preview')
    args = parser.parse_args()
    try:
        result = preview(json.loads(args.context.read_text()),
                         json.loads(args.authorization.read_text()) if args.authorization else None,
                         action=args.action)
        print(json.dumps(result, indent=2))
    except (ValueError, KeyError, OSError) as error:
        print(json.dumps({'execution_enabled': False, 'board_commands_executed': 0, 'rejected': str(error)}))
        raise SystemExit(2)


if __name__ == '__main__':
    main()
