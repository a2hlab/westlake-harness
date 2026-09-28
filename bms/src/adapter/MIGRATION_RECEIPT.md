# Adapter source migration receipt

- Canonical destination: `/opt/Bridge/src/adapter`
- Source snapshot: `/opt/Bridge/src/AlexBridge`
- Repository baseline: `c3589dbbd3dc944ee29f2f0f3964bec25a0c0b86`
- Migration mode: copy; the source directory was not deleted or rewritten
- Scope: source, patches, build/deploy/verification scripts, configuration,
  design documentation, local source snapshot, and versioned build inputs
- Excluded generated state: every `out/`, `.work/`, `.build/`, `build_out/`,
  and `.gen_tmp/` directory, plus `app/build/`
- Canonical-path rewrite: copied references to
  `/opt/Bridge/src/AlexBridge` were changed to `/opt/Bridge/src/adapter`

The source snapshot had pre-existing tracked and untracked work.  This
migration intentionally captures its current code state under the new
canonical directory while leaving all unrelated repository paths unstaged.
Git provides the authoritative content identity for the committed snapshot.
