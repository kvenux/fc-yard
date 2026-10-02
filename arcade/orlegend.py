"""Oriental Legend V126: read-only RAM observation and checkpoint policy search.

No terminal/victory field is claimed calibrated. Search results are local practice.
CPU byte addresses are word-swapped in FBNeo's exported 68000 RAM.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import subprocess
import sys

from emulator import Emulator, ROOT

OUT = ROOT / "runs/orlegend"
ROM = ROOT / "roms/orlegend.zip"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def observe(r):
    def word(o):
        return int.from_bytes(r[o:o+2], "little")
    def coord(o):return int.from_bytes(r[o:o+2], "little", signed=True)
    enemies = []
    for i in range(8):
        b = 0x11A40 + i * 0x13E
        hp = word(b + 0x48)
        if r[b-15] == 2 and 0 < hp < 4096:
            enemies.append({"slot": i, "x": coord(b), "y": coord(b+2), "hp": hp})
    return {"hp": word(0x1BE98), "lives": r[0x1C4A3],
            "x": coord(0x1BE50), "y": coord(0x1BE52),
            "stage_raw": word(0xC03A), "stage_byte": r[0xC03B], "scene_byte": r[0xC03A], "enemies": enemies}


def action(o, frame, config):
    enemies = o["enemies"]
    keys = []
    # Experimental route override, disabled unless explicitly selected in a trial.
    route = config.get("routes", {}).get(str(o["stage_raw"]))
    if route:
        keys.append(route["direction"])
        if abs(o["y"]-route["y"]) > 4:
            keys.append("up" if o["y"] > route["y"] else "down")
        if frame % config["period"] < config["period"] // 2:
            keys.append("attack")
        return keys
    if enemies:
        focus = config.get("focus_slot", {}).get(str(o["stage_raw"]))
        targets = [e for e in enemies if e["slot"] == focus] or enemies
        e = min(targets, key=lambda e: abs(e["x"]-o["x"])+3*abs(e["y"]-o["y"]))
        dx, dy = e["x"]-o["x"], e["y"]+config.get("enemy_y_offset",0)-o["y"]
        if abs(dy) > config["align"]:
            keys.append("down" if dy > 0 else "up")
        if abs(dx) > config["distance"] or frame % config["period"] == 0:
            keys.append("right" if dx > 0 else "left")
    else:
        keys.append("right")
    if frame % config["period"] < config["period"] // 2:
        keys.append("attack")
    if config.get("jump") and frame % config["jump"] < 2:
        keys = [k for k in keys if k != "attack"] + ["jump"]
    if enemies and config.get("rush") and frame % config["rush"] < 2:
        if abs(dx) < 100 and abs(dy) < 24:
            keys = ["right" if dx > 0 else "left", "down", "jump"]
    return keys


def search(args):
    out = Path(args.output) if args.output else OUT / time.strftime("search-%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=False)
    state = Path(args.state).read_bytes()
    (out / "initial.state").write_bytes(state)
    emu = Emulator(ROM, deterministic=True)
    manifest = {"core_sha256": sha(emu.core_path), "rom_sha256": sha(ROM),
                "state_sha256": sha(args.state), "source_sha256": sha(__file__), "frontend_sha256": sha(ROOT/"emulator.py"),
                "scope": "checkpoint_practice", "terminal_calibrated": False, "deterministic": True,
                "frames_budget": args.frames, "fps": emu.fps,
                "life_counter": "includes current life; stop at zero",
                "progress_metric": "raw scene code; not independently verified chapter count"}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    (out / "source.py").write_bytes(Path(__file__).read_bytes())
    (out / "emulator.py").write_bytes((ROOT / "emulator.py").read_bytes())
    configs = [{"period": p, "distance": d, "align": a, "jump": j}
               for p in (4, 8) for d in (32, 56) for a, j in ((8, 0), (14, 120))]
    results = []
    try:
        for n, config in enumerate([json.loads(args.config)] if args.config else configs):
            folder = out / f"candidate-{n:02d}"
            folder.mkdir()
            emu.restore(state)
            before = previous = observe(emu.ram())
            damage = 0
            trace = []
            samples = []
            started = time.perf_counter()
            for f in range(args.frames):
                o = observe(emu.ram())
                keys = action(o, f, config)
                emu.step(keys)
                after = observe(emu.ram())
                old = {e['slot']:e for e in previous['enemies']}
                new = {e['slot']:e for e in after['enemies']}
                # This metric is only a search proxy; slot recycling can affect it.
                damage += sum(max(0,e['hp']-new.get(i,{'hp':0})['hp']) for i,e in old.items())
                previous = after
                trace.append({"frame":f+1,"buttons":keys})
                if f % 600 == 599:
                    samples.append({"frame": f+1, **after})
                    emu.picture().save(folder / f"frame-{f+1:07d}.png")
                # Stop when the total life counter reaches zero; never train on attract demos.
                if after['lives'] == 0 or after['lives'] >= 128:
                    break
            expected = emu.fingerprint()
            (folder / "final.state").write_bytes(emu.save())
            (folder / "final.ram").write_bytes(emu.ram())
            emu.picture().save(folder / "final.png")
            elapsed = time.perf_counter()-started
            with (folder / "inputs.jsonl").open('w') as fp:
                for row in trace:
                    fp.write(json.dumps(row)+'\n')
            subprocess.run([sys.executable, __file__, '--replay', str(folder)], check=True)
            replay = json.loads((folder/'replay-fingerprint.json').read_text())
            reward = 5000*(after['stage_raw']-before['stage_raw']) + damage + 1000*(after['lives']-before['lives']) + 4*(after['hp']-before['hp'])
            if after['lives'] == 0 or after['lives'] >= 128:
                reward = -100000 + damage
            result = {"candidate":n,"config":config,"frames":len(trace),"before":before,"after":after,
                      "damage_proxy":damage,"reward":reward,"wall_seconds":elapsed,
                      "expected":expected,"replay":replay,"replay_equal":expected==replay,
                      "full_game_clear_verified":False,"scope":"checkpoint_practice",
                      "stop_reason":"lives_exhausted" if after['lives']==0 or after['lives']>=128 else "frame_budget"}
            (folder/'result.json').write_text(json.dumps(result,indent=2))
            (folder/'samples.json').write_text(json.dumps(samples,indent=2))
            results.append(result)
            print(json.dumps(result),flush=True)
            (out/'results.json').write_text(json.dumps(results,indent=2))
        verified = [r for r in results if r['replay_equal']]
        if verified:
            winner = max(verified,key=lambda r:r['reward'])
            (out/'best-policy.json').write_text(json.dumps(winner['config'],indent=2))
            (out/'winner.json').write_text(json.dumps(winner,indent=2))
        print('OUTPUT',out,flush=True)
    finally:
        emu.close()


def bootstrap():
    """One coin, default Wu-Kong, stop shortly after entering the first scene."""
    OUT.mkdir(parents=True, exist_ok=True)
    emu = Emulator(ROM, deterministic=True)
    trace = []
    def advance(keys, count):
        for _ in range(count):
            emu.step(keys)
            trace.append({'frame': len(trace)+1, 'buttons': keys})
    try:
        advance([], 1800)
        advance(['coin'], 2)
        advance([], 60)
        advance(['start'], 2)
        advance([], 420)
        for _ in range(20):
            advance(['attack'], 2)
            advance([], 58)
            if observe(emu.ram())['hp'] > 0:
                break
        advance([], 60)
        o = observe(emu.ram())
        if o['hp'] != 72 or o['lives'] != 2 or o['stage_raw'] != 0:
            raise RuntimeError(f'Unexpected first-scene state: {o}')
        (OUT/'deterministic-start.state').write_bytes(emu.save())
        (OUT/'deterministic-start.ram').write_bytes(emu.ram())
        emu.picture().save(OUT/'deterministic-start.png')
        (OUT/'boot-inputs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in trace))
        (OUT/'boot-manifest.json').write_text(json.dumps({
            'core_sha256': sha(emu.core_path), 'rom_sha256':sha(ROM),
            'frontend_sha256':sha(ROOT/'emulator.py'), 'deterministic':True,
            'initial_frames':len(trace), 'observation':o, 'expected':emu.fingerprint()},indent=2))
    finally:
        emu.close()


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state',default=str(OUT/'deterministic-start.state'))
    parser.add_argument('--frames',type=int,default=7200)
    parser.add_argument('--config')
    parser.add_argument('--output')
    parser.add_argument('--replay')
    parser.add_argument('--bootstrap', action='store_true')
    args=parser.parse_args()
    if args.frames < 1:
        parser.error('--frames must be positive')
    if args.bootstrap:
        bootstrap()
    elif args.replay:
        folder = Path(args.replay)
        emu = Emulator(ROM, deterministic=True)
        try:
            manifest = json.loads((folder.parent/'manifest.json').read_text())
            if (manifest['core_sha256'] != sha(emu.core_path)
                    or manifest['rom_sha256'] != sha(ROM)
                    or manifest['state_sha256'] != sha(folder.parent/'initial.state')
                    or not manifest.get('deterministic')):
                raise ValueError('Replay provenance mismatch')
            emu.restore((folder.parent/'initial.state').read_bytes())
            for row in (folder/'inputs.jsonl').read_text().splitlines():
                emu.step(json.loads(row)['buttons'])
            (folder/'replay-fingerprint.json').write_text(json.dumps(emu.fingerprint(),indent=2))
            (folder/'replay.state').write_bytes(emu.save())
        finally:
            emu.close()
    elif args.config:
        search(args)
    else:
        out=OUT/time.strftime('isolated-%Y%m%d-%H%M%S')
        out.mkdir(parents=True)
        configs=[{'period':p,'distance':d,'align':a,'jump':j}
                 for p in (4,8) for d in (32,56) for a,j in ((8,0),(14,120))]
        results=[]
        for n,config in enumerate(configs):
            dest=out/f'trial-{n:02d}'
            subprocess.run([sys.executable,__file__,'--state',args.state,'--frames',str(args.frames),
                            '--config',json.dumps(config),'--output',str(dest)],check=True)
            result=json.loads((dest/'candidate-00/result.json').read_text())
            result['trial']=n
            results.append(result)
            (out/'results.json').write_text(json.dumps(results,indent=2))
        verified=[r for r in results if r['replay_equal']]
        if verified:
            winner=max(verified,key=lambda r:r['reward'])
            (out/'winner.json').write_text(json.dumps(winner,indent=2))
        print('BATCH_OUTPUT',out,flush=True)
