"""Small synchronous libretro frontend. One core instance per process."""
import ctypes as C
import hashlib
import io
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
BUTTONS = {"attack": 0, "item": 1, "coin": 2, "start": 3,
           "up": 4, "down": 5, "left": 6, "right": 7, "jump": 8, "menu": 9,
           "c": 1, "d": 9}  # physical buttons 3/4; legacy aliases retained for replay
ENV = C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p)
VIDEO = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
AUDIO = C.CFUNCTYPE(None, C.c_int16, C.c_int16)
BATCH = C.CFUNCTYPE(C.c_size_t, C.c_void_p, C.c_size_t)
POLL = C.CFUNCTYPE(None)
INPUT = C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint)


class GameInfo(C.Structure):
    _fields_ = [("path", C.c_char_p), ("data", C.c_void_p),
                ("size", C.c_size_t), ("meta", C.c_char_p)]


class Variable(C.Structure):
    _fields_ = [("key", C.c_char_p), ("value", C.c_char_p)]


class Descriptor(C.Structure):
    _fields_ = [("port", C.c_uint), ("device", C.c_uint), ("index", C.c_uint),
                ("id", C.c_uint), ("description", C.c_char_p)]


class Geometry(C.Structure):
    _fields_ = [("width", C.c_uint), ("height", C.c_uint),
                ("max_width", C.c_uint), ("max_height", C.c_uint), ("aspect", C.c_float)]


class Timing(C.Structure):
    _fields_ = [("fps", C.c_double), ("sample_rate", C.c_double)]


class AVInfo(C.Structure):
    _fields_ = [("geometry", Geometry), ("timing", Timing)]


