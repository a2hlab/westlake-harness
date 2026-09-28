"""List each manifest lock's projects and whether they are fetched into the workspace."""
import sys
from pathlib import Path

manifest, workspace = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(manifest / "tools"))
from fetch_sources import read_lock  # noqa: E402

for lock in sys.argv[3:]:
    entries = read_lock(manifest / lock)
    ready = [e for e in entries if (workspace / e["path"] / ".git/a2hlab-source.json").exists()]
    print(f"{lock:30s} projects={len(entries):3d} ready={len(ready):3d}")
    for e in entries:
        target = workspace / e["path"]
        state = "ready" if e in ready else ("PARTIAL" if target.exists() else "todo")
        if state != "ready" or e.get("lfs"):
            print(f"    {state:7s} {e['path']:55s} {e['url'].split('/')[-1]:44s} {'LFS' if e.get('lfs') else ''}")
