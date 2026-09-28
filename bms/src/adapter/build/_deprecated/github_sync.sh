#!/bin/bash
# GitHub sync plumbing — sync doc/ to a remote branch without cloning the repo.
# Avoids Windows invalid-path issues in the remote tree by using git plumbing commands
# (hash-object / mktree / commit-tree) instead of checkout.
#
# STATUS (2026-04-15): GitHub sync is PAUSED. Do not run without explicit user approval.
#
# Authenticates via Windows Credential Manager (credential.helper=manager).

set -e

REPO="https://github.com/AlexYang-AgentCode/AI-Core-Team-Project.git"
BRANCH="Iceberg-Chen-v1.0"
TARGET_DIR="m_HanBingChen/doc"
SOURCE_DIR="/d/code/adapter/doc"

# 1. Init temp repo, fetch remote HEAD (shallow, no checkout)
TMPDIR=$(mktemp -d /tmp/gh_sync_XXXXXX)
cd "$TMPDIR"
git init && git remote add origin $REPO
git config user.email "iceberg@adapter.dev"
git config user.name "Iceberg Chen"
git fetch origin $BRANCH --depth=1
PARENT=$(git rev-parse FETCH_HEAD)

# 2. Create blobs for all files
TREE_INPUT=""
for f in $SOURCE_DIR/*.html $SOURCE_DIR/*.txt; do
    name=$(basename "$f")
    blob=$(git hash-object -w "$f")
    TREE_INPUT="${TREE_INPUT}100644 blob ${blob}\t${name}\n"
done
DOC_TREE=$(printf "$TREE_INPUT" | git mktree)

# 3. Build tree hierarchy (merge into existing repo tree)
PARENT_TREE=$(git cat-file -p $PARENT | head -1 | awk '{print $2}')
M_SHA=$(git ls-tree $PARENT_TREE | grep "m_HanBingChen" | awk '{print $3}')
NEW_M=$((git ls-tree "$M_SHA" | grep -v "	doc$"; echo "040000 tree $DOC_TREE	doc") | sort -t$'\t' -k2 | git mktree)
NEW_ROOT=$((git ls-tree "$PARENT_TREE" | grep -v "	m_HanBingChen$"; echo "040000 tree $NEW_M	m_HanBingChen") | sort -t$'\t' -k2 | git mktree)

# 4. Create commit and push
COMMIT=$(echo "Sync docs" | git commit-tree "$NEW_ROOT" -p "$PARENT")
git push origin "$COMMIT":refs/heads/$BRANCH

# 5. Cleanup
rm -rf "$TMPDIR"
