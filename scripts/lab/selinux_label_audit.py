#!/usr/bin/env python3
"""Read-only recursive label audit; relabel is callable only by guarded deployment."""
import argparse
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import posixpath
import re
import shlex
import shutil
import subprocess
import sys


RECIPE = Path(__file__).resolve().parents[2] / 'knowledge/gates/selinux-label-recipe.json'


def safe_target(path):
    if not isinstance(path, str) or not re.fullmatch(r'/(?:system|data/app)/[A-Za-z0-9_./+-]+', path):
        raise ValueError('unsafe label target: ' + str(path))
    if posixpath.normpath(path) != path or '..' in Path(path).parts:
        raise ValueError('noncanonical label target: ' + path)
    return path


def load_recipe(path=RECIPE):
    recipe = json.loads(Path(path).read_text())
    if recipe.get('schema_version') != 1 or not recipe.get('rules') or not recipe.get('required_targets'):
        raise ValueError('invalid label recipe')
    sources = {row['id'] for row in recipe['sources']}
    for row in [*recipe['rules'], recipe['default']]:
        if not re.fullmatch(r'u:object_r:[a-zA-Z0-9_]+:s0', row['context']) or not row.get('sources'):
            raise ValueError('invalid recipe context/provenance')
        if not set(row['sources']) <= sources:
            raise ValueError('unknown recipe source')
        if row is not recipe['default'] and set(row['match']) not in [{'exact'}, {'prefix'}, {'glob'}]:
            raise ValueError('invalid recipe matcher')
        if row is not recipe['default'] and not re.fullmatch(r'[A-Za-z0-9_./+*?-]+', next(iter(row['match'].values()))):
            raise ValueError('unsafe recipe matcher')
    for target in recipe['required_targets']:
        safe_target(target)
    return recipe


def expected_label(path, recipe):
    for row in recipe['rules']:
        match = row['match']
        if ('exact' in match and path == match['exact']) or (
            'prefix' in match and (path == match['prefix'] or path.startswith(match['prefix'] + '/'))
        ) or ('glob' in match and fnmatch.fnmatchcase(path, match['glob'])):
            return row['context'], row['id']
    return recipe['default']['context'], recipe['default']['id']


def plan_targets(plan, recipe):
    if isinstance(plan, list):
        rows, files = plan, {}
    elif isinstance(plan, dict):
        keys = [name for name in ['mounts', 'recover_layers'] if name in plan]
        if len(keys) != 1:
            raise ValueError('plan requires exactly one mounts/recover_layers list')
        rows, files = plan[keys[0]], plan.get('files', {})
    else:
        raise ValueError('invalid deployment plan')
    if not isinstance(rows, list) or not rows:
        raise ValueError('empty target inventory')
    targets = []
    for row in rows:
        target = safe_target(row['target'])
        kind = row.get('kind')
        if kind is None:
            source = row.get('source', '')
            if source in files:
                kind = 'file'
            elif source and any(name.startswith(source + '/') for name in files):
                kind = 'directory'
        if kind not in ['file', 'directory']:
            raise ValueError('file/directory kind cannot be determined: ' + target)
        targets.append(dict(target=target, kind=kind))
    if len({row['target'] for row in targets}) != len(targets):
        raise ValueError('duplicate target inventory')
    for required in recipe['required_targets']:
        if not any(required == row['target'] or (
            row['kind'] == 'directory' and required.startswith(row['target'] + '/')
        ) for row in targets):
            raise ValueError('required label scope missing: ' + required)
    return targets


def read_command(row):
    target = shlex.quote(row['target'])
    if row['kind'] == 'file':
        return 'set -eu; test -e ' + target + '; ls -Zd ' + target
    return ('set -eu; test -d ' + target + '; entries=$(find ' + target +
            ' -print) || exit; printf "%s\\n" "$entries" | while IFS= read -r entry; '
            'do ls -Zd "$entry" || exit; done')


