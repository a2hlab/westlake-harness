"""Fetch every not-yet-present project of the given manifest locks with the manifest's own fetch().

Unlike tools/fetch_sources.py this continues past a failed project (e.g. an LFS budget error) and
reports all failures at the end; a project directory that already exists is left untouched.
"""
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

manifest, workspace = Path(sys.argv[1]), Path(sys.argv[2]).resolve()
sys.path.insert(0, str(manifest / "tools"))
from fetch_sources import fetch, read_lock  # noqa: E402

todo, seen = [], set()
for lock in sys.argv[3:]:
    for entry in read_lock(manifest / lock):
        if entry["path"] not in seen and not (workspace / entry["path"]).exists():
            seen.add(entry["path"])
            todo.append(entry)
print(f"TODO {len(todo)} projects", flush=True)
failed = []
with ThreadPoolExecutor(max_workers=4) as pool:
    futures = {pool.submit(fetch, entry, workspace): entry for entry in todo}
    for future in as_completed(futures):
        try:
            future.result()
        except Exception as error:  # keep going; report everything at the end
            output = getattr(error, "output", b"") or b""
            failed.append((futures[future]["path"], f"{error} {output.decode(errors='replace')[-300:]}"))
            print("FAILED", futures[future]["path"], flush=True)
for path, why in failed:
    print("FAILURE", path, "::", why.replace("\n", " "), flush=True)
print(f"DONE {len(todo) - len(failed)}/{len(todo)} fetched", flush=True)
