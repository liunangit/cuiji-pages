#!/usr/bin/env python3
"""Create an offline Cuiji single dish packet; see docs/菜品分享协议.md."""
import argparse
import json
import pathlib
import urllib.parse
import zipfile

LIMIT = 50 * 1024 * 1024
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--title', required=True)
text = parser.add_mutually_exclusive_group(required=True)
text.add_argument('--text')
text.add_argument('--text-file', type=pathlib.Path)
parser.add_argument('--source')
parser.add_argument('--image', action='append', default=[], type=pathlib.Path)
parser.add_argument('--output', required=True, type=pathlib.Path)
args = parser.parse_args()
body = args.text_file.read_text(encoding='utf-8') if args.text_file else args.text
if not args.title.strip() or len(args.title.strip()) > 200:
    parser.error('Title must be nonempty and at most 200 Unicode code points (conservative producer limit).')
if len(body.encode('utf-8')) > 100_000 or len(args.image) > 6:
    parser.error('Text exceeds 100000 UTF-8 bytes or more than 6 images.')
if args.output.suffix.lower() != '.cuijidish':
    parser.error('Output must end in .cuijidish.')
if args.source:
    source = urllib.parse.urlsplit(args.source)
    if len(args.source.encode('utf-8')) > 4096 or source.scheme not in ('http', 'https') or not source.hostname or source.username is not None or source.password is not None:
        parser.error('Source must be a HTTP/HTTPS URL without credentials.')
if not (body.strip() or args.image or args.source):
    parser.error('Provide text, image or source in addition to title.')
images = []
for index, path in enumerate(args.image, 1):
    ext = path.suffix.lower().lstrip('.')
    if ext not in ('jpg', 'jpeg', 'png', 'heic', 'heif', 'webp', 'gif', 'tif', 'tiff', 'bmp'):
        parser.error(f'Unsupported image extension: {path}')
    if path.stat().st_size > 20 * 1024 * 1024:
        parser.error(f'Image exceeds 20 MiB: {path}')
    images.append((f'images/{index}.{ext}', path.read_bytes()))
manifest = {'format': 'com.nanliu.cuiji.dish', 'version': 1, 'title': args.title.strip(), 'text': body, 'images': [name for name, _ in images]}
if args.source:
    manifest['sourceURL'] = args.source
metadata = json.dumps(manifest, ensure_ascii=False, indent=2).encode('utf-8')
# Include ZIP directory/header overhead in the same total limit used by iOS.
if len(metadata) + sum(len(data) for _, data in images) + 4096 > LIMIT:
    parser.error('Package exceeds 50 MiB.')
with zipfile.ZipFile(args.output, 'w', compression=zipfile.ZIP_STORED) as archive:
    archive.writestr('manifest.json', metadata)
    for name, data in images:
        archive.writestr(name, data)
print(f'Created {args.output} ({args.output.stat().st_size} bytes). iOS will validate image contents on import.')
