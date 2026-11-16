#!/usr/bin/env python3
"""score_gms.py <tag> [--apps]  -- what the apps of a round got from the shared Play services process.

Every Play services API an app's client library opens goes through Play services' service broker:
IGmsServiceBroker.getService (code 46), with the API's service id, answered with the API's binder or an exception.
The binder trace in each app's stderr (WESTLAKE_PLAY_TRACE, "[WL-PLAY-TRACE] out <descriptor> code=<n>
[service=<id>] <reply>", $WL_SC/inputs/logs/<tag>/hk-<package>.stderr) has each such call and the first int of its
reply, the exception code (0: answered). Per service id, by its name in Play services' own numbering
(gms-service-ids.json), this prints how many apps asked and how many were answered, and the codes the others got.
Then per Play services interface the apps called directly (the advertising id, Phenotype, Clearcut and the rest),
as score_store.py reads the Play Store's: the apps whose two-way calls were answered, and the apps whose one-way
calls were followed by a call back on an interface of the same package.
With PLAY_DIR (the round's Play services directory), it also counts the apps with an FCM registration, from the
token counts the round recorded (play-tokens.log: counts only, no token leaves the board).
Only counts, service names and package names are printed. LIST=<file> limits it to those packages."""

import collections
import json
import os
import re
import sys
from pathlib import Path

TRACE = re.compile(r'\[WL-PLAY-TRACE\] (out|in) (\S+) code=(\d+)(?: service=(\d+))? (\S*)')
BROKER = 'com.google.android.gms.common.internal.IGmsServiceBroker'
GET_SERVICE = '46'
# The broker answers a getService by a call back: IGmsCallbacks.onPostInitComplete (1) or
# onPostInitCompleteWithConnectionInfo (3), whose first argument is a ConnectionResult code. The trace gives it as
# status=<code>, with the service the app last asked for (afterService=<id>).
CALLBACK = re.compile(r'\[WL-PLAY-TRACE\] in com\.google\.android\.gms\.common\.internal\.IGmsCallbacks code=[13] '
                      r'status=(-?\d+) afterService=(-?\d+)')
CONNECTION_RESULTS = {
    0: 'SUCCESS', 1: 'SERVICE_MISSING', 2: 'SERVICE_VERSION_UPDATE_REQUIRED', 3: 'SERVICE_DISABLED',
    4: 'SIGN_IN_REQUIRED', 5: 'INVALID_ACCOUNT', 6: 'RESOLUTION_REQUIRED', 7: 'NETWORK_ERROR', 8: 'INTERNAL_ERROR',
    9: 'SERVICE_INVALID', 10: 'DEVELOPER_ERROR', 11: 'LICENSE_CHECK_FAILED', 13: 'CANCELED', 14: 'TIMEOUT',
    15: 'INTERRUPTED', 16: 'API_UNAVAILABLE', 17: 'SIGN_IN_FAILED', 18: 'SERVICE_UPDATING',
    19: 'SERVICE_MISSING_PERMISSION', 20: 'RESTRICTED_PROFILE', 22: 'RESOLUTION_ACTIVITY_NOT_FOUND',
    23: 'API_DISABLED', 24: 'API_DISABLED_FOR_CONNECTION'}
# Play services' interfaces; the Play Store's are score_store.py's.
GMS = ('com.google.android.gms.', 'com.google.android.c2dm.', 'com.google.firebase.')
INTERFACE_TRANSACTION = '1598968902'
SERVICE_IDS = Path(__file__).with_name('gms-service-ids.json')


def service_names(path=SERVICE_IDS):
    """Service id -> name, from Play services' numbering (gms-service-ids.json)."""
    try:
        return {int(k): v['name'] for k, v in json.loads(Path(path).read_text())['ids'].items()}
    except (OSError, ValueError, KeyError):
        return {}


def apps_of(logs, only=None):
    for path in sorted(Path(logs).glob('hk-*.stderr')):
        app = path.name[len('hk-'):-len('.stderr')]
        if only is None or app in only:
            yield app, path


def broker(logs, only=None):
    """Per service id: the apps that asked for it, those answered, and those refused (by the reply's first int)."""
    asked = collections.defaultdict(set)
    answered = collections.defaultdict(set)
    refused = collections.defaultdict(lambda: collections.defaultdict(set))
    for app, path in apps_of(logs, only):
        for line in path.read_text(errors='replace').splitlines():
            if '[WL-PLAY-TRACE] out ' + BROKER not in line:
                continue
            m = TRACE.search(line)
            if not m or m.group(3) != GET_SERVICE or m.group(4) is None:
                continue
            service, reply = int(m.group(4)), m.group(5)
            asked[service].add(app)
            if reply == '0':
                answered[service].add(app)
            else:
                refused[service][reply or 'none'].add(app)
    return asked, answered, refused


