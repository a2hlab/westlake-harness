# Corpus-v2 APK scanner v2: precise contract candidates

v1 grouped all `android/webkit` calls by a prefix and retained at most three
examples; a MimeTypeMap representative concealed actual content WebView calls.
The new rule preserves exact owner/name/descriptor counts and up to three
DEX/member/method/offset/line witnesses per API. Whole-APK presence still does
not establish startup execution, a failed branch or a fatal point.

- Inputs: the unchanged 100 SHA-bound APKs, independently re-read 136 DEX
  members with the same pinned dexdump binary; every member hash matches v1.
- `precise-profile.json.gz.b64` contains all 100 profiles, exact content API
  witnesses, tool SHA and collector dependencies; there are 15 content-call apps.
- `rules.py` adds `webview-content-contract`, promotes the existing bounded
  Activity jump evidence to an explicit transition contract, and exposes bounded
  Koin initialization/use. Candidate cohorts contain 15/32/1 apps, 46 distinct.
- Direct WebView content APIs: constructor, loadUrl/loadData/loadDataWithBaseURL,
  evaluateJavascript, getSettings, setWebViewClient/setWebChromeClient.
  MimeTypeMap, Linkify, WebSettings utility calls and unrelated same-named classes
  are not content matches. Subclass-owned/reflected/obfuscated calls remain unknown.
- Startup transitions and Koin use the unchanged v1 three-hop exact-target graph;
  virtual dispatch, later callbacks, branch outcomes and actual window ownership
  remain unresolved. No generic getSystemService call becomes a hard gate.
- Default t20 is unchanged **73 own-ui / 27 unknown**. First wall and checkpoint
  stay unknown. New evidence is candidate reporting, not an admission gate.
- `abstention_experiment_t20` is a deliberately unpromoted sensitivity analysis:
  blanket demotion gives 38 own-ui / 62 unknown, removes 27 signed-lit positives
  and worsens positive precision. See `../../2026-10-01-cv2-scoring/FEEDBACK.json`
  for the label-based ablation, which is never an input to rules/report.
- This is retrospective feedback, **not a new frozen or held-out prediction**.
  All v1 code/CSV/evidence is preserved byte for byte. No positive upgrades by key
  or observed labels, no claim that these APIs caused an original termination.

```sh
python3 benchmark/2026-10-01-corpus-v2/apk-scan-v2/collect.py \
  --apks "$WORKSPACES/westlake-inputs/corpus-v2/apks" \
  --dexdump "$HOME/Library/Android/sdk/build-tools/37.0.0/dexdump" \
  --output /tmp/cv2-precise-profile.json
python3 benchmark/2026-10-01-corpus-v2/apk-scan-v2/report.py --output /tmp/cv2-static-v2
python3 benchmark/2026-10-01-cv2-scoring/test_score.py FeedbackTests ReplayTests
```

The collection output is gzip-compressed deterministically (mtime=0) and base64
encoded for compact checked-in replay. All detector dependencies and DEX hashes
are enforced by report.py. Handoff and completed gates are in the scoring directory.
