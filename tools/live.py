"""Launch a deployed studio from any working directory."""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('game', choices=['battlecity', 'contra', 'orlegend', 'kovsh'])
    p.add_argument('--port', type=int)
    a = p.parse_args()
    env = dict(os.environ, PYTHONUTF8='1')
    if a.game in ('battlecity', 'contra'):
        env['PORT'] = str(a.port or 8787)
        command = ['node', 'server.cjs']
    elif a.game == 'orlegend':
        command = [sys.executable, 'arcade/serve.py', '--rom', 'arcade/roms/orlegend.zip',
                   '--profile', 'arcade/no-profile.json', '--replay',
                   'arcade/runs/orlegend/bt/full-v4-screen-01/64-16', '--port', str(a.port or 8791)]
    else:
        command = [sys.executable, 'arcade/kovsh_playback.py', '--port', str(a.port or 8796)]
    raise SystemExit(subprocess.call(command, cwd=ROOT, env=env))


if __name__ == '__main__':
    main()
