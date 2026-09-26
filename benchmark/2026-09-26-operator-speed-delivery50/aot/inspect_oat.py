"""Read ELF64 sections and the source-matched ART 247 OatHeader (no oatdump needed)."""
import argparse
import json
import pathlib
import struct


def inspect(path):
    data = path.read_bytes()
    if data[:6] != b'\x7fELF\x02\x01':
        raise ValueError('Expected little-endian ELF64')
    machine = struct.unpack_from('<H', data, 18)[0]
    offset = struct.unpack_from('<Q', data, 40)[0]
    width, count, names_index = struct.unpack_from('<HHH', data, 58)
    headers = [struct.unpack_from('<IIQQQQIIQQ', data, offset + i * width)
               for i in range(count)]
    names_header = headers[names_index]
    names = data[names_header[4]:names_header[4] + names_header[5]]
    sections = {}
    for header in headers:
        name = names[header[0]:].split(b'\0', 1)[0].decode()
        sections[name] = {'offset': header[4], 'bytes': header[5]}
    start = sections['.rodata']['offset']
    if data[start:start + 8] != b'oat\n247\0':
        raise ValueError('Expected OAT 247 at .rodata start')
    # runtime/oat/oat.h: magic/version then fifteen 32-bit fields.
    fields = struct.unpack_from('<15I', data, start + 8)
    kv = data[start + 68:start + 68 + fields[14]].split(b'\0')
    if kv[-1] != b'' or len(kv) % 2 != 1:
        raise ValueError('Malformed OatHeader key/value store')
    metadata = {kv[i].decode(): kv[i + 1].decode() for i in range(0, len(kv)-1, 2)}
    return {'path': str(path), 'elf_machine': machine, 'oat_version': '247',
            'instruction_set': fields[1], 'dex_file_count': fields[3],
            'metadata': metadata, 'sections': sections,
            'device_accepted': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('file', type=pathlib.Path)
    args = parser.parse_args()
    print(json.dumps(inspect(args.file), indent=2))
