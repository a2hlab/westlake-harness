#!/usr/bin/env python3
"""Static scan of the M2 (full-screen WebView) keys: where the page comes from and which WebView APIs the DEX names.

    m2_web_scan.py  -> evidence/m2-web-scan.json (+ table on stdout)

DEX string-table hits are an upper bound (a name in the string pool, not a proven call). Page source = assets/ web roots,
capacitor.config.json (androidScheme / server.url), and the start URL strings found in the DEX.
"""
import json
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'scripts/lab'))
import lab_paths  # noqa: E402

IN = lab_paths.inputs()
KEYS = {
    'cv2-ca-vaults-randomlydie': 'corpus-v2/app-inputs/cv2-ca-vaults-randomlydie',
    'cv2-com-degeder-yam': 'corpus-v2/app-inputs/cv2-com-degeder-yam',
    'cv2-com-paultirk-yatoo': 'corpus-v2/app-inputs/cv2-com-paultirk-yatoo',
    'cv2-timur-webrtc-check': 'corpus-v2/app-inputs/cv2-timur-webrtc-check',
    'fd-tutanota': 'apks/fdroid100/de.tutao.tutanota_396709.apk',
    'cv2-dev-obfusk-jiten-webview': 'corpus-v2/app-inputs/cv2-dev-obfusk-jiten-webview',
    'cv2-com-caniwebview-android': 'corpus-v2/app-inputs/cv2-com-caniwebview-android',
}
APIS = ['addJavascriptInterface', 'shouldInterceptRequest', 'evaluateJavascript', 'loadDataWithBaseURL', 'loadUrl',
        'WebViewAssetLoader', 'addWebMessageListener', 'postWebMessage', 'createWebMessageChannel', 'onPermissionRequest',
        'onShowFileChooser', 'setDomStorageEnabled', 'setJavaScriptEnabled', 'setMixedContentMode',
        'onRenderProcessGone', 'getUserMedia']
URL = re.compile(rb'(?:https?|file)://(?:localhost|appassets\.androidplatform\.net|android_asset)[\x21-\x7e]{0,60}')


def apk_of(rel):
    p = IN / rel
    if p.suffix == '.apk':
        return p
    apks = sorted(p.glob('*.apk'))
    return apks[0] if apks else None


def scan(apk):
    out = {'apk': str(apk.relative_to(IN)), 'web_roots': {}, 'capacitor': None, 'apis': {}, 'start_urls': []}
    with zipfile.ZipFile(apk) as z:
        names = z.namelist()
        for n in names:
            if n.startswith('assets/') and n.endswith(('.html', '.js', '.css')):
                root = '/'.join(n.split('/')[:2])
                out['web_roots'][root] = out['web_roots'].get(root, 0) + 1
        if 'assets/capacitor.config.json' in names:
            c = json.loads(z.read('assets/capacitor.config.json'))
            out['capacitor'] = {'androidScheme': (c.get('server') or {}).get('androidScheme', c.get('android', {}).get('scheme')),
                                'server_url': (c.get('server') or {}).get('url'), 'plugins': sorted((c.get('plugins') or {}))}
        dex = b''.join(z.read(n) for n in names if re.fullmatch(r'classes\d*\.dex', n))
    for a in APIS:
        out['apis'][a] = dex.count(a.encode())
    out['start_urls'] = sorted({m.decode() for m in URL.findall(dex)})[:8]
    return out


def main():
    res = {}
    for k, rel in KEYS.items():
        apk = apk_of(rel)
        res[k] = scan(apk) if apk else {'apk': None}
        r = res[k]
        roots = ', '.join(f'{a}({b})' for a, b in sorted(r.get('web_roots', {}).items(), key=lambda x: -x[1])[:3])
        hit = [a for a, n in r.get('apis', {}).items() if n]
        print(f'{k}: roots={roots or "-"} capacitor={r.get("capacitor")} apis={hit} urls={r.get("start_urls")}')
    (HERE / 'evidence').mkdir(exist_ok=True)
    (HERE / 'evidence/m2-web-scan.json').write_text(json.dumps(res, indent=1, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
