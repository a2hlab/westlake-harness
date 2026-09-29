#!/usr/bin/env python3
"""B8 (#65) acceptance checks: inventory | not_ported | effective | white_window | lit | no_regression."""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
INV = json.loads((HERE / 'inventory.json').read_text())['items']
RES = HERE / 'results.json'


def fail(msg):
    print('FAIL:', msg); sys.exit(1)


def board():
    if not RES.exists():
        fail('no board results yet (overlay waits for the #66 generation)')
    return json.loads(RES.read_text())


def inventory():
    if [r['num'] for r in INV] != list(range(1, 24)):
        fail('inventory rows are not items 1..23')
    for r in INV:
        if not (r['westlake'] and r['route_a'] and r['status']):
            fail('item %d lacks Westlake/route-A location or status' % r['num'])
        if r['status'].startswith('missing') and not r['port_approach'].strip('— '):
            fail('missing item %d has no port approach' % r['num'])
    print('inventory: 23 items with Westlake location, route-A location and status')


def not_ported():
    for r in INV:
        if 'port' not in r and len(r.get('not_ported_reason', '')) < 10:
            fail('item %d neither ported nor explained' % r['num'])
    print('not_ported: %d items carry a reason' % sum('port' not in r for r in INV))


def effective():
    res = board()
    for r in INV:
        if 'port' not in r:
            continue
        ev = res.get('effective', {}).get(str(r['num']))
        if not ev or not ev.get('marker_lines') or ev.get('original_error_count', 1) != 0:
            fail('item %d has no positive on-board evidence' % r['num'])
    print('effective: every ported item has on-board evidence')


def white_window():
    res = board().get('white_window', {})
    if len(res) < 7 or any('schedule_launch_ability' not in v or 'first_frame' not in v for v in res.values()):
        fail('white-window apps not all recorded')
    print('white_window: recorded')


def lit():
    res = board()
    if res.get('lit_count') is None or res.get('lit_count') != res.get('outer_signed_lit_count'):
        fail('lit count not yet signed by the outer loop')
    print('lit: matches outer review')


def no_regression():
    res = board().get('no_regression', {})
    if not (res.get('helloworld') and res.get('zigzag')):
        fail('HelloWorld/ZigZag regression screenshots missing')
    print('no_regression: screenshots pending outer review')


{'inventory': inventory, 'not_ported': not_ported, 'effective': effective, 'white_window': white_window,
 'lit': lit, 'no_regression': no_regression}[sys.argv[1]]()
