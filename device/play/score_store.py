#!/usr/bin/env python3
"""score_store.py <tag> [--apps]  -- what Google Play's client libraries got from the Play Store host in a round.

Play Core (asset delivery, split install, in-app updates and review) and Play Integrity log each call to a Play
Store service and each callback, as "PID: [<pid>] <Service> : <message>", in the app's hilog. The harness captures
that per app ($WL_SC/inputs/logs/<tag>/hk-<package>.hilog). Per service this prints:
- how many apps called it, and how many got a callback ("on..."), by callback;
- how many started binding the service and never connected to it ("Initiate binding to the service" and no
  "linkToDeath" after it): the Play Store host never answered the bind;
- the error codes they got (onError(<code>), or "<call> failed: <code>");
- with --apps, the apps per callback and error.
Not every client library logs there: the Engage SDK and Play Core's prewarm log no callback. So it also reads the
binder trace in each app's stderr (WESTLAKE_PLAY_TRACE, "[WL-PLAY-TRACE] out <descriptor> code=<n> <reply>"), per
Play Store interface: the apps whose two-way calls got a reply without an exception (or with one, by code), and the
apps whose one-way calls (or two-way calls the store answered with an empty reply) were followed by a call back on
an interface of the same package (its callback).
Only counts, callback names and package names are printed: requests carry nonces and tokens, which never leave
the logs. LIST=<file> limits it to those packages."""
import collections
import os
import re
import sys
from pathlib import Path

LINE = re.compile(r'PID: \[\d+\]\s+(\w+)\s*:\s*(.*)$')
# Play Core logs a callback under its own class (OnRequestInstallCallback for in-app updates): each logged name
# goes to the service family it serves, first match winning; anything else keeps its own name.
FAMILIES = [('express integrity', ('ExpressIntegrity',)), ('integrity', ('Integrity',)),
            ('in-app update', ('AppUpdate', 'OnRequestInstallCallback')), ('asset delivery', ('AssetPack',)),
            ('split install', ('SplitInstall',)), ('in-app review', ('Review',))]


def family(name):
    for label, parts in FAMILIES:
        if any(part in name for part in parts):
            return label
    return name


# Play Core's in-app review logs its callback under the in-app update callback's class name
# (OnRequestInstallCallback); the callback's own name says which service answered.
CALLBACK_FAMILIES = {'onGetLaunchReviewFlowInfo': 'in-app review'}
CALLBACK = re.compile(r'^(on[A-Z]\w*)')
ERROR = re.compile(r'onError\((-?\d+)\)|failed: (-?\d+)')


def score(logs, only=None):
    calls = collections.defaultdict(set)          # service -> apps that logged anything for it
    callbacks = collections.defaultdict(lambda: collections.defaultdict(set))
    errors = collections.defaultdict(lambda: collections.defaultdict(set))
    binding = collections.defaultdict(set)        # service -> apps that started a bind
    connected = collections.defaultdict(set)      # service -> apps whose bind connected
    for path in sorted(Path(logs).glob('hk-*.hilog')):
        app = path.name[len('hk-'):-len('.hilog')]
        if only is not None and app not in only:
            continue
        for line in path.read_text(errors='replace').splitlines():
            if 'PlayCore' not in line and 'PlayIntegrity' not in line:
                continue
            m = LINE.search(line)
            if not m:
                continue
            service, message = family(m.group(1)), m.group(2).strip()
            c = CALLBACK.match(message)
            if c and c.group(1) in CALLBACK_FAMILIES:
                service = CALLBACK_FAMILIES[c.group(1)]
            calls[service].add(app)
            if message.startswith('Initiate binding to the service'):
                binding[service].add(app)
            elif message.startswith('linkToDeath'):
                connected[service].add(app)
            e = ERROR.search(message)
            if e:
                errors[service][e.group(1) or e.group(2)].add(app)
                continue
            if c and c.group(1) not in ('onServiceConnected', 'onServiceDisconnected', 'onBindingDied'):
                callbacks[service][c.group(1)].add(app)
    unconnected = {service: apps - connected[service] for service, apps in binding.items() if apps - connected[service]}
    return calls, callbacks, errors, unconnected


