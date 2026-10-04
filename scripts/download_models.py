"""Build-time model fetcher; the desktop application never calls this tool."""
import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'resources'


def ensure_resources(verify_only=False):
    entries = json.loads((ROOT / 'model-manifest.json').read_text(encoding='utf-8'))
    for entry in entries:
        path = (ROOT / entry['file']).resolve()
        if not path.is_relative_to(ROOT.resolve()):
            raise ValueError('Resource path must stay in resources')
        if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256']:
            continue
        if verify_only:
            raise RuntimeError(f'Missing or invalid resource: {entry["file"]}')
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_suffix(path.suffix + '.part')
        digest = hashlib.sha256()
        request = urllib.request.Request(entry['url'], headers={'User-Agent': 'AI-Upscale-King-build'})
        try:
            with urllib.request.urlopen(request, timeout=90) as response, partial.open('wb') as output:
                while block := response.read(1024 * 1024):
                    digest.update(block); output.write(block)
            if digest.hexdigest() != entry['sha256'] or partial.stat().st_size != entry['bytes']:
                raise RuntimeError(f'Resource checksum mismatch: {entry["file"]}')
            partial.replace(path)
        finally:
            partial.unlink(missing_ok=True)
    print('Verified pinned models and upstream notices')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--verify-only', action='store_true')
    ensure_resources(parser.parse_args().verify_only)
