# Verified remote REA archive

The original five public packet files are copied byte-identically. Their pending upload plan remains the historical pre-upload stage. This new receipt records actual execution: local verification, absent-directory creation, transfer, remote SHA/size/mode check and remote full member verification all returned rc 0.

Remote artifact: `HW248_ARTIFACT_ROOT/t23-codex-rea-evidence-20261020/t23-codex-rea-evidence.tar.gz`. SHA-256 `934e425dd25b4c3432d65d0757a60cc87269e56117249c21c4fc0ce71be13631`, 6,198,752 bytes. Directory mode 700 and file mode 600 were read back. Existing destinations were refused; no overwrite occurred.

The same exact `verify_archive.py` verified the archive locally and on hw248. Both outputs match: all 66 data members match their recorded SHA/size, the manifest hash matches, and the member set contains exactly those 66 plus MANIFEST.json (67 total). The script does not extract or execute archive contents.

Actual private argv/stdout/stderr/rc are indexed in `source-index.json`; public `sanitized-envelopes.json` replaces only local home and remote artifact-root aliases. The archive remains private because original REA/log records contain local operational paths. The packet's function-extent cautions and static-only limitations remain unchanged. No new REA analysis, ADB, HDC or playback claim was made for this persistence step.
