"""Cold-boot replay of published inputs; no checkpoints or ROM modifications."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'arcade'))
from emulator import Emulator


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('game', choices=['contra', 'orlegend', 'kovsh'])
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    registry = json.loads((ROOT / 'games.json').read_text(encoding='utf-8'))
    game = registry['games'][a.game]
    proof = json.loads((ROOT / game['proof']).read_text(encoding='utf-8'))
    rom, core = ROOT / game['rom'], ROOT / game['core']
    for name, path in [('rom', rom), ('core', core)]:
        if not path.is_file():
            p.error(f'Missing {path}. See README.md and tools/setup.py.')
        if hashlib.sha256(path.read_bytes()).hexdigest() != proof[name + '_sha256']:
            p.error(f'{name} SHA256 does not match the certified version')
    if hashlib.sha256((ROOT / game['inputs']).read_bytes()).hexdigest() != proof['inputs_sha256']:
        p.error('Published input checksum mismatch')
    start = time.perf_counter()
    e = Emulator(rom, core, deterministic=True, headless=game['headless'])
    deaths = coins = 0
    last_dead = False
    try:
        if a.game == 'contra':
            record = json.loads((ROOT / game['inputs']).read_text())
            for mask, count in record['actions']:
                e.mask = (mask & 252) | ((mask & 1) << 8) | ((mask & 2) >> 1)
                for _ in range(count):
                    e.core.retro_run(); e.frame += 1
                    dead = e.ram_view()[0x90] == 2
                    deaths += int(dead and not last_dead); last_dead = dead
        else:
            observer = __import__(a.game).observe
            previous = observer(e.ram_view())
            coin_down = False
            with (ROOT / game['inputs']).open(encoding='utf-8') as stream:
                for index, line in enumerate(stream):
                    row = json.loads(line)
                    if row['frame'] != index + 1:
                        raise ValueError('Non-contiguous input trace')
                    buttons = row['buttons']
                    coins += int('coin' in buttons and not coin_down)
                    coin_down = 'coin' in buttons
                    e.step(buttons)
                    now = observer(e.ram_view())
                    if 0 <= now['lives'] < previous['lives'] <= 2:
                        deaths += previous['lives'] - now['lives']
                    previous = now
                    if e.frame % 100000 == 0:
                        print(f'{a.game}: {e.frame:,} frames', flush=True)
        actual = e.fingerprint()
        equal = {key: actual[key] == value for key, value in proof['expected'].items() if value is not None}
        ok = all(equal.values()) and e.frame == proof['frames'] and deaths == proof['deaths']
        if 'coins' in proof:
            ok = ok and coins == proof['coins']
        result = dict(game=a.game, frames=e.frame, deaths=deaths, coins=coins,
                      equal=equal, passed=ok, actual=actual, scope=proof['scope'],
                      restores=0, seconds=round(time.perf_counter()-start, 2))
        output = a.output or ROOT / 'outputs' / f'{a.game}-replay.json'
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(json.dumps(result), flush=True)
        return 0 if ok else 1
    finally:
        e.close()


if __name__ == '__main__':
    sys.exit(main())
