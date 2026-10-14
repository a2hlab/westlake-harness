import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path

SOURCE_SHA = 'b9089fe59f9049e993f92646161e0723496224a44436a2500087e2d05409e8f7'
RECOVERED_SHA = '3abcb0ab814c384fb023b639d8ca49451771a3e87c5fd2e5f0f91ba20850ab8c'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def restore(data):
    if digest(data) != SOURCE_SHA:
        raise ValueError('not the exact captured original APK member')
    recovered = data.decode('utf-8', errors='strict').encode('latin1', errors='strict')
    if recovered.decode('latin1').encode('utf-8') != data or digest(recovered) != RECOVERED_SHA:
        raise ValueError('not byte-exact reversible transform')
    if recovered[:4] != b'RIFF' or recovered[8:12] != b'WEBP' or struct.unpack_from('<I', recovered, 4)[0] + 8 != len(recovered):
        raise ValueError('invalid recovered RIFF')
    cursor = 12
    chunks = []
    while cursor < len(recovered):
        if cursor + 8 > len(recovered):
            raise ValueError('truncated chunk header')
        size = struct.unpack_from('<I', recovered, cursor + 4)[0]
        chunks.append(dict(type=recovered[cursor:cursor + 4].decode('ascii'), size=size))
        cursor += 8 + size + size % 2
        if cursor > len(recovered):
            raise ValueError('truncated chunk')
    if cursor != len(recovered):
        raise ValueError('not exact RIFF boundary')
    return recovered, chunks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    data = args.source.read_bytes()
    recovered, chunks = restore(data)
    args.out.mkdir(parents=True, exist_ok=False)
    webp = args.out / 'recovered.webp'
    png = args.out / 'icon.png'
    webp.write_bytes(recovered)
    ffmpeg = Path('/opt/homebrew/bin/ffmpeg')
    command = [str(ffmpeg), '-nostdin', '-v', 'error', '-i', str(webp), '-frames:v', '1', str(png)]
    conversion = subprocess.run(command, capture_output=True)
    if conversion.returncode != 0:
        raise ValueError('decoder/converter failed')
    decoded = []
    for path in [webp, png]:
        result = subprocess.run([str(ffmpeg), '-nostdin', '-v', 'error', '-i', str(path), '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgba', 'pipe:1'], capture_output=True)
        if result.returncode != 0 or not result.stdout or len(result.stdout) % 4:
            raise ValueError('RGBA decode failed')
        decoded.append(result.stdout)
    if decoded[0] != decoded[1]:
        raise ValueError('PNG conversion changed decoded pixels')
    width, height = struct.unpack_from('>II', png.read_bytes(), 16)
    result = dict(source_sha256=digest(data), source_bytes=len(data), source_member='res/d2.webp',
                  apk_sha256='3b6cb46847c99fb82537e7fa3f0527f4443c544fa8a8839588c5ce32e368b446',
                  transform='strict UTF8 decode -> Latin1 encode; inverse roundtrip exact',
                  recovered_webp_sha256=digest(recovered), recovered_bytes=len(recovered), chunks=chunks,
                  png_sha256=digest(png.read_bytes()), width=width, height=height,
                  rgba_sha256=digest(decoded[0]), rgba_bytes=len(decoded[0]), pixels_unchanged=True,
                  alpha_nonzero=sum(value > 0 for value in decoded[0][3::4]),
                  alpha_zero=sum(value == 0 for value in decoded[0][3::4]),
                  ffmpeg_sha256=digest(ffmpeg.read_bytes()), conversion_rc=conversion.returncode,
                  stdout=conversion.stdout.decode('utf8', errors='backslashreplace'),
                  stderr=conversion.stderr.decode('utf8', errors='backslashreplace'),
                  limitation='Recovers exactly available encoded bytes; not a reconstruction of artistic intent. Original low-resolution cyan/green pattern preserved; no drawing/scaling/recoloring.',
                  separate_from_eight_repaired_icons=True, execution_enabled=False)
    (args.out / 'receipts.json').write_text(json.dumps([dict(package='com.frequent.habits', **result)], indent=2) + '\n')
    (args.out / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