def parse_labels(text, row):
    labels = {}
    for line in text.splitlines():
        fields = line.split()
        if len(fields) < 2:
            raise ValueError('unparseable ls -Z row: ' + line)
        path = safe_target(fields[-1])
        if path != row['target'] and not (row['kind'] == 'directory' and path.startswith(row['target'] + '/')):
            raise ValueError('label readback outside declared target: ' + path)
        contexts = [field for field in fields[:-1] if re.fullmatch(r'[^:]+:[^:]+:[^:]+:s[0-9]+(?:[:][^\s]+)?', field)]
        if len(contexts) != 1 or path in labels:
            raise ValueError('missing/ambiguous/duplicate label readback: ' + path)
        labels[path] = contexts[0]
    if row['target'] not in labels:
        raise ValueError('target omitted from label readback: ' + row['target'])
    return labels


def audit(shell, plan, recipe=None):
    recipe = recipe or load_recipe()
    targets = plan_targets(plan, recipe)
    labels = {}
    for row in targets:
        for path, label in parse_labels(shell(read_command(row)), row).items():
            if path in labels and labels[path] != label:
                raise ValueError('label changed during overlapping reads: ' + path)
            labels[path] = label
    for required in recipe['required_targets']:
        if required not in labels:
            raise ValueError('required label path absent: ' + required)
    rows = []
    for path, label in sorted(labels.items()):
        expected, rule = expected_label(path, recipe)
        rows.append(dict(path=path, expected=expected, actual=label, rule=rule, passed=expected == label))
    mismatches = [row for row in rows if not row['passed']]
    return dict(status='FAIL' if mismatches else 'PASS', target_count=len(targets), path_count=len(rows),
                rows=rows, mismatches=mismatches, complete=True)


def save_report(path, report):
    Path(path).write_text(json.dumps(report, indent=2) + '\n')


