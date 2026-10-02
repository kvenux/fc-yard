"""Browser playback of the audited four-stage KOVSH input stream.

Rendering is confined to this playback process; training stays headless.
Seeking re-executes recorded buttons, with only playback-local cache restores.
"""
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import threading
import time
from types import SimpleNamespace
from urllib.parse import urlparse, parse_qs
from http.server import ThreadingHTTPServer

from emulator import Emulator, ROOT, BUTTONS
from kovsh import observe
from serve import handler

BASE = ROOT / 'runs/kovsh'
PREFIX = BASE / 'one-life-chapter4-best-prefix-045.jsonl'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Playback:
    def __init__(self):
        manifest = json.loads((BASE / 'one-life-next-chapter-cold-045/manifest.json').read_text())
        core = ROOT / 'cores/fbneo_pgm_statefix_libretro.dll'
        rom = ROOT / 'roms/kovsh.zip'
        for path, expected in ((core, manifest['core_sha256']), (rom, manifest['rom_sha256']),
                               (PREFIX, manifest['prefix_sha256'])):
            if sha(path) != expected:
                raise ValueError(f'回放文件校验失败：{path.name}')
        rows = [json.loads(line) for line in PREFIX.read_text().splitlines()]
        if any(row['frame'] != i + 1 or not set(row['buttons']) <= BUTTONS.keys()
               for i, row in enumerate(rows)):
            raise ValueError('输入记录不连续或按键无效')
        self.inputs = [row['buttons'] for row in rows]
        self.expected_ram = json.loads((ROOT.parent / 'data/kovsh/proof.json').read_text())['expected']['ram']
        self.lock = threading.RLock()
        self.stopping = threading.Event()
        self.args = SimpleNamespace(rom=str(rom))
        self.emu = Emulator(rom, core=core, deterministic=True)
        self.cache = {0: self.emu.save()}
        self.frame_image = None
        self.buttons = []
        self.playing = True
        self.speed = 1.0
        self.actual_speed = 0.0
        self.error = ''
        self.seek_target = 3790
        self.resume_after_seek = True
        self.replay_result = None
        self.observation = {}
        self.audio_chunks = deque(maxlen=90)
        self.audio_sequence = 0
        self.audio_epoch = 0

    def clear_audio(self):
        self.emu.audio.clear()
        self.audio_chunks.clear()
        self.audio_epoch += 1

    def audio_packet(self, after, epoch):
        chunks = list(self.audio_chunks)
        if epoch != self.audio_epoch or after < 0:
            chunks = chunks[-3:]
        else:
            chunks = [chunk for chunk in chunks if chunk[0] > after]
        return b''.join(chunk[1] for chunk in chunks)

    def status(self):
        o = dict(self.observation)
        o['inventory'] = [dict(id=k, name='道具 ' + k, count=v)
                          for k, v in o.get('inventory', {}).items()]
        o['progress'] = f"场景 {o.get('chapter', '—')} / {o.get('room_raw', '—')}"
        seeking = self.seek_target is not None
        reason = (f'跳转中：{self.emu.frame:,} → {self.seek_target:,} 帧' if seeking else
                  '前四关已执行动作 · 一币零死亡路线')
        if self.emu.frame == len(self.inputs):
            reason = '前四关播放结束 · 剩余 55 血' if self.replay_result and self.replay_result['equal'] else '播放结束 · 核验失败'
        return dict(ready=True, game='kovsh', playing=self.playing and not seeking,
                    mode='replay', frame=self.emu.frame, recorded_frames=self.emu.frame,
                    total_frames=len(self.inputs), fps=self.emu.fps, speed=self.speed,
                    actual_speed=self.actual_speed, reason=reason, error=self.error,
                    buttons=self.buttons, observation=o, calibrated=True,
                    items_calibrated=True, item_events=[], replay_result=self.replay_result,
                    headless=False, has_video=True, full_game_clear_verified=False,
                    seeking=seeking, audio=True, audio_sample_rate=self.emu.av.timing.sample_rate,
                    audio_epoch=self.audio_epoch,
                    verified_scope='前四关连续一币零死亡；整局尚未通关')

    def advance(self):
        if self.emu.frame >= len(self.inputs):
            self.playing = False
            return
        self.buttons = self.inputs[self.emu.frame]
        self.emu.step(self.buttons)
        if self.emu.audio:
            self.audio_sequence += 1
            self.audio_chunks.append((self.audio_sequence, bytes(self.emu.audio)))
            self.emu.audio.clear()
        if self.emu.frame % 3600 == 0:
            self.cache[self.emu.frame] = self.emu.save()
        self.observation = observe(self.emu.ram_view())
        if self.emu.frame == len(self.inputs):
            self.playing = False
            self.replay_result = {'equal': hashlib.sha256(self.emu.ram()).hexdigest() == self.expected_ram, 'scope': 'terminal_ram'}

    def command(self, data):
        action = data.get('action')
        if action in ('seek', 'reload'):
            target = 3790 if action == 'reload' else int(data['frame'])
            if not 0 <= target <= len(self.inputs):
                raise ValueError('跳转帧超出路线范围')
            self.clear_audio()
            self.seek_target = target
            self.resume_after_seek = bool(data.get('play', self.playing))
            self.playing = False
            self.replay_result = None
            cached = max(frame for frame in self.cache if frame <= target)
            self.emu.restore(self.cache[cached], frame=cached)
            self.buttons = []
            self.observation = observe(self.emu.ram_view())
        elif action == 'play':
            self.clear_audio()
            value = bool(data.get('value', not self.playing))
            if self.seek_target is not None:
                self.resume_after_seek = value
            elif self.emu.frame == len(self.inputs) and value:
                return self.command({'action': 'reload', 'play': True})
            else:
                self.playing = value
        elif action == 'speed':
            value = float(data['value'])
            if value not in (.5, 1, 2, 4):
                raise ValueError('无效倍速')
            self.clear_audio()
            self.speed = value
        elif action == 'step':
            if self.seek_target is not None:
                raise ValueError('正在跳转')
            self.playing = False
            self.clear_audio()
            self.emu.capture_audio = False
            self.advance()
            self.frame_image = self.emu.jpeg()
        else:
            raise ValueError('本页播放已记录动作，请使用暂停、倍速或跳转')
        return self.status()

    def run(self):
        previous = speed_since = time.perf_counter()
        accumulator = 0.0
        last_image = 0.0
        speed_frames = 0
        while not self.stopping.wait(.002):
            now = time.perf_counter()
            with self.lock:
                try:
                    if self.seek_target is not None:
                        target = self.seek_target
                        self.emu.capture_audio = False
                        # Bounded chunks keep status and playback controls responsive.
                        self.emu.av_enable = 2
                        for _ in range(min(240, target - self.emu.frame)):
                            if self.emu.frame + 1 == target:
                                self.emu.av_enable = 3
                            self.advance()
                        if self.emu.frame == target:
                            self.emu.av_enable = 3
                            self.frame_image = self.emu.jpeg()
                            self.seek_target = None
                            self.playing = self.resume_after_seek and target < len(self.inputs)
                        accumulator = 0
                    elif self.playing:
                        self.emu.capture_audio = True
                        accumulator = min(12, accumulator + min(now - previous, .1) * self.emu.fps * self.speed)
                        deadline = time.perf_counter() + .012
                        while accumulator >= 1 and self.playing:
                            self.advance()
                            accumulator -= 1
                            speed_frames += 1
                            if time.perf_counter() >= deadline:
                                break
                        if now - last_image > 1 / 30 or not self.playing:
                            self.frame_image = self.emu.jpeg()
                            last_image = now
                    else:
                        self.emu.capture_audio = False
                        accumulator = 0
                except Exception as exc:
                    self.error, self.playing, self.seek_target = str(exc), False, None
                    self.emu.av_enable = 3
                if now - speed_since >= 1:
                    self.actual_speed = round(speed_frames / (now - speed_since) / self.emu.fps, 2)
                    speed_since, speed_frames = now, 0
            previous = now


