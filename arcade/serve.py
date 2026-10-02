"""Local emulator + browser broadcast. Run: python arcade/serve.py"""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import time
from urllib.parse import urlparse

from emulator import Emulator, ROOT, BUTTONS
from policy import Heuristic, Observer
from train import sha, verify_profile


class Studio:
    def __init__(self, args):
        self.args, self.lock = args, threading.RLock()
        self.emu, self.observer = None, None
        self.policy = Heuristic(json.loads(Path(args.policy).read_text()) if args.policy else None)
        self.playing, self.mode, self.speed = False, "manual", 1.0
        self.error, self.reason = "", "等待载入游戏"
        self.buttons, self.observation = [], {}
        self.frame_image = None
        self.stopping = threading.Event()
        self.actual_speed, self.last_keys = 0.0, []
        self.button_flash_until = {}
        self.pending, self.pending_frames = [], 0
        self.trace, self.initial_state = [], None
        self.replay, self.replay_index, self.replay_manifest = None, 0, None
        self.replay_result = None
        self.load()

    def load(self):
        if self.emu:
            return
        try:
            self.emu = Emulator(self.args.rom, deterministic=Path(self.args.rom).stem == "orlegend")
            if not self.args.replay:
                self.emu.step([], 1)
            self.initial_state = self.emu.save()
            self.frame_image = self.emu.jpeg()
            self.reason = "手动投币、选人；可在首关保存训练起点"
            self.error = ""
            profile = Path(self.args.profile)
            if profile.exists():
                self.observer = Observer(profile)
                verify_profile(self.observer, self.emu)
            if self.args.replay:
                candidate = Path(self.args.replay).resolve()
                root = candidate if (candidate / "manifest.json").exists() else candidate.parent
                manifest = json.loads((root / "manifest.json").read_text())
                if manifest["core_sha256"] != sha(self.emu.core_path) or manifest["rom_sha256"] != sha(self.emu.rom):
                    raise ValueError("回放核心或 ROM 哈希不一致")
                initial = None if manifest.get("start") == "poweron" else (root / "initial.state").read_bytes()
                if initial is not None and (manifest.get("state_sha256") or manifest.get("initial_state_sha256")) and (manifest.get("state_sha256") or manifest.get("initial_state_sha256")) != sha(root / "initial.state"):
                    raise ValueError("回放初始存档哈希不一致")
                self.replay = [json.loads(line) for line in (candidate / "inputs.jsonl").read_text().splitlines()]
                if not self.replay or any(row.get("frame") != i + 1 or not set(row.get("buttons", [])) <= BUTTONS.keys()
                                          for i, row in enumerate(self.replay)):
                    raise ValueError("回放输入不完整或按键无效")
                self.replay_manifest = json.loads((candidate / "result.json").read_text())
                if initial is not None:self.emu.restore(initial)
                self.initial_state = initial
                self.replay_index, self.trace, self.replay_result = 0, [], None
                self.mode, self.reason = "replay", "纯按键回放：AI 不参与执行"
        except Exception as exc:
            self.error = str(exc)
            self.observer = None
            if self.emu:
                self.emu.close()
                self.emu = None

    def status(self):
        return {"ready": bool(self.emu), "game": Path(self.args.rom).stem, "error": self.error, "playing": self.playing,
                "mode": self.mode, "frame": self.emu.frame if self.emu else 0,
                "fps": self.emu.fps if self.emu else 60, "speed": self.speed,
                "actual_speed": round(self.actual_speed, 2), "reason": self.reason,
                "buttons": self.last_keys, "observation": self.observation,
                "display_buttons": [key for key, until in self.button_flash_until.items() if until > time.monotonic()],
                "calibrated": bool(self.observer), "replay_result": self.replay_result,
                "items_calibrated": bool(self.observer and self.observer.profile.get("items", {}).get("enabled")),
                "item_phase": self.policy.items.phase,
                "item_events": self.policy.items.events[-5:] if self.mode == "heuristic" else [],
                "full_game_clear_verified": bool(self.replay_manifest and self.replay_manifest.get("full_game_clear_verified")),
                "continues": self.replay_manifest.get("continues") if self.replay_manifest else None,
                "deaths": self.replay_manifest.get("deaths") if self.replay_manifest else None,
                "recorded_frames": len(self.trace), "audio": False,
                "inputs": self.emu.descriptors if self.emu else []}

    def advance(self):
        if not self.emu:
            raise ValueError("尚未载入 ROM")
        if self.mode == "replay":
            if self.replay_index >= len(self.replay):
                self.playing = False
                return
            keys = self.replay[self.replay_index]["buttons"]
            self.replay_index += 1
        elif self.mode == "heuristic":
            if not self.observer:
                raise ValueError("需要先校准游戏状态观察器")
            if not self.pending_frames:
                self.pending, self.pending_frames = self.policy.choose(self.emu, self.observer)
            keys = self.pending
            self.pending_frames -= 1
            self.reason = self.policy.reason
        else:
            keys = self.buttons
        self.emu.step(keys)
        self.last_keys = list(keys)
        for key in keys:
            self.button_flash_until[key] = time.monotonic() + .14
        self.trace.append({"frame": len(self.trace) + 1, "buttons": list(keys)})
        if not self.observer and Path(self.args.rom).stem == "orlegend":
            from orlegend import observe
            observed = observe(self.emu.ram())
            self.observation = {**observed, "progress": f"{observed['stage_byte']}:{observed['scene_byte']}"}
        if self.observer:
            self.observation = self.observer.read(self.emu.ram())
            if self.mode == "heuristic":
                self.policy.feedback(self.observation, self.emu.frame)
            if self.observation["victory"] or self.observation["game_over"]:
                self.playing = False
                self.reason = "观察到终局；完整通关结论需独立审核"
        if self.mode == "replay" and self.replay_index == len(self.replay):
            self.playing = False
            actual = self.emu.fingerprint()
            self.replay_result = {"equal": all(actual[k] == v for k, v in (self.replay_manifest.get("expected") or self.replay_manifest["fingerprint"]).items() if k != "video" and v is not None), "actual": actual}
            self.reason = "回放核对一致" if self.replay_result["equal"] else "回放核对失败"

    def command(self, data):
        action = data.get("action")
        if action == "reload":
            self.load()
            return self.status()
        if not self.emu:
            raise ValueError(f"缺少游戏 ROM：{self.args.rom}")
        if action == "play":
            if self.replay is not None and self.replay_index >= len(self.replay):
                raise ValueError("回放已结束；重新启动直播服务可从头播放并保持完整状态核验")
            self.playing = bool(data.get("value", not self.playing))
            if not self.playing:
                self.buttons = []
                self.last_keys = []
                self.button_flash_until.clear()
        elif action == "step":
            self.playing = False
            self.advance()
            self.frame_image = self.emu.jpeg()
        elif action == "speed":
            value = float(data["value"])
            if value not in (0.5, 1, 2, 4):
                raise ValueError("无效倍速")
            self.speed = value
        elif action == "mode":
            mode = data["value"]
            if self.replay is not None or mode not in ("manual", "heuristic"):
                raise ValueError("回放模式不能切换策略")
            if mode == "heuristic" and not self.observer:
                raise ValueError("观察器尚未校准，不能启用状态策略")
            self.mode, self.pending_frames, self.buttons = mode, 0, []
        elif action == "keys":
            if self.mode != "manual":
                raise ValueError("当前不是手动模式")
            keys = data.get("buttons", [])
            if not isinstance(keys, list) or not set(keys) <= BUTTONS.keys():
                raise ValueError("无效按键")
            self.buttons = list(set(keys))
        elif action == "save":
            directory = ROOT / "runs" / time.strftime("capture-%Y%m%d-%H%M%S")
            directory.mkdir(exist_ok=False)
            state = self.emu.save()
            (directory / "current.state").write_bytes(state)
            (directory / "initial.state").write_bytes(self.initial_state)
            (directory / "ram.bin").write_bytes(self.emu.ram())
            pic = self.emu.picture()
            if pic:
                pic.save(directory / "frame.png")
            (directory / "inputs.jsonl").write_text("".join(json.dumps(row) + "\n" for row in self.trace), encoding="utf-8")
            (directory / "manifest.json").write_text(json.dumps({"core_sha256": sha(self.emu.core_path),
                "rom_sha256": sha(self.emu.rom), "state_sha256": sha(directory / "current.state"),
                "status": self.status()}, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"saved": str(directory)}
        else:
            raise ValueError("未知操作")
        return self.status()

    def run(self):
        previous, speed_since, speed_frames = time.perf_counter(), time.perf_counter(), 0
        accumulator, last_image = 0.0, 0.0
        while not self.stopping.wait(0.002):
            now = time.perf_counter()
            with self.lock:
                if self.playing and self.emu:
                    accumulator = min(6, accumulator + min(now - previous, .1) * self.emu.fps * self.speed)
                    try:
                        deadline = time.perf_counter() + .012
                        while accumulator >= 1 and self.playing:
                            self.advance()
                            accumulator -= 1
                            speed_frames += 1
                            if time.perf_counter() >= deadline:
                                break
                        if now - last_image > 1 / 30:
                            self.frame_image = self.emu.jpeg()
                            last_image = now
                    except Exception as exc:
                        self.error, self.playing = str(exc), False
                else:
                    accumulator = 0
                if now - speed_since >= 1:
                    self.actual_speed = speed_frames / (now - speed_since) / (self.emu.fps if self.emu else 60)
                    speed_since, speed_frames = now, 0
            previous = now


def handler(studio):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def respond(self, body, kind="application/json", code=200):
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/api/status":
                with studio.lock:
                    body = json.dumps(studio.status(), ensure_ascii=False).encode()
                self.respond(body)
            elif path == "/frame.jpg":
                with studio.lock:
                    body = studio.frame_image
                self.respond(body or b"", "image/jpeg", 200 if body else 204)
            elif path == "/assets/arcade-panel-v1.png":
                self.respond((ROOT / "web/assets/arcade-panel-v1.png").read_bytes(), "image/png")
            elif path in ("/", "/live.html", "/live.css", "/live.js"):
                filename = "live.html" if path == "/" else path[1:]
                kind = {"html": "text/html; charset=utf-8", "css": "text/css", "js": "text/javascript"}[filename.rsplit(".", 1)[1]]
                body = (ROOT / "web" / filename).read_bytes()
                if filename == "live.html" and Path(studio.args.rom).stem == "orlegend":
                    body = body.decode("utf-8").replace("三国战纪 · 风云再起", "西游释厄传 · V126").replace("三国战纪 <span>风云再起</span>", "西游释厄传 <span>V126</span>").replace("风云再起", "西游释厄传").replace("KNIGHTS OF VALOUR · SUPER HEROES", "ORIENTAL LEGEND · V126").replace("<span>关卡进展</span>", "<span>场景码</span>").replace("<span>生命</span>", "<span>生命（含当前）</span>").encode("utf-8")
                self.respond(body, kind)
            else:
                self.respond(b"Not found", "text/plain", 404)

        def do_POST(self):
            if self.path != "/api/control":
                self.respond(b"{}", code=404)
                return
            origin = self.headers.get("Origin")
            if origin and urlparse(origin).netloc != self.headers.get("Host"):
                self.respond(b"{}", code=403)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 65536:
                    raise ValueError("Invalid body length")
                data = json.loads(self.rfile.read(length))
                with studio.lock:
                    result = studio.command(data)
                self.respond(json.dumps(result, ensure_ascii=False).encode())
            except (ValueError, KeyError, OSError, RuntimeError) as exc:
                self.respond(json.dumps({"error": str(exc)}, ensure_ascii=False).encode(), code=400)
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", default=str(ROOT / "roms/kovsh.zip"))
    parser.add_argument("--profile", default=str(ROOT / "observation.json"))
    parser.add_argument("--policy")
    parser.add_argument("--replay", help="candidate directory from train.py")
    parser.add_argument("--port", type=int, default=8788)
    args = parser.parse_args()
    studio = Studio(args)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler(studio))
    worker = threading.Thread(target=studio.run, daemon=True)
    worker.start()
    print(f"http://127.0.0.1:{args.port}/live.html", flush=True)
    if studio.error:
        print(studio.error, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        studio.stopping.set()
        worker.join()
        server.server_close()
        if studio.emu:
            studio.emu.close()


if __name__ == "__main__":
    main()
