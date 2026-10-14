#!/usr/bin/env python3
"""Apply reviewed delivery amendments without changing original API evidence."""
import argparse
import collections
import copy
import json
from pathlib import Path

import generate as g

BASE_SHA = 'c78e9e61f79b958f22e5f69a9309287d383c3824b74e38a16c4413e619c1d6b0'
ALLOWED = {'id', 'source_entry', 'coverage_status', 'gaps', 'recipe'}


def amend(base, recipes, changes, revision, tree):
    result = copy.deepcopy(base)
    recipe_doc = copy.deepcopy(recipes)
    rows = {row['id']: row for row in result['rows']}
    by_recipe = {recipe['id']: recipe for recipe in recipe_doc['recipes']}
    seen = set()
    for change in changes:
        g.need(set(change) <= ALLOWED, 'only delivery fields may be amended')
        rid = change['id']
        g.need(rid in rows and rid not in seen, 'unknown or duplicate row amendment')
        seen.add(rid)
        row = rows[rid]
        if 'source_entry' in change:
            entries = []
            for entry in change['source_entry']:
                audit = g.audit_entry(entry, revision, tree)
                g.need(audit['master_tracked_exact'], 'source must already be committed on master')
                g.need(entry.get('role') is not None, 'source role must be explicit')
                expected = entry.get('expected_sha256')
                g.need(expected is None or expected == audit['sha256'], 'source differs from expected hash')
                entries.append({**entry, 'git_blob': audit['git_blob'],
                                'master_blob': audit['git_blob'], 'master_tracked': True,
                                'exact_expected_match': expected == audit['sha256']})
            row['source_entry'] = entries
            row['source_revision'] = {
                'master_commit': revision,
                'expected_source_sha256': sorted({e['expected_sha256'] for e in entries if e.get('expected_sha256')}),
                'exact_binding': bool(entries) and all(e['exact_expected_match'] for e in entries),
                'binding_scope': 'source_evidence_pins_not_automatic_current_deployment',
                'status': 'reviewed_source_pins',
            }
        for field in ('coverage_status', 'gaps'):
            if field in change:
                row[field] = copy.deepcopy(change[field])
        if 'recipe' in change:
            recipe = copy.deepcopy(change['recipe'])
            # A row-specific recipe prevents changing unrelated rows implicitly.
            g.need(recipe['id'] == 'closeout-' + rid, 'recipe must be scoped to the amended row')
            if recipe.get('entry'):
                audit = g.audit_entry(recipe['entry'], revision, tree)
                g.need(audit['master_tracked_exact'], 'build entry must already be committed on master')
            by_recipe[recipe['id']] = recipe
            row['build_recipe'] = {'id': recipe['id'], 'path': 'recipes/recipes.json',
                                   'sha256': None, 'status': recipe['status']}
        row['complete_delivery_claim'] = False
    recipe_doc['recipes'] = list(by_recipe.values())
    for row in result['rows']:
        recipe = by_recipe[row['build_recipe']['id']]
        for target, source in [('build_command', 'command'), ('build_dependencies', 'dependencies'),
                               ('build_outputs', 'outputs'), ('build_verification', 'verification')]:
            row[target] = copy.deepcopy(recipe[source])
    result['master_commit'] = revision
    result['closeout'] = {'base_mapping_sha256': BASE_SHA, 'updated_rows': sorted(seen),
                         'api_semantic_evidence_changed': False}
    result['summary'].update(
        source_file_refs=sum(len(r['source_entry']) for r in result['rows']),
        master_exact_refs=sum(e['master_tracked'] for r in result['rows'] for e in r['source_entry']),
        coverage_counts=dict(collections.Counter(r['coverage_status'] for r in result['rows'])))
    return result, recipe_doc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--amendments', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    base_path = g.HERE / 'release-v2/source-build-mapping.json'
    g.need(g.sha(base_path) == BASE_SHA, 'immutable v2 mapping changed')
    base = g.read(base_path)
    recipes_path = base_path.parent / base['recipes']['path']
    g.need(g.sha(recipes_path) == base['recipes']['sha256'], 'base recipes changed')
    revision, tree = g.master_tree()
    result, recipes = amend(base, g.read(recipes_path), g.read(args.amendments)['rows'], revision, tree)
    g.need(not args.out.exists(), 'fresh output required')
    (args.out / 'recipes').mkdir(parents=True)
    recipes_path = args.out / 'recipes/recipes.json'
    g.write(recipes_path, recipes)
    digest = g.sha(recipes_path)
    result['recipes']['sha256'] = digest
    for row in result['rows']:
        row['build_recipe']['sha256'] = digest
    result['closeout']['amendments_sha256'] = g.sha(args.amendments)
    g.write(args.out / 'source-build-mapping.json', result)
    print(json.dumps(result['summary']))


if __name__ == '__main__':
    main()