def playback_handler(studio):
    parent = handler(studio)

    class Handler(parent):
        def do_GET(self):
            path = urlparse(self.path).path
            if path in ('/', '/live.html'):
                html = (ROOT / 'web/live.html').read_text(encoding='utf-8')
                html = html.replace('直播控制台', '前四关 · 策略演示')
                html = html.replace('保存训练起点', '路线已核验').replace('重新检测 ROM', '从首关重播')
                html = html.replace('当前直播无声。', '点击声音开关播放原版游戏音效。')
                html = html.replace('<button id="capture">',
                                    '<button id="sound-toggle" type="button" aria-pressed="false" '
                                    'style="width:100%;margin-top:12px">声音：关</button>'
                                    '<button id="capture">')
                html = html.replace('实时模拟器画面 · 普通按键控制 · 对局记录可核验',
                                    '真实模拟器画面 · 已记录动作 · 前四关一币零死亡 · 整局尚未通关')
                toolbar = '''<section style="margin:14px 0"><label>跳转到已验证路线
<select id="seek-preset"><option value="3790">首关开始</option><option value="86890">第四关 · 竹林</option>
<option value="93629">绳索入口</option><option value="95248">山洞入口</option>
<option value="100376">山洞出口</option><option value="108657">第四关 Boss</option></select></label>
<button id="seek-go">跳转并播放</button><p>前四关约 32 分钟，可用 2× / 4× 播放。</p>
<p id="route-proof">前四关连续一币零死亡 · 整局尚未通关</p>
<a href="/route-curve.png" target="_blank">第四关路线得分与血量曲线</a></section>'''
                html = html.replace('<div id="notice"', toolbar + '<div id="notice"')
                html = html.replace('</body>', '''<script src="kovsh-audio.js"></script><script>
document.getElementById('save').disabled=true;
document.getElementById('save').onclick=()=>{};
document.getElementById('seek-go').onclick=()=>command('seek',{frame:Number(document.getElementById('seek-preset').value),play:true});
</script></body>''')
                self.respond(html.encode(), 'text/html; charset=utf-8')
            elif path == '/live.js':
                js = (ROOT / 'web/live.js').read_text(encoding='utf-8')
                js = js.replace('回放', '播放')
                js = js.replace('  renderCabinet(s); renderItems(s);',
                                "  $('evidence').textContent=s.verified_scope; $('save').disabled=true; "
                                "$('badge').textContent=s.seeking?'跳转中':s.playing?'运行中':'已暂停'; "
                                "$('play').disabled=s.seeking; $('step').disabled=s.seeking; "
                                "renderCabinet(s); renderItems(s);")
                self.respond(js.encode(), 'text/javascript')
            elif path == '/route-curve.png':
                self.respond((BASE / 'adopted-route-score-curve.png').read_bytes(), 'image/png')
            elif path == '/kovsh-audio.js':
                self.respond((ROOT / 'web/kovsh-audio.js').read_bytes(), 'text/javascript')
            elif path == '/audio.pcm':
                query = parse_qs(urlparse(self.path).query)
                with studio.lock:
                    body = studio.audio_packet(int(query.get('after', ['-1'])[0]),
                                               int(query.get('epoch', ['-1'])[0]))
                    audio_headers = {
                        'X-Audio-Cursor': studio.audio_sequence, 'X-Audio-Epoch': studio.audio_epoch,
                        'X-Audio-Rate': studio.emu.av.timing.sample_rate, 'X-Audio-Speed': studio.speed,
                        'X-Audio-Playing': int(studio.playing and studio.seek_target is None),
                    }
                self.send_response(200)
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Content-Length', str(len(body)))
                for name, value in audio_headers.items():
                    self.send_header(name, str(value))
                self.end_headers()
                self.wfile.write(body)
            else:
                super().do_GET()
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8796)
    args = parser.parse_args()
    studio = Playback()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), playback_handler(studio))
    worker = threading.Thread(target=studio.run, daemon=True)
    worker.start()
    print(f'http://127.0.0.1:{args.port}/live.html', flush=True)
    try:
        server.serve_forever()
    finally:
        studio.stopping.set()
        worker.join()
        studio.emu.close()
        server.server_close()


if __name__ == '__main__':
    main()
