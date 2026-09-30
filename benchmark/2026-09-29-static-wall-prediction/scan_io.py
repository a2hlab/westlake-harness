"""Read tracked gzip evidence transparently; original files may remain in a live worktree."""
import gzip,json
from pathlib import Path
def physical(path):
    path=Path(path)
    return path if path.exists() else Path(str(path)+'.gz') if Path(str(path)+'.gz').exists() else path
def load(path):
    path=physical(path)
    return json.loads(gzip.open(path,'rt').read() if path.suffix=='.gz' else path.read_text())
