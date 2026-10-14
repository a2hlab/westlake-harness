import argparse
import base64
import hashlib
import json
import re
import sqlite3
from pathlib import Path

PACKAGES = ('app.varlorg.unote', 'com.alxgnon.postwriter', 'org.tasks')
TABLE = 'bundleResource'


def identifier(value):
    if not re.fullmatch('[A-Za-z_][A-Za-z0-9_]*', value):
        raise ValueError('unexpected SQL identifier')
    return '"' + value + '"'


def literal(value):
    if value is None:
        return 'NULL'
    if isinstance(value, bytes):
        return "X'" + value.hex() + "'"
    if isinstance(value, str):
        if '\x00' in value:
            raise ValueError('NUL in SQLite text')
        return "'" + value.replace("'", "''") + "'"
    if isinstance(value, (int, float)):
        return str(value)
    raise ValueError('unexpected SQLite type')


def predicate(columns, row):
    return ' AND '.join(identifier(column) + ' IS ' + literal(value) for column, value in zip(columns, row))


def belongs(name, package):
    return name == package or name.startswith(package + '/')


def make_sql(columns, before, after):
    lines = ['.bail on', 'PRAGMA busy_timeout=5000;', 'DROP TABLE IF EXISTS temp.icon_cas_guard;', 'BEGIN IMMEDIATE;',
             'CREATE TEMP TABLE icon_cas_guard (ok INTEGER CHECK(ok=1));']
    names = [row[columns.index('NAME')] for row in before]
    for package in PACKAGES:
        expected = sum(belongs(name, package) for name in names)
        query = f"SELECT count(*) FROM {identifier(TABLE)} WHERE NAME={literal(package)} OR substr(NAME,1,{len(package) + 1})={literal(package + '/')}"
        lines.append(f'INSERT INTO icon_cas_guard SELECT CASE WHEN ({query})={expected} THEN 1 ELSE 0 END;')
    for old, new in zip(before, after):
        where = predicate(columns, old)
        lines.append(f'INSERT INTO icon_cas_guard SELECT CASE WHEN (SELECT count(*) FROM {identifier(TABLE)} WHERE {where})=1 THEN 1 ELSE 0 END;')
        assignments = ','.join(identifier(column) + '=' + literal(new[index]) for index, column in enumerate(columns) if column in ('ICON', 'FOREGROUND'))
        lines.append(f'UPDATE {identifier(TABLE)} SET {assignments} WHERE {where};')
        lines.append('INSERT INTO icon_cas_guard SELECT CASE WHEN changes()=1 THEN 1 ELSE 0 END;')
        lines.append(f'INSERT INTO icon_cas_guard SELECT CASE WHEN (SELECT count(*) FROM {identifier(TABLE)} WHERE {predicate(columns, new)})=1 THEN 1 ELSE 0 END;')
    lines.extend(['COMMIT;', 'SELECT \'ICON_ROW_TRANSACTION_COMMITTED\';'])
    return '\n'.join(lines) + '\n'


def make_verify_sql(columns, rows):
    lines = ['.bail on', 'DROP TABLE IF EXISTS temp.icon_cas_guard;', 'BEGIN;',
             'CREATE TEMP TABLE icon_cas_guard (ok INTEGER CHECK(ok=1));']
    names = [row[columns.index('NAME')] for row in rows]
    for package in PACKAGES:
        count = sum(belongs(name, package) for name in names)
        query = f"SELECT count(*) FROM {identifier(TABLE)} WHERE NAME={literal(package)} OR substr(NAME,1,{len(package) + 1})={literal(package + '/')}"
        lines.append(f'INSERT INTO icon_cas_guard SELECT CASE WHEN ({query})={count} THEN 1 ELSE 0 END;')
    for row in rows:
        lines.append(f'INSERT INTO icon_cas_guard SELECT CASE WHEN (SELECT count(*) FROM {identifier(TABLE)} WHERE {predicate(columns, row)})=1 THEN 1 ELSE 0 END;')
    lines.extend(['ROLLBACK;', "SELECT 'ICON_ROWS_VERIFIED';"])
    return '\n'.join(lines) + '\n'


def build(connection, images):
    columns = [row[1] for row in connection.execute(f'PRAGMA table_info({identifier(TABLE)})')]
    if not {'NAME', 'ICON', 'FOREGROUND'} <= set(columns):
        raise ValueError('unsupported actual schema')
    for column in columns:
        identifier(column)
    before = []
    after = []
    for row in connection.execute(f'SELECT * FROM {identifier(TABLE)} ORDER BY NAME'):
        name = row[columns.index('NAME')]
        matches = [package for package in PACKAGES if isinstance(name, str) and belongs(name, package)]
        if not matches:
            continue
        if len(matches) != 1:
            raise ValueError('ambiguous package key')
        package = matches[0]
        image = images[package]
        if not image.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('candidate is not PNG')
        replacement = list(row)
        replacement[columns.index('ICON')] = 'data:image/png;base64,' + base64.b64encode(image).decode('ascii')
        replacement[columns.index('FOREGROUND')] = image
        before.append(tuple(row))
        after.append(tuple(replacement))
    names = [row[columns.index('NAME')] for row in before]
    if any(not any(belongs(name, package) for name in names) for package in PACKAGES):
        raise ValueError('actual package rows missing or unsupported NAME layout')
    if len(names) != len(set(names)):
        raise ValueError('NAME not unique')
    return columns, before, after


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db-copy', type=Path, required=True)
    parser.add_argument('--db-sha', required=True)
    parser.add_argument('--candidates', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if hashlib.sha256(args.db_copy.read_bytes()).hexdigest() != args.db_sha:
        raise ValueError('received DB pin changed')
    receipts = {row['package']: row for row in json.loads((args.candidates / 'receipts.json').read_text())}
    images = {}
    for package in PACKAGES:
        images[package] = (args.candidates / (package + '.png')).read_bytes()
        if hashlib.sha256(images[package]).hexdigest() != receipts[package]['png_sha256']:
            raise ValueError('candidate PNG pin changed')
    connection = sqlite3.connect(args.db_copy.resolve().as_uri() + '?mode=ro', uri=True)
    try:
        columns, before, after = build(connection, images)
    finally:
        connection.close()
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / 'apply.sql').write_text(make_sql(columns, before, after))
    (args.out / 'rollback.sql').write_text(make_sql(columns, after, before))
    (args.out / 'verify-before.sql').write_text(make_verify_sql(columns, before))
    (args.out / 'verify-after.sql').write_text(make_verify_sql(columns, after))
    def encode(row):
        return {column: {'blob_hex': value.hex()} if isinstance(value, bytes) else value for column, value in zip(columns, row)}
    (args.out / 'row-backup.json').write_text(json.dumps([encode(row) for row in before], indent=2) + '\n')
    result = dict(execution_enabled=False, table=TABLE, columns=columns, exact_row_names=[row[columns.index('NAME')] for row in before],
                  db_source_sha256=args.db_sha, changed_columns=['ICON', 'FOREGROUND'],
                  apply_sha256=hashlib.sha256((args.out / 'apply.sql').read_bytes()).hexdigest(),
                  rollback_sha256=hashlib.sha256((args.out / 'rollback.sql').read_bytes()).hexdigest(),
                  row_count=len(before), required_execution='existing SQLite CLI with .bail on; one locked/root transaction; launcher refresh and actual tile readback',
                  whole_db_replacement=False, note='No current device changes performed by compiler')
    (args.out / 'plan.disabled.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
