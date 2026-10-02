"""Load the pinned FBNeo core and audit a local Feng Yun Zai Qi ROM set.

No ROM assets are downloaded. Run: python arcade/probe.py [path/to/kovsh.zip]
"""
import ctypes as C
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parent


class SystemInfo(C.Structure):
    _fields_ = [("name", C.c_char_p), ("version", C.c_char_p),
                ("extensions", C.c_char_p), ("need_fullpath", C.c_bool),
                ("block_extract", C.c_bool)]


def requirements():
    source = (ROOT / "cores/d_pgm.cpp").read_text(encoding="utf-8")
    block = source.split("static struct BurnRomInfo kovshRomDesc[] = {", 1)[1].split("};", 1)[0]
    rows = []
    for line in block.splitlines():
        if line.lstrip().startswith("//"):
            continue
        match = re.search(r'\{\s*"([^"]+)"\s*,\s*(0x[0-9a-fA-F]+)\s*,\s*(0x[0-9a-fA-F]+)', line)
        if match:
            rows.append({"name": match[1], "size": int(match[2], 16), "crc": f"{int(match[3], 16):08x}"})
    return rows


def main():
    dll = ROOT / "cores/fbneo_libretro.dll"
    core = C.CDLL(str(dll))
    core.retro_get_system_info.argtypes = [C.POINTER(SystemInfo)]
    core.retro_api_version.restype = C.c_uint
    info = SystemInfo()
    core.retro_get_system_info(C.byref(info))
    result = {"core": info.name.decode(), "version": info.version.decode(),
              "api_version": core.retro_api_version(),
              "core_sha256": hashlib.sha256(dll.read_bytes()).hexdigest(),
              "driver": "kovsh", "rom_loaded": False, "gameplay_tested": False,
              "requirements": requirements()}
    rom = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "roms/kovsh.zip"
    result["rom_path"] = str(rom.resolve())
    if rom.is_file():
        with zipfile.ZipFile(rom) as archive:
            entries = {Path(x.filename).name.lower(): x for x in archive.infolist()}
            for row in result["requirements"]:
                entry = entries.get(row["name"].lower())
                row["status"] = "missing" if entry is None else (
                    "ok" if entry.file_size == row["size"] and f"{entry.CRC:08x}" == row["crc"] else "mismatch")
        result["bios_present"] = (rom.parent / "pgm.zip").is_file()
        result["status"] = "rom_audited_not_booted"
    else:
        result["status"] = "missing_rom"
    (ROOT / "runs/probe.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "requirements"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
