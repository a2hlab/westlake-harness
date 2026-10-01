"""Freeze scope and provider-only first-screen predictions without runtime results."""

import argparse
import base64
import csv
import gzip
import io
import json
from pathlib import Path

import scan_webview as scan

HERE = Path(__file__).resolve().parent
POLICY = {
    'de.koelle.christian.trickytripper': dict(short='trickytripper',
        role='startup changelog dialog plus later help dialog',
        first_screen='native-dialog-candidate-with-blank-WebView', t20='lit-webview-fallback',
        next_wall='no Chromium renderer; changelog HTML stays blank', confidence='medium-conditional',
        criterion='getProvider UOE disappears; native dialog title/buttons visible at t20, HTML absent; not functional-lit'),
    'com.knirirr.beecount': dict(short='beecount', role='startup WelcomeActivity changelog dialog',
        first_screen='native-dialog-candidate-with-blank-WebView', t20='lit-webview-fallback',
        next_wall='no Chromium renderer; changelog HTML stays blank', confidence='medium-conditional',
        criterion='WelcomeActivity getProvider UOE disappears; native changelog dialog title/buttons visible at t20, HTML absent'),
    'dev.obfusk.jiten_webview': dict(short='jiten-webview', role='startup XML WebView and setupWebView',
        first_screen='blocked-WebSettings-null', t20='dead', next_wall='WebSettings.setJavaScriptEnabled on null', confidence='high-conditional',
        criterion='provider UOE cleared; setupWebView dereferences null settings; terminal-first root and signed t20 separate'),
    'com.caniwebview.android': dict(short='caniwebview', role='startup NavHost WebViewFragment plus fullscreen WebViewActivity',
        first_screen='blocked-WebSettings-null', t20='dead', next_wall='Kotlin checkNotNullExpressionValue for WebSettings in WebViewFragment.onViewCreated/onResume', confidence='medium-conditional',
        criterion='XML inflation provider UOE cleared; null settings check or dereference terminates; screenshot remains non-lit'),
    'eu.dfdx.jslab': dict(short='jslab', role='startup ViewPager2 first PlaceholderFragment',
        first_screen='blocked-WebSettings-null', t20='dead', next_wall='WebSettings.setJavaScriptEnabled in PlaceholderFragment.onCreateView', confidence='high-conditional',
        criterion='FragmentMainBinding inflation provider UOE cleared; first Fragment settings call terminates; signed t20 non-lit'),
    'com.stoutner.privacybrowser.standard': dict(short='privacybrowser', role='startup MainWebViewActivity static WebView call and user-agent probe',
        first_screen='blocked-WebSettings-null', t20='dead', next_wall='WebSettings.getUserAgentString on null in MainWebViewActivity.onCreate', confidence='medium-conditional',
        criterion='enableSlowWholeDocumentDraw provider UOE cleared; WebSettings user-agent probe remains null; browser HTML cannot render'),
    'com.degeder.yam': dict(short='yam', role='startup Capacitor WebView/bridge, not later page only',
        first_screen='blocked-or-unknown-Capacitor-bridge-null', t20='dead', next_wall='Capacitor bridge null onStart persists; settings-null is another conditional blocker if initialization reaches bridge.K', confidence='medium-conditional',
        criterion='Do not claim getProvider as the observed first fatal; bridge j.H null onStart is baseline; unchanged or new settings failure and t20 non-lit'),
}
FIELDS = ['key', 'package', 'apk_sha256', 'webview_scope', 'first_screen_prediction', 'predicted_t20',
          'provider_checkpoint', 'next_wall_candidate', 'confidence', 'criterion', 'runtime_jar_sha256']


def load_facts():
    return json.loads(gzip.decompress(base64.b64decode((HERE/'facts.json.gz.b64').read_bytes())))


