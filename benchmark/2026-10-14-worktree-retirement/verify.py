"""Fail-closed evidence gate for this bounded retirement, not a deletion tool."""
import json
from pathlib import Path
ALLOWLIST = {"westlake-harness-label", "agent-a2ef2d12ea17a76fc"}

def validate_removal(e):
    if e.get("name") not in ALLOWLIST:
        raise ValueError("outside exact allowlist")
    for field in ("master_ancestor", "tracked_clean", "untracked_clean", "live_content_matches_archive", "restore_verified", "no_open_files", "archive_members_verified"):
        if e.get(field) is not True:
            raise ValueError("unverified " + field)
    local, remote = e.get("local_archive_sha256", ""), e.get("remote_archive_sha256", "")
    if len(local) != 64 or any(c not in "0123456789abcdef" for c in local) or local != remote:
        raise ValueError("archive SHA missing or differs")
    return True

def validate_result(result):
    if result["branch_refs_unchanged_during_cleanup"] is not True:
        raise ValueError("branch refs changed")
    if result["force_used"] or result["remote_directories_removed"]:
        raise ValueError("unexpected mutation")
    for entry in result["removed"]:
        validate_removal(entry)
        if entry["remove_rc"] != 0 or entry["exists_after"]:
            raise ValueError("removal not completed")
    if set(e["name"] for e in result["removed"]) != ALLOWLIST:
        raise ValueError("incomplete bounded batch")
    if result["pruned_registration_count"] != 7 or not result["stale_residual_paths_unchanged"]:
        raise ValueError("stale metadata pruning differs")
    return True

if __name__ == "__main__":
    result = json.loads(Path(__file__).with_name("results.json").read_text())
    validate_result(result)
    print("VERIFIED: two archived removals, seven stale registrations, branches and retained data preserved")