def connections(logs, only=None):
    """Per service id: the apps whose connection was called back, by ConnectionResult code (0: connected)."""
    results = collections.defaultdict(lambda: collections.defaultdict(set))
    for app, path in apps_of(logs, only):
        for line in path.read_text(errors='replace').splitlines():
            if 'IGmsCallbacks' not in line:
                continue
            m = CALLBACK.search(line)
            if m and int(m.group(2)) >= 0:
                results[int(m.group(2))][int(m.group(1))].add(app)
    return results


def interfaces(logs, only=None):
    """Per Play services interface other than the broker: the apps that called it, those whose two-way calls were
    answered (reply 0) or failed (by code), and those whose one-way calls (or empty replies) got a call back on an
    interface of the same package."""
    calls = collections.defaultdict(set)
    replied = collections.defaultdict(set)
    failed = collections.defaultdict(lambda: collections.defaultdict(set))
    oneway = collections.defaultdict(set)
    called_back = collections.defaultdict(set)
    for app, path in apps_of(logs, only):
        sent, back = set(), set()
        for line in path.read_text(errors='replace').splitlines():
            if '[WL-PLAY-TRACE]' not in line:
                continue
            m = TRACE.search(line)
            if not m:
                continue
            way, descriptor, code, _, reply = m.groups()
            if way == 'in':
                if code != INTERFACE_TRANSACTION:
                    back.add(descriptor.rpartition('.')[0])
                continue
            if not descriptor.startswith(GMS) or descriptor == BROKER:
                continue
            calls[descriptor].add(app)
            if reply in ('oneway', 'empty'):
                oneway[descriptor].add(app)
                sent.add(descriptor)
            elif reply == '0':
                replied[descriptor].add(app)
            else:
                failed[descriptor][reply].add(app)
        for descriptor in sent:
            if descriptor.rpartition('.')[0] in back:
                called_back[descriptor].add(app)
    return calls, replied, failed, oneway, called_back


def push(play_dir, only=None):
    """The apps with an FCM token file and those with at least one registration, from the last count the round
    recorded per app (play-tokens.log lines "T <package> <registrations> <messengers>")."""
    last = {}
    path = Path(play_dir) / 'play-tokens.log'
    if not path.exists():
        return None
    for line in path.read_text(errors='replace').splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == 'T' and parts[2].isdigit():
            if only is None or parts[1] in only:
                last[parts[1]] = int(parts[2])
    return set(last), {app for app, count in last.items() if count > 0}


def main():
    tag = sys.argv[1]
    show_apps = '--apps' in sys.argv[2:]
    logs = Path(os.environ['WL_SC']) / 'inputs/logs' / tag
    only = None
    if os.environ.get('LIST'):
        only = {x.strip() for x in open(os.environ['LIST']) if x.strip()}
    listed = (lambda apps: f'  {" ".join(sorted(apps))}') if show_apps else (lambda apps: '')
    names = service_names()
    asked, answered, refused = broker(logs, only)
    results = connections(logs, only)
    if asked:
        print("Play services' service broker (getService), by service: the apps that asked, those whose request was "
              "taken (no exception), and the connection result Play services called back with")
    for service in sorted(asked, key=lambda s: (-len(asked[s]), s)):
        connected = results[service].get(0, set())
        print(f'  {names.get(service, "service")} ({service}): {len(asked[service])} apps; '
              f'{len(answered[service])} taken, {len(connected)} connected' + listed(asked[service] - connected))
        for code, apps in sorted(refused[service].items(), key=lambda kv: -len(kv[1])):
            print(f'    reply {code}: {len(apps)}' + listed(apps))
        for status, apps in sorted(results[service].items(), key=lambda kv: -len(kv[1])):
            if status != 0:
                print(f'    {CONNECTION_RESULTS.get(status, "status")} ({status}): {len(apps)}' + listed(apps))
    calls, replied, failed, oneway, called_back = interfaces(logs, only)
    if calls:
        print('Play services interfaces in the binder trace:')
    for descriptor in sorted(calls, key=lambda d: -len(calls[d])):
        said = []
        if replied[descriptor] or failed[descriptor]:
            said.append(f'{len(replied[descriptor])} answered')
        if oneway[descriptor]:
            said.append(f'{len(oneway[descriptor])} one-way, {len(called_back[descriptor])} called back')
        print(f'  {descriptor}: {len(calls[descriptor])} apps; ' + ', '.join(said))
        for code, apps in sorted(failed[descriptor].items(), key=lambda kv: -len(kv[1])):
            print(f'    reply {code}: {len(apps)}' + listed(apps))
    if os.environ.get('PLAY_DIR'):
        counted = push(os.environ['PLAY_DIR'], only)
        if counted is not None:
            files, registered = counted
            print(f'Push (FCM): {len(registered)} apps registered, of {len(files)} with a token file'
                  + listed(files - registered))


if __name__ == '__main__':
    main()