class Emulator:
    def __init__(self, rom=None, core=None, system=None, deterministic=False, headless=False):
        self.deterministic = deterministic
        self.core_path = Path(core or ROOT / "cores/fbneo_libretro.dll").resolve()
        self.rom = Path(rom).resolve() if rom else None
        if self.rom and not self.rom.is_file():
            raise FileNotFoundError(f"缺少 ROM：{self.rom}")
        # FBNeo copies its fixed path buffer from these pointers; keep padded buffers alive.
        self._directory_buffer = C.create_string_buffer(str(Path(system or (self.rom.parent if self.rom else ROOT / "roms")).resolve()).encode(), 8192)
        self._isolated_save = tempfile.TemporaryDirectory(prefix="orlegend-") if deterministic else None
        save_path = self._isolated_save.name if self._isolated_save else str(ROOT / "runs")
        self._save_buffer = C.create_string_buffer(save_path.encode(), 8192)
        self.directory = C.cast(self._directory_buffer, C.c_char_p)
        self.save_directory = C.cast(self._save_buffer, C.c_char_p)
        self.options, self.descriptors, self.messages = {}, [], []
        self.pixel_format, self.frame, self.mask = 0, 0, 0
        self.image, self.video_bytes, self.video_shape = None, None, None
        self.audio = bytearray()
        self.capture_audio = False
        self.headless = headless
        # Keep audio emulation active; only skip drawing and frontend pixel copies.
        self.av_enable = 2 if headless else 3
        self.video_callbacks = 0
        self._ram_view = None
        self.loaded, self.closed = False, False
        self.core = C.CDLL(str(self.core_path))
        self.callbacks = [ENV(self._environment), VIDEO(self._video), AUDIO(self._audio),
                          BATCH(self._batch), POLL(lambda: None), INPUT(self._input)]
        for name, cb in zip(("environment", "video_refresh", "audio_sample", "audio_sample_batch",
                             "input_poll", "input_state"), self.callbacks):
            fn = getattr(self.core, "retro_set_" + name)
            fn.argtypes = [type(cb)]
            fn.restype = None
            fn(cb)
        signatures = {
            "retro_init": ([], None), "retro_deinit": ([], None),
            "retro_run": ([], None), "retro_reset": ([], None),
            "retro_load_game": ([C.POINTER(GameInfo)], C.c_bool),
            "retro_unload_game": ([], None),
            "retro_get_system_av_info": ([C.POINTER(AVInfo)], None),
            "retro_set_controller_port_device": ([C.c_uint, C.c_uint], None),
            "retro_serialize_size": ([], C.c_size_t),
            "retro_serialize": ([C.c_void_p, C.c_size_t], C.c_bool),
            "retro_unserialize": ([C.c_void_p, C.c_size_t], C.c_bool),
            "retro_get_memory_size": ([C.c_uint], C.c_size_t),
            "retro_get_memory_data": ([C.c_uint], C.c_void_p),
        }
        for name, (args, result) in signatures.items():
            fn = getattr(self.core, name)
            fn.argtypes, fn.restype = args, result
        self.core.retro_init()
        self._path = str(self.rom).encode() if self.rom else None
        self._game = GameInfo(self._path, None, 0, None)
        if not self.core.retro_load_game(C.byref(self._game) if self.rom else None):
            self.close()
            raise RuntimeError("FBNeo 未能加载游戏。检查 ROM 版本、文件 CRC 和同目录 pgm.zip。" + " / ".join(self.messages[-3:]))
        self.loaded = True
        if self.deterministic:
            # FBNeo's documented rollback context fixes RTC and includes sync state.
            self.core.retro_serialize_size()
        if self.rom and self.rom.stem.startswith(("kovsh", "orlegend")) and not self.core.retro_get_memory_size(2):
            # FBNeo may return true while displaying an internal ROM error screen.
            self.close()
            raise RuntimeError("游戏未成功启动：核心没有暴露 PGM 主内存，请检查 ROM/BIOS 完整性。")
        self.core.retro_set_controller_port_device(0, 1)
        self.av = AVInfo()
        self.core.retro_get_system_av_info(C.byref(self.av))
        self.fps = self.av.timing.fps or 60.0

    def _environment(self, command, data):
        cmd = command & 0xFFFF
        def put(kind, value):
            if not data:
                return False
            C.cast(data, C.POINTER(kind))[0] = value
            return True
        if cmd == 72 and self.deterministic:
            if data:
                C.cast(data, C.POINTER(C.c_int))[0] = 3
            return True
        if cmd in (9, 30):
            return put(C.c_char_p, self.directory)
        if cmd == 31:
            return put(C.c_char_p, self.save_directory)
        if cmd == 3:
            return put(C.c_bool, True)
        if cmd == 10:
            fmt = C.cast(data, C.POINTER(C.c_int))[0]
            if fmt not in (0, 1, 2):
                return False
            self.pixel_format = fmt
            return True
        if cmd == 11:
            self.descriptors = []
            entries = C.cast(data, C.POINTER(Descriptor))
            for i in range(512):
                d = entries[i]
                if not d.description:
                    break
                self.descriptors.append({"port": d.port, "id": d.id, "label": d.description.decode(errors="replace")})
            return True
        if cmd == 16:
            variables = C.cast(data, C.POINTER(Variable))
            for i in range(4096):
                v = variables[i]
                if not v.key:
                    break
                choices = (v.value or b"").split(b";", 1)[-1].strip().split(b"|")
                self.options.setdefault(v.key, choices[0])
            # Disable cheats and side effects where supported.
            for key in (b"fbneo-allow-depth-32",):
                if key in self.options:
                    self.options[key] = b"enabled"
            return True
        if cmd == 15:
            v = C.cast(data, C.POINTER(Variable)).contents
            v.value = self.options.get(v.key)
            return v.value is not None
        if cmd == 17:
            return put(C.c_bool, False)
        if cmd in (52, 59, 39):
            return put(C.c_uint, 0)  # legacy options/messages; English
        if cmd == 24:
            return put(C.c_uint64, 1 << 1)
        if cmd == 47:
            return put(C.c_int, self.av_enable)
        if cmd == 51:
            return True
        if cmd == 61:
            return put(C.c_uint, 1)
        if cmd == 6 and data:
            message = C.cast(data, C.POINTER(C.c_char_p))[0]
            if message:
                self.messages.append(message.decode(errors="replace"))
                self.messages = self.messages[-30:]
            return True
        if cmd in (8, 18, 34, 35, 37, 42, 87):
            return True
        # Do not claim callbacks/interfaces that this frontend doesn't implement.
        return False

    def _video(self, data, width, height, pitch):
        self.video_callbacks += 1
        if self.headless:
            return
        if data and data != C.c_void_p(-1).value:
            self.video_bytes = C.string_at(data, pitch * height)
            self.video_shape = (width, height, pitch, self.pixel_format)
            self.image = None

    def _audio(self, left, right):
        if self.capture_audio:
            import struct
            self.audio.extend(struct.pack("<hh", left, right))

    def _batch(self, data, frames):
        if self.capture_audio:
            self.audio.extend(C.string_at(data, frames * 4))
        return frames

    def _input(self, port, device, index, button):
        if port or (device & 0xFF) != 1:
            return 0
        return self.mask if button == 256 else int(bool(self.mask & (1 << button)))

    def step(self, buttons=(), frames=1):
        if not self.loaded:
            raise RuntimeError("Game not loaded")
        if not 1 <= frames <= 60000:
            raise ValueError("frames must be 1..60000")
        self.mask = sum(1 << button for button in {BUTTONS[b] for b in buttons})
        for _ in range(frames):
            self.core.retro_run()
            self.frame += 1

    def picture(self):
        if self.video_bytes is None:
            return None
        if self.image is None:
            w, h, pitch, fmt = self.video_shape
            rawmode = {0: "BGR;15", 1: "BGRX", 2: "BGR;16"}[fmt]
            self.image = Image.frombytes("RGB", (w, h), self.video_bytes, "raw", rawmode, pitch, 1)
        return self.image

    def jpeg(self):
        pic = self.picture()
        if pic is None:
            return None
        buffer = io.BytesIO()
        pic.save(buffer, "JPEG", quality=90)
        return buffer.getvalue()

    def save(self):
        size = self.core.retro_serialize_size()
        if not size:
            raise RuntimeError("Core does not support savestates")
        buf = C.create_string_buffer(size)
        if not self.core.retro_serialize(buf, size):
            raise RuntimeError("Savestate failed")
        return buf.raw

    def restore(self, state, frame=0):
        buf = C.create_string_buffer(state)
        if not self.core.retro_unserialize(buf, len(state)):
            raise RuntimeError("Savestate restore failed")
        self.frame, self.mask = frame, 0
        self.audio.clear()
        self.image, self.video_bytes, self.video_shape = None, None, None
        self._ram_view = None

    def ram_view(self):
        """Live read-only RAM, valid until restore/close; ram() remains a snapshot."""
        if self.closed:
            raise RuntimeError("Emulator closed")
        if self._ram_view is None:
            size = self.core.retro_get_memory_size(2)
            ptr = self.core.retro_get_memory_data(2)
            if not size or not ptr:
                return memoryview(b"")
            self._ram_view = memoryview((C.c_ubyte * size).from_address(ptr)).cast('B').toreadonly()
        return self._ram_view

    def ram(self):
        size = self.core.retro_get_memory_size(2)
        ptr = self.core.retro_get_memory_data(2)
        return C.string_at(ptr, size) if size and ptr else b""

    def fingerprint(self):
        return {"state": hashlib.sha256(self.save()).hexdigest(),
                "ram": hashlib.sha256(self.ram()).hexdigest(),
                "video": None if self.headless else hashlib.sha256(self.video_bytes or b"").hexdigest()}

    def close(self):
        if not self.closed:
            self._ram_view = None
            if self.loaded:
                self.core.retro_unload_game()
            self.core.retro_deinit()
            self.loaded, self.closed = False, True
            if self._isolated_save:
                self._isolated_save.cleanup()
