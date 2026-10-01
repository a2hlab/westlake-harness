"""Retrospective conservative contracts, not runtime fatal determinations."""

CONTENT_APIS = {'<init>', 'loadUrl', 'loadData', 'loadDataWithBaseURL',
                'evaluateJavascript', 'getSettings', 'setWebViewClient', 'setWebChromeClient'}


def webview_content(owner, name):
    return owner == 'Landroid/webkit/WebView;' and name in CONTENT_APIS


def candidates(row, precise):
    output = []
    for call in precise['webview_content']:
        output.append(dict(family='webview-content-contract', layer='JAR/window',
                           evidence=call, scope='whole-APK; execution-and-branch-unknown'))
    for candidate in row['first_wall_candidates']:
        if candidate['family'] in {'secondary-activity-window-session', 'koin-init-or-use'} and candidate['startup_occurrences']:
            output.append(dict(family='startup-activity-transition-contract' if candidate['family'].startswith('secondary') else 'startup-koin-contract',
                               layer='window/first-frame' if candidate['family'].startswith('secondary') else 'JAR',
                               evidence=candidate['evidence'], scope='bounded-exact-target-startup; not-runtime-proof'))
    return output


def revise(row, precise):
    if row['apk_sha256'] != precise['apk_sha256'] or row['package'] != precise['package']:
        raise ValueError('APK profile identity mismatch')
    alerts = candidates(row, precise)
    return dict(key=row['key'], package=row['package'], apk_sha256=row['apk_sha256'],
                v1_t20=row['t20'], t20=row['t20'],
                abstention_experiment_t20='unknown' if alerts else row['t20'],
                first_wall='unknown', checkpoint='unknown', candidates=alerts,
                change='candidate-coverage-added' if alerts else 'unchanged',
                interpretation='Candidate-only default. Blanket contract abstention is an unpromoted experiment; references do not establish fatal causes or screen ownership')