TRACE = re.compile(r'\[WL-PLAY-TRACE\] (out|in) (\S+) code=(\d+) (\S*)')
# The Play Store's interfaces: Play Core's and Play's protocols, the store's own (billing, licensing, key transfer)
# and Engage's. Calls to Play services go to the other host.
STORE = ('com.google.android.play.', 'com.android.vending.', 'com.google.android.finsky.', 'com.google.android.engage.')
INTERFACE_TRANSACTION = '1598968902'


def traces(logs, only=None):
    """Per Play Store interface, from the binder trace in each app's stderr: the apps that called it, those whose
    two-way calls were answered (the reply's first int, the exception code, 0) or failed (by code), and those whose
    one-way calls (or empty replies) got a call back on an interface of the interface's own package. Codes, not
    data, are traced."""
    calls = collections.defaultdict(set)
    replied = collections.defaultdict(set)
    failed = collections.defaultdict(lambda: collections.defaultdict(set))
    oneway = collections.defaultdict(set)
    called_back = collections.defaultdict(set)
    for path in sorted(Path(logs).glob('hk-*.stderr')):
        app = path.name[len('hk-'):-len('.stderr')]
        if only is not None and app not in only:
            continue
        sent, back = set(), set()
        for line in path.read_text(errors='replace').splitlines():
            if '[WL-PLAY-TRACE]' not in line:
                continue
            m = TRACE.search(line)
            if not m:
                continue
            way, descriptor, code, reply = m.groups()
            if way == 'in':
                if code != INTERFACE_TRANSACTION:
                    back.add(descriptor.rpartition('.')[0])
                continue
            if not descriptor.startswith(STORE):
                continue
            calls[descriptor].add(app)
            if reply in ('oneway', 'empty'):
                # An empty reply to a two-way call: the store's side of the method is one-way (Billing's
                # callback methods, licensing's checkLicenseV2), so its answer is a call back too.
                oneway[descriptor].add(app)
                sent.add(descriptor)
                if reply == 'empty':
                    failed[descriptor][reply].add(app)
            elif reply == '0':
                replied[descriptor].add(app)
            else:
                failed[descriptor][reply].add(app)
        for descriptor in sent:
            if descriptor.rpartition('.')[0] in back:
                called_back[descriptor].add(app)
    return calls, replied, failed, oneway, called_back


def main():
    tag = sys.argv[1]
    show_apps = '--apps' in sys.argv[2:]
    logs = Path(os.environ['WL_SC']) / 'inputs/logs' / tag
    only = None
    if os.environ.get('LIST'):
        only = {x.strip() for x in open(os.environ['LIST']) if x.strip()}
    calls, callbacks, errors, unconnected = score(logs, only)
    for service in sorted(calls, key=lambda s: -len(calls[s])):
        answered = set().union(*callbacks[service].values()) if callbacks[service] else set()
        print(f'{service}: {len(calls[service])} apps, {len(answered)} with a callback')
        if service in unconnected:
            apps = unconnected[service]
            print(f'  never connected: {len(apps)}' + (f'  {" ".join(sorted(apps))}' if show_apps else ''))
        for name, apps in sorted(callbacks[service].items(), key=lambda kv: -len(kv[1])):
            print(f'  {name}: {len(apps)}' + (f'  {" ".join(sorted(apps))}' if show_apps else ''))
        for code, apps in sorted(errors[service].items(), key=lambda kv: -len(kv[1])):
            print(f'  error {code}: {len(apps)}' + (f'  {" ".join(sorted(apps))}' if show_apps else ''))
    calls, replied, failed, oneway, called_back = traces(logs, only)
    if calls:
        print('Play Store interfaces in the binder trace:')
    for descriptor in sorted(calls, key=lambda d: -len(calls[d])):
        said = []
        if replied[descriptor] or set(failed[descriptor]) - {'empty'}:
            said.append(f'{len(replied[descriptor])} answered')
        if oneway[descriptor]:
            said.append(f'{len(oneway[descriptor])} one-way or empty reply, {len(called_back[descriptor])} called back')
        print(f'  {descriptor}: {len(calls[descriptor])} apps; ' + ', '.join(said))
        for name, apps in (('answered', replied[descriptor]), ('called back', called_back[descriptor])):
            if show_apps and apps:
                print(f'    {name}: {" ".join(sorted(apps))}')
        for code, apps in sorted(failed[descriptor].items(), key=lambda kv: -len(kv[1])):
            print(f'    reply {code}: {len(apps)}' + (f'  {" ".join(sorted(apps))}' if show_apps else ''))


if __name__ == '__main__':
    main()
