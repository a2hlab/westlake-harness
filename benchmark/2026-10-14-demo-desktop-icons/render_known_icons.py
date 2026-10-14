import argparse
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ANDROID = '{http://schemas.android.com/apk/res/android}'
SVG = 'http://www.w3.org/2000/svg'
TARGETS = {
    'app.varlorg.unote': ('res/r2.xml', None, None),
    'com.alxgnon.postwriter': ('res/mipmap/ic_launcher.xml', 0x7f050044, 0x7f070062),
    'org.tasks': ('res/me.xml', 0x7f060027, 0x7f0800ad),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def color(value):
    if not value.startswith('#') or len(value) not in (7, 9):
        raise ValueError('unresolved color')
    int(value[1:], 16)
    return (value if len(value) == 7 else '#' + value[3:],
            1.0 if len(value) == 7 else int(value[1:3], 16) / 255)


def vector_svg(xml, background=None):
    root = ET.fromstring(xml)
    if root.tag != 'vector':
        raise ValueError('not a vector')
    width = float(root.attrib[ANDROID + 'viewportWidth'])
    height = float(root.attrib[ANDROID + 'viewportHeight'])
    outer = ET.Element('svg', xmlns=SVG, width='256', height='256', viewBox=f'0 0 {width} {height}')
    if background is not None:
        fill, alpha = color(background)
        ET.SubElement(outer, 'rect', width=str(width), height=str(height), fill=fill, **{'fill-opacity': str(alpha)})
    tint = root.get(ANDROID + 'tint')

    def convert(node, parent):
        attrs = {key.removeprefix(ANDROID): value for key, value in node.attrib.items()}
        if node.tag == 'group':
            allowed = {'translateX', 'translateY', 'scaleX', 'scaleY', 'name'}
            if set(attrs) - allowed:
                raise ValueError('unsupported vector group transform')
            transform = f"translate({attrs.get('translateX', '0')} {attrs.get('translateY', '0')}) scale({attrs.get('scaleX', '1')} {attrs.get('scaleY', '1')})"
            child = ET.SubElement(parent, 'g', transform=transform)
            for entry in node:
                convert(entry, child)
        elif node.tag == 'path':
            allowed = {'pathData', 'fillColor', 'fillAlpha', 'strokeColor', 'strokeAlpha', 'strokeWidth', 'fillType', 'name'}
            if set(attrs) - allowed:
                raise ValueError('unsupported path attribute')
            result = {'d': attrs['pathData']}
            for kind in ('fill', 'stroke'):
                value = attrs.get(kind + 'Color', '#FF000000' if kind == 'fill' else '#00000000')
                base, alpha = color(tint if tint and alpha_nonzero(value) else value)
                result[kind] = base
                result[kind + '-opacity'] = str(alpha * float(attrs.get(kind + 'Alpha', '1')))
            result['stroke-width'] = attrs.get('strokeWidth', '0')
            result['fill-rule'] = 'evenodd' if attrs.get('fillType') in ('1', 'evenOdd') else 'nonzero'
            ET.SubElement(parent, 'path', result)
        else:
            raise ValueError('unsupported vector element')

    for entry in root:
        convert(entry, outer)
    return ET.tostring(outer, encoding='utf-8', xml_declaration=True)


def alpha_nonzero(value):
    return color(value)[1] != 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--manifest-sha', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    raw = args.manifest.read_bytes()
    if digest(raw) != args.manifest_sha:
        raise ValueError('inventory changed')
    args.out.mkdir(parents=True, exist_ok=False)
    from loguru import logger
    logger.remove()
    from androguard.core.apk import APK
    from androguard.core.axml import AXMLPrinter
    manifest = json.loads(raw)
    renderer = Path('/opt/homebrew/bin/rsvg-convert')
    receipts = []
    for package, (selected, bg_id, fg_id) in TARGETS.items():
        app = next(app for app in manifest['apps'] if app['package'] == package)
        if app['disposition'] not in ('keep', 'protect'):
            raise ValueError('package outside inventory')
        apk_path = Path(app['source_apk'])
        if digest(apk_path.read_bytes()) != app['source_apk_sha256']:
            raise ValueError('APK changed')
        apk = APK(str(apk_path))
        if apk.get_package() != package or apk.get_app_icon() != selected:
            raise ValueError('manifest selection changed')
        resources = apk.get_android_resources()
        background = None
        vector_path = selected
        if bg_id is not None:
            adaptive = ET.fromstring(AXMLPrinter(apk.get_file(selected)).get_xml())
            if adaptive.tag != 'adaptive-icon':
                raise ValueError('not the pinned adaptive icon')
            for tag, resource_id in [('background', bg_id), ('foreground', fg_id)]:
                element = adaptive.find(tag)
                if element is None or element.get(ANDROID + 'drawable') != f'@{resource_id:08X}':
                    raise ValueError('adaptive layer reference changed')
            def exact_default(resource_id):
                candidates = [value for config, value in resources.get_resolved_res_configs(resource_id) if not config.get_qualifier()]
                if len(candidates) != 1:
                    raise ValueError('ambiguous default resource')
                return candidates[0]
            background = exact_default(bg_id)
            vector_path = exact_default(fg_id)
        xml = AXMLPrinter(apk.get_file(vector_path)).get_xml()
        svg = vector_svg(xml, background)
        xml_path = args.out / (package + '.xml')
        svg_path = args.out / (package + '.svg')
        png_path = args.out / (package + '.png')
        xml_path.write_bytes(xml)
        svg_path.write_bytes(svg)
        result = subprocess.run([str(renderer), '-o', str(png_path), str(svg_path)], capture_output=True)
        if result.returncode != 0:
            raise ValueError('renderer failed')
        receipts.append(dict(package=package, apk_sha256=app['source_apk_sha256'], selected=selected,
                             vector=vector_path, compiled_vector_sha256=digest(apk.get_file(vector_path)),
                             decoded_xml_sha256=digest(xml), background=background,
                             svg_sha256=digest(svg), png_sha256=digest(png_path.read_bytes()),
                             renderer_sha256=digest(renderer.read_bytes()), renderer_rc=0,
                             argv=[str(renderer), '-o', png_path.name, svg_path.name],
                             stdout=result.stdout.decode('utf-8', errors='backslashreplace'),
                             stderr=result.stderr.decode('utf-8', errors='backslashreplace'),
                             status='OFFLINE_CANDIDATE_REQUIRES_VISUAL_AND_DEVICE_CACHE_REVIEW'))
    (args.out / 'receipts.json').write_text(json.dumps(receipts, indent=2) + '\n')


if __name__ == '__main__':
    main()
