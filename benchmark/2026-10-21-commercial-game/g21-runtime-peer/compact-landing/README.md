# Compact G21 transaction review

The original apply and automatic rollback failed before runtime start because the remote wrapper joined the heredoc terminator. The later original-journal rollback succeeded, restored baseline/control rendering, and closed the window. The game was never started. Read initial/, recovery/, then closure/; their historical states remain separate.

This is the only proposed landing package. The prior full311-file review remains untouched as private audit material. Large stderr, full journal and native PASS exception dumps are not copied here. original-sha-index.json.gz contains only a JSON map of original relative paths to SHA256/size (9922 originals), not compressed log contents. Resolve paths under $G21_WINDOW as defined in source-index.json; journal-after-automatic-rollback.json is the immutable failed journal. Complete319-target tables remain in initial/hash-stages.json and recovery/hash-stages.json. label-summary.json separates the295-path audits from the299-path recipe report.

The two actual images already exist in main; public-evidence-refs.json pins their repository-relative paths and SHA, plus closure receipts. They are referenced rather than duplicated. Public text copies preserve previous path sanitization. No personal absolute path is required.

Run `python3 check_compact.py --main REPOSITORY_ROOT --raw PRIVATE_G21_WINDOW` to verify the package, referenced public evidence, and every indexed original. Both arguments are optional for a portable package-only check; omitted external checks are explicitly reported skipped. manifest.json and landing-paths.txt define this package only. No device, build, shared Git write or new experiment is involved.
