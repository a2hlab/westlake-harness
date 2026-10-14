import argparse
import csv
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from render_known_icons import ANDROID, color, vector_svg

PACKAGES = ('com.kaajjo.libresudoku', 'com.lcdcode.moodcairns', 'com.paperknifeplus.app', 'com.groce.app', 'org.fossify.calendar')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def clipped_vector(xml):
    root = ET.fromstring(xml)
    if not any(element.tag == 'clip-path' for element in root.iter()):
        return vector_svg(xml)
    if root.tag != 'vector':
        raise ValueError('clip input is not vector')
    width = root.get(ANDROID + 'viewportWidth')
    height = root.get(ANDROID + 'viewportHeight')
    outer = ET.Element('svg', xmlns='http://www.w3.org/2000/svg', width='256', height='256', viewBox=f'0 0 {width} {height}')
    definitions = ET.SubElement(outer, 'defs')
    count = 0

    def children(source, parent):
        nonlocal count
        active = parent
        for child in source:
            attrs = {key.removeprefix(ANDROID): value for key, value in child.attrib.items()}
            if child.tag == 'clip-path':
                if set(attrs) - {'pathData', 'fillType', 'name'}:
                    raise ValueError('unsupported clip attributes')
                count += 1
                clip_id = 'source-clip-' + str(count)
                definition = ET.SubElement(definitions, 'clipPath', id=clip_id, clipPathUnits='userSpaceOnUse')
                ET.SubElement(definition, 'path', d=attrs['pathData'], **{'clip-rule': 'evenodd' if attrs.get('fillType') in ('1', 'evenOdd') else 'nonzero'})
                active = ET.SubElement(active, 'g', **{'clip-path': 'url(#' + clip_id + ')'})
            elif child.tag == 'group':
                if set(attrs) - {'translateX', 'translateY', 'scaleX', 'scaleY', 'name'}:
                    raise ValueError('unsupported group attributes')
                transform = f"translate({attrs.get('translateX', '0')} {attrs.get('translateY', '0')}) scale({attrs.get('scaleX', '1')} {attrs.get('scaleY', '1')})"
                group = ET.SubElement(active, 'g', transform=transform)
                children(child, group)
            elif child.tag == 'path':
                container = ET.Element('vector', root.attrib)
                copied = ET.fromstring(ET.tostring(child))
                cap = copied.attrib.pop(ANDROID + 'strokeLineCap', None)
                if cap is not None and cap not in ('0', '1', '2', 'butt', 'round', 'square'):
                    raise ValueError('unsupported line cap')
                container.append(copied)
                rendered = ET.fromstring(vector_svg(ET.tostring(container)))
                for path in rendered:
                    if cap is not None:
                        path.set('stroke-linecap', {'0': 'butt', '1': 'round', '2': 'square'}.get(cap, cap))
                    active.append(path)
            else:
                raise ValueError('unsupported clipped vector element')
    children(root, outer)
    return ET.tostring(outer, encoding='utf-8', xml_declaration=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--manifest-sha', required=True)
    parser.add_argument('--history', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    raw = args.manifest.read_bytes()
    if sha(raw) != args.manifest_sha:
        raise ValueError('inventory drift')
    manifest = json.loads(raw)
    history = {row['key']: row for row in csv.DictReader(args.history.open())}
    args.out.mkdir(parents=True, exist_ok=False)
    from loguru import logger
    logger.remove()
    from androguard.core.apk import APK
    from androguard.core.axml import AXMLPrinter
    receipts = []
    renderer = Path('/opt/homebrew/bin/rsvg-convert')
    for package in PACKAGES:
        app = next(app for app in manifest['apps'] if app['package'] == package)
        prior = history[app['key']]
        if app['disposition'] != 'keep' or app['source_apk_sha256'] != prior['apk_sha256']:
            raise ValueError('not retained exact APK')
        apk_path = Path(app['source_apk'])
        if sha(apk_path.read_bytes()) != app['source_apk_sha256']:
            raise ValueError('APK bytes drift')
        apk = APK(str(apk_path))
        if int(apk.get_attribute_value('application', 'icon')[1:], 16) != int(prior['icon_id'], 16):
            raise ValueError('manifest icon ID drift')
        resources = apk.get_android_resources()
        selected = prior['selected_file']
        raw_xml = apk.get_file(selected)
        xml = AXMLPrinter(raw_xml).get_xml()
        document = ET.fromstring(xml)
        layers = []
        provenance = []
        if document.tag == 'vector':
            layers = [ET.fromstring(clipped_vector(xml))]
        elif document.tag == 'adaptive-icon':
            for tag in ('background', 'foreground'):
                ref = document.find(tag).get(ANDROID + 'drawable')
                candidates = [value for config, value in resources.get_resolved_res_configs(int(ref[1:], 16)) if not config.get_qualifier()]
                if len(candidates) != 1:
                    raise ValueError('ambiguous default adaptive layer')
                value = candidates[0]
                if value.startswith('#'):
                    fill, alpha = color(value)
                    layer = ET.Element('svg', xmlns='http://www.w3.org/2000/svg', viewBox='0 0 108 108')
                    ET.SubElement(layer, 'rect', width='108', height='108', fill=fill, **{'fill-opacity': str(alpha)})
                    provenance.append(dict(layer=tag, resource_ref=ref, color=value))
                else:
                    compiled = apk.get_file(value)
                    decoded = AXMLPrinter(compiled).get_xml()
                    node = ET.fromstring(decoded)
                    if node.tag == 'shape':
                        if len(node) != 1 or node[0].tag != 'solid':
                            raise ValueError('unsupported background shape')
                        fill, alpha = color(node[0].get(ANDROID + 'color'))
                        layer = ET.Element('svg', xmlns='http://www.w3.org/2000/svg', viewBox='0 0 108 108')
                        ET.SubElement(layer, 'rect', width='108', height='108', fill=fill, **{'fill-opacity': str(alpha)})
                    else:
                        layer = ET.fromstring(clipped_vector(decoded))
                    (args.out / (package + '.' + tag + '.xml')).write_bytes(decoded)
                    provenance.append(dict(layer=tag, resource_ref=ref, member=value, compiled_sha256=sha(compiled), decoded_xml_sha256=sha(decoded)))
                layers.append(layer)
        else:
            raise ValueError('unsupported launcher resource')
        output = ET.Element('svg', xmlns='http://www.w3.org/2000/svg', width='256', height='256', viewBox='0 0 108 108')
        for layer in layers:
            layer.set('x', '0')
            layer.set('y', '0')
            layer.set('width', '108')
            layer.set('height', '108')
            output.append(layer)
        svg = ET.tostring(output, encoding='utf-8', xml_declaration=True)
        svg_path = args.out / (package + '.svg')
        png_path = args.out / (package + '.png')
        svg_path.write_bytes(svg)
        (args.out / (package + '.xml')).write_bytes(xml)
        result = subprocess.run([str(renderer), '-o', str(png_path), str(svg_path)], capture_output=True)
        if result.returncode != 0:
            raise ValueError('rasterization failed')
        receipts.append(dict(package=package, key=app['key'], apk_sha256=app['source_apk_sha256'], selected=selected,
                             manifest_icon_id=prior['icon_id'], compiled_selected_sha256=sha(raw_xml), decoded_xml_sha256=sha(xml),
                             layers=provenance, svg_sha256=sha(svg), png_sha256=sha(png_path.read_bytes()),
                             renderer_sha256=sha(renderer.read_bytes()), renderer_rc=result.returncode,
                             stdout=result.stdout.decode('utf8', errors='backslashreplace'), stderr=result.stderr.decode('utf8', errors='backslashreplace'),
                             status='SOURCE_DERIVED_CANDIDATE_PENDING_ROOT_VISUAL_REVIEW'))
    (args.out / 'receipts.json').write_text(json.dumps(receipts, indent=2) + '\n')


if __name__ == '__main__':
    main()
