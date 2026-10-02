"""Locate candidate RAM fields by comparing captured ram.bin files.

Example: python arcade/calibrate.py --samples a/ram.bin=100 b/ram.bin=90 --size 2
Candidates are NOT automatically installed as verified game observations.
"""
import argparse
import json
from pathlib import Path


def find_fields(samples, size, endian):
    if len({len(data) for data, _ in samples}) != 1:
        raise ValueError("样本 RAM 大小不一致")
    return [offset for offset in range(len(samples[0][0]) - size + 1)
            if all(int.from_bytes(data[offset:offset + size], endian) == expected
                   for data, expected in samples)]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--samples", nargs="+", required=True, help="path/to/ram.bin=observed_value")
    p.add_argument("--size", type=int, choices=(1, 2, 4), default=2)
    p.add_argument("--endian", choices=("little", "big"), default="little")
    args = p.parse_args()
    if len(args.samples) < 2:
        p.error("至少需要两个独立画面与 RAM 对照样本")
    samples = []
    for arg in args.samples:
        path, value = arg.rsplit("=", 1)
        samples.append((Path(path).read_bytes(), int(value, 0)))
    offsets = find_fields(samples, args.size, args.endian)
    print(json.dumps({"candidate_offsets": offsets, "size": args.size, "endian": args.endian,
                      "verified": False, "note": "候选需在独立场景、受伤、死亡、切关时继续核对"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
