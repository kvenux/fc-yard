"""Install hash-locked emulator cores or the optional generated Contra video."""
import argparse
import hashlib
import json
import os
import platform
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def download(url, destination, expected):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, dir=destination.parent) as f:
        temporary = Path(f.name)
    try:
        urllib.request.urlretrieve(url, temporary)
        if digest(temporary) != expected:
            raise ValueError(f'Download checksum mismatch: {url}')
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check', action='store_true')
    p.add_argument('--video', action='store_true', help='Install only the optional Contra replay MP4')
    args = p.parse_args()
    lock = json.loads((ROOT / 'tools/cores-lock.json').read_text())
    base = f"https://github.com/{lock['repository']}/releases/download/{lock['release']}/"
    if args.video:
        meta = json.loads((ROOT / 'contra/runs/latest-video.json').read_text())
        destination = ROOT / 'contra/runs' / meta['video']
        if destination.exists() and digest(destination) == meta['videoSha256']:
            print('Contra video already verified'); return
        download(base + 'full-clear-audio.mp4', destination, meta['videoSha256'])
        print('Contra video installed and verified'); return
    if args.check:
        registry = json.loads((ROOT / 'games.json').read_text())
        failed = False
        for name, game in registry['games'].items():
            if 'rom' not in game: continue
            proof = json.loads((ROOT / game['proof']).read_text())
            for kind in ['rom', 'core']:
                path = ROOT / game[kind]
                status = 'missing' if not path.exists() else 'OK' if digest(path) == proof[kind+'_sha256'] else 'WRONG SHA256'
                print(f'{name} {kind}: {status} ({path})')
                failed |= status != 'OK'
        if failed: raise SystemExit(1)
        return
    if platform.system() != 'Windows' or platform.machine().lower() not in ['amd64', 'x86_64']:
        p.error('Certified native binaries require Windows x86_64. Browser studios and --video work on other OSes. See docs/EMULATORS.md.')
    if all((ROOT / path).exists() and digest(ROOT / path) == item['sha256'] for path, item in lock['files'].items()):
        print('All core files already verified'); return
    with tempfile.TemporaryDirectory() as folder:
        archive = Path(folder) / lock['asset']
        download(base + lock['asset'], archive, lock['asset_sha256'])
        with zipfile.ZipFile(archive) as z:
            for relative, item in lock['files'].items():
                content = z.read(relative)
                if hashlib.sha256(content).hexdigest() != item['sha256']:
                    raise ValueError(f'Core checksum mismatch: {relative}')
                destination = ROOT / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
    print('Pinned cores installed. Supply your own ROMs, then run python tools/setup.py --check.')


if __name__ == '__main__':
    main()
