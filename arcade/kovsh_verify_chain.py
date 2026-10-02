"""Replay a recorded KOVSH route from power-on, without loading checkpoints."""
import argparse
import json
from pathlib import Path
from PIL import Image
from emulator import Emulator
from kovsh import OUT, ROM, observe, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('chain', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    chain = json.loads(args.chain.read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    e = Emulator(ROM, deterministic=True)
    frames = coins = 0
    previous = []
    checks = []
    try:
        segments = [{'file': 'boot-inputs.jsonl', 'frames': None}] + chain['parts']
        with (args.output/'inputs.jsonl').open('w') as trace:
            for part in segments:
                directory = OUT/part['directory'] if 'directory' in part else OUT
                source = directory/part.get('file', 'inputs.jsonl')
                if not source.exists(): source = directory/'inputs.partial.jsonl'
                rows = source.read_text().splitlines()
                count = part['frames'] or len(rows)
                assert len(rows) >= count
                for line in rows[:count]:
                    buttons = json.loads(line)['buttons']
                    coins += int('coin' in buttons and 'coin' not in previous)
                    previous = buttons
                    e.step(buttons)
                    frames += 1
                    trace.write(json.dumps({'frame': frames, 'buttons': buttons})+'\n')
                if 'directory' in part:
                    stem = part.get('endpoint', f'frame-{count:06d}')
                    expected_ram = (directory/f'{stem}.ram').read_bytes()
                    checks.append({'directory': part['directory'], 'frames': count,
                        'observation_equal': observe(e.ram()) == observe(expected_ram),
                        'ram_equal': e.ram() == expected_ram,
                        'video_equal': e.picture().tobytes() == Image.open(directory/f'{stem}.png').convert('RGB').tobytes()})
                e.picture().save(args.output/'current.png')
                (args.output/'progress.json').write_text(json.dumps({'frames':frames,'coins':coins,'checks':checks,'observation':observe(e.ram())}))
        (args.output/'final.state').write_bytes(e.save())
        (args.output/'final.ram').write_bytes(e.ram())
        e.picture().save(args.output/'final.png')
        report = {'frames':frames,'coins':coins,'checks':checks,
            'all_equal':all(c['observation_equal'] and c['ram_equal'] and c['video_equal'] for c in checks),
            'after':observe(e.ram()),'rom_sha256':sha(ROM),'core_sha256':sha(e.core_path),
            'full_game_clear_verified':False}
        (args.output/'report.json').write_text(json.dumps(report,indent=2))
        (args.output/'manifest.json').write_text(json.dumps({
            'game':'kovsh','start':'poweron','scope':'continuous_poweron_replay',
            'rom_sha256':report['rom_sha256'],'core_sha256':report['core_sha256'],
            'source_chain':str(args.chain.resolve()),'full_game_clear_verified':False
        },indent=2))
        (args.output/'result.json').write_text(json.dumps({
            'expected':e.fingerprint(),'frames':frames,'coins':coins,
            'replay_verified':report['all_equal'],'after':report['after'],
            'full_game_clear_verified':False
        },indent=2))
        print(json.dumps(report),flush=True)
    finally:e.close()


if __name__ == '__main__':main()