def generate_shell(recipe):
    digest = hashlib.sha256(json.dumps(recipe, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    lines = ['#!/system/bin/sh', 'set -u', 'set -f', 'LC_ALL=C; export LC_ALL',
             'LABEL_RECIPE_SHA256=' + shlex.quote(digest), 'label_context() {', 'case "$1" in']
    for row in recipe['rules']:
        match = row['match']
        if 'exact' in match:
            pattern = shlex.quote(match['exact'])
        elif 'prefix' in match:
            pattern = shlex.quote(match['prefix']) + '|' + shlex.quote(match['prefix']) + '/*'
        else:
            pattern = match['glob']
        lines.append(pattern + ') printf "%s\\n" ' + shlex.quote(row['context']) + ' ;;')
    lines.extend(['*) printf "%s\\n" ' + shlex.quote(recipe['default']['context']) + ' ;;', 'esac', '}',
                  'label_required() { printf "%s\\n" ' + ' '.join(map(shlex.quote, recipe['required_targets'])) + '; }'])
    lines.append(r'''
label_safe() {
 case "$1" in *[!A-Za-z0-9_./+-]*|*//*|*/../*|*/./*|*/..|*/.|*/) return 1 ;; esac
 case "$1" in /system/*|/data/app/*) return 0 ;; *) return 1 ;; esac
}
label_source_safe() {
 case "$1" in *[!A-Za-z0-9_./+-]*|*//*|*/../*|*/./*|*/..|*/.|*/) return 1 ;; esac
 case "$1" in /data/*) return 0 ;; *) return 1 ;; esac
}
mode=${1:-audit}
case "$mode" in
 context) label_safe "${2:-}" || exit 2; label_context "$2"; exit 0 ;;
 audit|apply|audit-source|apply-source) ;;
 *) printf 'FAIL invalid mode\n'; exit 2 ;;
esac
plan=$(cat "${2:--}") || { printf 'FAIL plan unreadable\n'; exit 2; }
[ -n "$plan" ] || { printf 'FAIL empty plan\n'; exit 2; }
tab=$(printf '\t')
seen='|'
while IFS="$tab" read -r kind target source extra; do
 [ -z "$extra" ] || { printf 'FAIL invalid plan columns\n'; exit 2; }
 case "$kind" in file|directory) ;; *) printf 'FAIL invalid target kind\n'; exit 2 ;; esac
 label_safe "$target" || { printf 'FAIL unsafe target %s\n' "$target"; exit 2; }
 case "$seen" in *"|$target|"*) printf 'FAIL duplicate target %s\n' "$target"; exit 2 ;; esac
 seen="$seen$target|"
 case "$mode" in *-source) label_source_safe "$source" || { printf 'FAIL unsafe source %s\n' "$source"; exit 2; } ;; esac
done <<LABEL_PLAN_VALIDATE
$plan
LABEL_PLAN_VALIDATE
required=$(label_required)
while IFS= read -r wanted; do
 covered=0
 while IFS="$tab" read -r kind target source extra; do
  [ "$wanted" = "$target" ] && covered=1
  if [ "$kind" = directory ]; then case "$wanted" in "$target"/*) covered=1 ;; esac; fi
 done <<LABEL_PLAN_COVERAGE
$plan
LABEL_PLAN_COVERAGE
 [ "$covered" = 1 ] || { printf 'FAIL required target missing %s\n' "$wanted"; exit 2; }
done <<LABEL_REQUIRED
$required
LABEL_REQUIRED
paths=0
bad=0
seen_paths='|'
while IFS="$tab" read -r kind target source extra; do
 physical=$target
 case "$mode" in *-source) physical=$source ;; esac
 if [ "$kind" = directory ]; then
  toybox test -d "$physical" || { printf 'FAIL directory absent %s\n' "$physical"; exit 1; }
  entries=$(find "$physical" -print) || { printf 'FAIL incomplete tree %s\n' "$physical"; exit 1; }
 else
  toybox test -e "$physical" || { printf 'FAIL file absent %s\n' "$physical"; exit 1; }
  entries=$physical
 fi
 [ -n "$entries" ] || { printf 'FAIL empty inventory %s\n' "$physical"; exit 1; }
 while IFS= read -r entry; do
  case "$mode" in
   *-source) label_source_safe "$entry" || exit 2 ;;
   *) label_safe "$entry" || exit 2 ;;
  esac
  canonical="$target${entry#"$physical"}"
  seen_paths="$seen_paths$canonical|"
  expected=$(label_context "$canonical")
  listing=$(ls -Zd "$entry") || { printf 'FAIL %s expected=%s actual=unreadable\n' "$canonical" "$expected"; exit 1; }
  actual='?'
  labels=0
  for field in $listing; do
   case "$field" in *:object_r:*:s0) actual=$field; labels=$((labels+1)) ;; esac
  done
  [ "$labels" = 1 ] || actual='?'
  case "$mode" in
   apply|apply-source)
    if [ "$actual" != "$expected" ]; then
     chcon -h "$expected" "$entry" || { printf 'FAIL %s expected=%s actual=%s chcon=failed\n' "$canonical" "$expected" "$actual"; exit 1; }
     listing=$(ls -Zd "$entry") || exit 1
     actual='?'; labels=0
     for field in $listing; do
      case "$field" in *:object_r:*:s0) actual=$field; labels=$((labels+1)) ;; esac
     done
     [ "$labels" = 1 ] || actual='?'
    fi ;;
  esac
  paths=$((paths+1))
  if [ "$actual" != "$expected" ]; then
   bad=$((bad+1))
   printf 'FAIL %s expected=%s actual=%s\n' "$canonical" "$expected" "$actual"
  fi
 done <<LABEL_ENTRIES
$entries
LABEL_ENTRIES
done <<LABEL_PLAN_APPLY
$plan
LABEL_PLAN_APPLY
while IFS= read -r wanted; do
 case "$seen_paths" in *"|$wanted|"*) ;; *) printf 'FAIL required readback absent %s\n' "$wanted"; exit 1 ;; esac
done <<LABEL_FINAL_REQUIRED
$required
LABEL_FINAL_REQUIRED
printf 'LABEL-RECIPE paths=%s mismatches=%s recipe=%s\n' "$paths" "$bad" "$LABEL_RECIPE_SHA256"
if [ "$bad" = 0 ]; then printf 'PASS\n'; exit 0; fi
printf 'FAIL\n'; exit 1
'''.strip())
    return '\n'.join(lines) + '\n'


def apply_recipe(shell, plan, evidence):
    evidence = Path(evidence)
    evidence.mkdir(parents=True, exist_ok=False)
    recipe = load_recipe()
    provenance = dict(recipe_sha256=hashlib.sha256(RECIPE.read_bytes()).hexdigest(),
                      sources=recipe['sources'])
    save_report(evidence / 'recipe.json', provenance)
    try:
        before = audit(shell, plan, recipe)
        save_report(evidence / 'before.json', before)
        script = generate_shell(recipe)
        (evidence / 'label-recipe.sh').write_text(script)
        targets = plan_targets(plan, recipe)
        tsv = '\n'.join(row['kind'] + '\t' + row['target'] for row in targets) + '\n'
        (evidence / 'plan.tsv').write_text(tsv)
        output = shell('sh -c ' + shlex.quote(script) + ' -- apply - <<\'LABEL_RECIPE_INPUT\'\n' + tsv + 'LABEL_RECIPE_INPUT')
        (evidence / 'apply-stdout.txt').write_text(output)
        after = audit(shell, plan, recipe)
        save_report(evidence / 'after.json', after)
        if after['status'] != 'PASS':
            details = '; '.join(row['path'] + ' expected=' + row['expected'] + ' actual=' + row['actual'] for row in after['mismatches'])
            raise RuntimeError('SELinux label recipe rejected: ' + details)
        return after
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        save_report(evidence / 'failure.json', dict(status='FAIL', error=str(error)))
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('serial')
    parser.add_argument('plan', type=Path)
    parser.add_argument('--hdc', default=os.environ.get('HDC') or shutil.which('hdc'))
    parser.add_argument('--recipe', type=Path, default=RECIPE)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    import lab_paths
    if args.serial not in lab_paths.boards('oh'):
        raise ValueError('serial is not an approved full OH board identifier')
    recipe = load_recipe(args.recipe)
    plan = json.loads(args.plan.read_text())
    plan_targets(plan, recipe)
    if not args.hdc:
        raise ValueError('set HDC or --hdc to the executable/forwarding wrapper')
    args.out.mkdir(parents=True, exist_ok=False)
    count = 0

    def shell(command):
        nonlocal count
        count += 1
        result = subprocess.run([args.hdc, '-t', args.serial, 'shell', command], capture_output=True,
                                text=True, encoding='utf-8', errors='backslashreplace', timeout=120)
        save_report(args.out / f'{count:03d}.json', dict(command=command, exit_code=result.returncode,
                    stdout=result.stdout, stderr=result.stderr))
        if result.returncode or result.stderr.strip():
            raise RuntimeError('incomplete label collection; inspect raw=' + f'{count:03d}.json')
        return result.stdout

    try:
        boot_before = shell('cat /proc/sys/kernel/random/boot_id').strip()
        if not re.fullmatch(r'[0-9a-f-]{36}', boot_before):
            raise ValueError('boot identity missing')
        report = audit(shell, plan, recipe)
        if shell('cat /proc/sys/kernel/random/boot_id').strip() != boot_before:
            raise ValueError('boot changed during label audit')
        report.update(serial=args.serial, boot_id=boot_before, readonly=True,
                      plan_sha256=hashlib.sha256(args.plan.read_bytes()).hexdigest(),
                      recipe_sha256=hashlib.sha256(args.recipe.read_bytes()).hexdigest())
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        report = dict(status='FAIL', serial=args.serial, readonly=True, complete=False, error=str(error))
    save_report(args.out / 'audit.json', report)
    print(report['status'])
    for row in report.get('mismatches', []):
        print(row['path'] + ' expected=' + row['expected'] + ' actual=' + row['actual'])
    if report.get('error'):
        print(report['error'])
    return 0 if report['status'] == 'PASS' else 1


def generate_main(argv):
    parser = argparse.ArgumentParser(description='Generate the shared toybox-only board label recipe')
    parser.add_argument('--recipe', type=Path, default=RECIPE)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    args.out.write_text(generate_shell(load_recipe(args.recipe)))
    args.out.chmod(0o755)


if __name__ == '__main__':
    if sys.argv[1:2] == ['generate-sh']:
        generate_main(sys.argv[2:])
    else:
        sys.exit(main())
