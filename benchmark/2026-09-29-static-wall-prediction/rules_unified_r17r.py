"""Framework audio startup requirements, independent of app names and outcomes.

The family has TWO submechanisms, not a common fix. A reference is a conditional
requirement, never proof of startup reachability or missing runtime support.
"""
from scan_apps import INVOKE

FAMILY = 'framework-audio-native-closure'


def requirement(owner, name, signature):
    if ((owner == 'android/media/SoundPool$Builder' and name == 'build'
         and signature == '()Landroid/media/SoundPool;') or
        (owner == 'android/media/SoundPool' and name == '<init>')):
        return 'soundpool-declared-library'
    if (owner == 'android/media/AudioAttributes$Builder'
        and name in {'setLegacyStreamType', 'setInternalLegacyStreamType'}
        and signature == '(I)Landroid/media/AudioAttributes$Builder;'):
        return 'audio-product-strategy-jni'
    if (owner == 'android/media/audiopolicy/AudioProductStrategy'
        and name in {'getAudioProductStrategies', 'native_list_audio_product_strategies'}):
        return 'audio-product-strategy-jni'
    return None


def inspect_method(method, dex, insns):
    """Compatible with the existing DEX instruction/reachability scanner."""
    rows = []
    for offset, line, text in insns:
        match = INVOKE.search(text)
        if not match:
            continue
        _, _, owner, name, signature = match.groups()
        sub = requirement(owner, name, signature)
        if sub:
            rows.append(dict(family=FAMILY, submechanism=sub, method=method,
                             dex=dex, offset=offset, line=line, instruction=text,
                             target=owner+'.'+name+signature,
                             verdict='conditional-runtime-requirement',
                             missing_implementation='unknown',
                             stub_ok='unknown', needs_real='unknown'))
    return rows
