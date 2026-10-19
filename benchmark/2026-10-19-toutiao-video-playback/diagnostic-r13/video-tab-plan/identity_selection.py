"""Pure identity checks; no device imports or discovery from truncated comm."""
NAME = 'com.ss.android.article.news'
UID = '20011206'
def select_exact(ps, parent, child):
    rows = [line.split() for line in ps.splitlines()]
    business = [r for r in rows if len(r) == 4 and r[2:] == [UID, NAME]]
    if business != [[str(child), str(parent), UID, NAME]]:
        raise ValueError('missing/ambiguous/different exact business child')
    return child

def check_stat(raw, pid, birth, parent=None):
    head, tail = raw.rsplit(') ', 1)
    fields = tail.split()
    if len(fields) < 20 or int(head.split()[0]) != pid or int(fields[19]) != birth:
        raise ValueError('PID/birth mismatch')
    if fields[0] in ('Z', 'X') or (parent is not None and int(fields[1]) != parent):
        raise ValueError('dead child or parent mismatch')