def build(facts, evidence):
    if len(facts['apps']) != 7 or {app['package'] for app in facts['apps']} != scan.PACKAGES:
        raise ValueError('Incomplete seven-key cohort')
    rows = []
    for app in sorted(facts['apps'], key=lambda row: row['key']):
        calibration = evidence['calibrations'][app['key']]
        startup = [site for site in app['webview_sites'] if any(context['tier']=='startup-chain' for context in site['contexts'])]
        observed_provider = any('WebViewFactory.getProvider' in row.get('message','')
            for row in calibration['first_fatal'].get('root',{}).get('frames',[]))
        scope = 'startup-required' if startup or observed_provider else 'unresolved-callback-or-page'
        policy = POLICY[app['package']]
        rows.append(dict(key=app['key'], package=app['package'], apk_sha256=app['apk_sha256'],
            short=policy['short'], webview_scope=scope, role=policy['role'],
            first_screen_prediction=policy['first_screen'], predicted_t20=policy['t20'],
            provider_checkpoint='conditional-pass-not-observed-fatal' if app['package']=='com.degeder.yam' else 'conditional-pass',
            next_wall_candidate=policy['next_wall'], confidence=policy['confidence'], criterion=policy['criterion'],
            runtime_jar_sha256=evidence['candidate_runtime']['sha256'],
            startup_witnesses=startup, layout_resources=[{name:row[name] for name in ['resource','name','member','sha256','tags']} for row in app['layouts']],
            later_activity_sites=[site for site in app['webview_sites'] if any(context['tier']=='later-activity-lifecycle' for context in site['contexts'])],
            unanchored_or_callback_sites=[site for site in app['webview_sites'] if not site['contexts']],
            calibration_ref='provider-evidence.json/calibrations/'+app['key'],
            observed_first_fatal=calibration['first_fatal']['root'],
            evidence_ref='facts.json.gz.b64/app='+app['key'],
            limits='Later-page references do not cancel startup demand; Fragment/virtual dispatch and UI ownership are not established by bounded call graph alone'))
    return dict(schema='webview-startup-predictions-v1', rows=rows,
        counts=dict(keys=7, dex_members=sum(len(app['dex']) for app in facts['apps']),
            webview_and_settings_calls=sum(app['counts']['webview_sites'] for app in facts['apps']),
            startup_required=sum(row['webview_scope']=='startup-required' for row in rows),later_only=0,
            native_chrome_fallback_candidates=2,settings_null_candidates=4,bridge_null_or_unknown_candidates=1,
            predicted_functional_lit=0,observed_provider_fatal=6),
        conditions=['No real Chromium provider, seed succeeds and nested proxies can be created',
            'Same selected APKs and equivalent launch/data branch as prior diagnostics',
            'The candidate is U8 J9 87fd463d carrying the J8 mechanism; do not substitute J8 6895b9e4',
            'Other U8 repairs and independent window failures can move the actual first fatal earlier or later'],
        rule='Whole DEX + WebView subclass ancestry + all WebView layouts + inherited launch lifecycle + terminal-first PID calibrations. Unknown callback dispatch is not a later-page proof.',
        baseline='Old cv2 U7 signed results remain unchanged; diagnostic hilog is calibration only; no U8 results used',
        visual_rule='Native dialog chrome with blank embedded HTML is lit-webview-fallback, never functional-lit',
        source=dict(scanner_dependencies=facts['scanner_dependencies'], audit_dependencies=evidence['audit_dependencies'],
            facts_sha256=scan.b10.digest((HERE/'facts.json.gz.b64').read_bytes()),
            provider_evidence_sha256=scan.b10.digest((HERE/'provider-evidence.json').read_bytes()),
            generator_sha256=scan.b10.digest(Path(__file__).read_bytes())))


def generate():
    facts = load_facts()
    evidence = json.loads((HERE/'provider-evidence.json').read_text())
    for path, pin in {**facts['scanner_dependencies'],**evidence['audit_dependencies']}.items():
        if scan.b10.digest((scan.ROOT/path).read_bytes()) != pin:
            raise ValueError('Scanner dependency drift: '+path)
    return build(facts, evidence)


def csv_text(result):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, FIELDS, lineterminator='\n')
    writer.writeheader()
    for row in result['rows']:
        writer.writerow({field:row[field] for field in FIELDS})
    return stream.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = generate()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/'results.json').write_text(json.dumps(result, sort_keys=True, indent=2)+'\n')
    (args.output/'PREDICTIONS.csv').write_text(csv_text(result))
    print(result['counts'])


if __name__ == '__main__':
    main()
