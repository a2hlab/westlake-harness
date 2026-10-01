"""Read-only, bounded tracked-source searches; stdout is the audit receipt."""

import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
TREES = {
    'Westlake': 'vm-copies/westlake-current',
    '00.Workspace': '00.Workspace',
    'real-work': '01.OH61AOSP16/real-work',
}
PATTERNS = {
    'bridge': 'resolve_oh_wm_funcs|dl_iterate_phdr|dladdr|dlns_inherit',
    'bitmap': 'nativeGetColorSpace|Bitmap_getColorSpace|ColorSpace.*getNativeInstance|nativeCreate.*ColorSpace',
    'abort': 'android_set_abort_message',
    'audio': 'slCreateEngine',
    'media': 'AMediaCodec_create|AMediaExtractor_new|AMediaFormat_new',
    'account': 'new AccountManager|AccountManager.class|ACCOUNT_SERVICE',
    'theme': 'Theme.AppCompat|windowActionBar|applyTheme|setTheme',
    'webview': 'WebViewFactory|getWebViewClassLoader|WebViewUpdateServiceAdapter',
    'map': 'MapInfoLayer|ColorMatrix\\(ColorMatrix',
    'datasource': 'DataSourceModule|SessionMixin|CountryPreference|pa0.G',
    'zlib': 'libz.so|__gnu_strerror_r|android_dlopen_ext',
}


def collect():
    workspaces = Path(os.environ.get('WORKSPACES', ROOT.parent))
    receipt = dict(status='bounded-local-source-search-not-global-absence', repositories={}, searches=[])
    for name, relative in TREES.items():
        tree = workspaces / relative
        commit = subprocess.check_output(['git', '-C', str(tree), 'rev-parse', 'HEAD']).decode().strip()
        receipt['repositories'][name] = dict(path=relative, commit=commit)
        for topic, pattern in PATTERNS.items():
            command = ['git', '-C', str(tree), 'grep', '-n', '-I', '-E', pattern, commit, '--',
                       '*.c', '*.cc', '*.cpp', '*.h', '*.java', '*.sh', '*.py']
            result = subprocess.run(command, capture_output=True)
            if result.returncode not in (0, 1):
                raise RuntimeError(result.stderr.decode())
            lines = result.stdout.decode(errors='replace').splitlines()
            receipt['searches'].append(dict(repository=name, topic=topic, pattern=pattern,
                                            returncode=result.returncode, match_lines=len(lines),
                                            output_sha256=hashlib.sha256(result.stdout).hexdigest(),
                                            examples=lines[:32], omitted=max(0, len(lines)-32)))
    return receipt


if __name__ == '__main__':
    print(json.dumps(collect(), ensure_ascii=False, sort_keys=True, indent=2))
