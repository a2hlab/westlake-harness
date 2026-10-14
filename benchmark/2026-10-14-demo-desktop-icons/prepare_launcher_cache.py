import argparse
import base64
import hashlib
import json
import sqlite3
from pathlib import Path

from prepare_cache import identifier, literal, predicate

PACKAGES = ('app.varlorg.unote', 'com.alxgnon.postwriter', 'org.tasks',
            'com.kaajjo.libresudoku', 'com.lcdcode.moodcairns',
            'com.paperknifeplus.app', 'com.groce.app', 'org.fossify.calendar')
COLUMNS = ('bundle_name', 'module_name', 'ability_name', 'icon_type', 'fore_pic', 'back_pic', 'combine_pic', 'system_state', 'app_version')
PLACEHOLDER = '3554d69ae22fe60a485a56e6099cb873943fc34f461b42898d2f8e42c5c0fc7f'


def make_sql(before, after=None):
    lines = ['.bail on', 'PRAGMA busy_timeout=5000;', 'DROP TABLE IF EXISTS temp.launcher_icon_guard;',
             'BEGIN IMMEDIATE;' if after is not None else 'BEGIN;',
             'CREATE TEMP TABLE launcher_icon_guard(ok INTEGER CHECK(ok=1));']
    for package in PACKAGES:
        count = sum(row[0] == package for row in before)
        lines.append(f'INSERT INTO launcher_icon_guard SELECT CASE WHEN (SELECT count(*) FROM icon_info WHERE bundle_name={literal(package)})={count} THEN 1 ELSE 0 END;')
    for index, old in enumerate(before):
        where = predicate(COLUMNS, old)
        lines.append(f'INSERT INTO launcher_icon_guard SELECT CASE WHEN (SELECT count(*) FROM icon_info WHERE {where})=1 THEN 1 ELSE 0 END;')
        if after is not None:
            new = after[index]
            lines.append(f'UPDATE icon_info SET combine_pic={literal(new[6])} WHERE {where};')
            lines.append('INSERT INTO launcher_icon_guard SELECT CASE WHEN changes()=1 THEN 1 ELSE 0 END;')
            lines.append(f'INSERT INTO launcher_icon_guard SELECT CASE WHEN (SELECT count(*) FROM icon_info WHERE {predicate(COLUMNS, new)})=1 THEN 1 ELSE 0 END;')
    lines.extend(['COMMIT;' if after is not None else 'ROLLBACK;', "SELECT 'LAUNCHER_ICON_ROWS_VERIFIED';"])
    return '\n'.join(lines) + '\n'


def build(connection, images):
    columns = tuple(row[1] for row in connection.execute('PRAGMA table_info(icon_info)'))
    if columns != COLUMNS:
        raise ValueError('actual launcher schema changed')
    before = []
    after = []
    for package in PACKAGES:
        rows = connection.execute('SELECT * FROM icon_info WHERE bundle_name=? ORDER BY module_name,ability_name', (package,)).fetchall()
        if len(rows) != (3 if package == 'org.fossify.calendar' else 2):
            raise ValueError('unexpected launcher row closure')
        for row in rows:
            if row[3] != 'normal' or row[4] is not None or row[5] is not None:
                raise ValueError('not verified normal/combine-only icon')
            if not isinstance(row[6], str) or not row[6].startswith('data:image/png;base64,'):
                raise ValueError('unexpected launcher image encoding')
            data = base64.b64decode(row[6].split(',', 1)[1], validate=True)
            if hashlib.sha256(data).hexdigest() != PLACEHOLDER:
                raise ValueError('not the captured placeholder; refuse foreign image')
            new = list(row)
            new[6] = 'data:image/png;base64,' + base64.b64encode(images[package]).decode('ascii')
            before.append(row)
            after.append(tuple(new))
    return before, after


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db-copy', type=Path, required=True)
    parser.add_argument('--db-sha', required=True)
    parser.add_argument('--wal-sha', required=True)
    parser.add_argument('--three', type=Path, required=True)
    parser.add_argument('--five', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if hashlib.sha256(args.db_copy.read_bytes()).hexdigest() != args.db_sha:
        raise ValueError('launcher DB input changed')
    wal = Path(str(args.db_copy) + '-wal')
    if hashlib.sha256(wal.read_bytes()).hexdigest() != args.wal_sha:
        raise ValueError('launcher WAL input changed')
    images = {}
    for directory in [args.three, args.five]:
        for receipt in json.loads((directory / 'receipts.json').read_text()):
            package = receipt['package']
            png = (directory / (package + '.png')).read_bytes()
            if hashlib.sha256(png).hexdigest() != receipt['png_sha256'] or not png.startswith(b'\x89PNG\r\n\x1a\n'):
                raise ValueError('candidate image identity drift')
            if package in images:
                raise ValueError('duplicate candidate')
            images[package] = png
    if set(images) != set(PACKAGES):
        raise ValueError('not exact eight-package image set')
    connection = sqlite3.connect(args.db_copy.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        before, after = build(connection, images)
    finally:
        connection.close()
    args.out.mkdir(parents=True, exist_ok=False)
    sqls = {'apply.sql': make_sql(before, after), 'rollback.sql': make_sql(after, before),
            'verify-before.sql': make_sql(before), 'verify-after.sql': make_sql(after)}
    for name, value in sqls.items():
        (args.out / name).write_text(value)
    (args.out / 'row-backup.json').write_text(json.dumps([dict(zip(COLUMNS, row)) for row in before], indent=2) + '\n')
    result = dict(execution_enabled=False, table='icon_info', changed_columns=['combine_pic'], row_count=len(before),
                  exact_keys=[dict(zip(COLUMNS[:3], row[:3])) for row in before],
                  db_sha256=args.db_sha, wal_sha256=args.wal_sha,
                  files={name: hashlib.sha256(value.encode()).hexdigest() for name, value in sqls.items()},
                  unrelated_tables_changed=False, whole_db_replacement=False,
                  abc_source_binding='pending native authoritative normal-icon read chain',
                  device_calls=0)
    (args.out / 'plan.disabled.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
