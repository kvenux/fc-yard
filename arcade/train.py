"""Parameter search from an audited checkpoint and independent input replay.

Results from checkpoints are practice results, never evidence of a full-game clear.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import time

from emulator import Emulator, ROOT
from policy import Observer, Heuristic, reward


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_profile(observer, emulator):
    p = observer.profile
    if p.get("core_sha256") != sha(emulator.core_path) or p.get("rom_sha256") != sha(emulator.rom):
        raise ValueError("观察器与当前模拟核心/ROM 的哈希不一致，需要重新校准")


def episode(emu, observer, policy, state, budget, trace_path, snapshot_dir):
    emu.restore(state)
    before = observer.read(emu.ram())
    if before["victory"] or before["game_over"]:
        raise ValueError("起始存档已处于终局，不能作为训练样本")
    actions, after = [], before
    began = time.perf_counter()
    with trace_path.open("w", encoding="utf-8") as stream:
        while emu.frame < budget:
            keys, duration = policy.choose(emu, observer)
            for _ in range(min(duration, budget - emu.frame)):
                emu.step(keys)
                after = observer.read(emu.ram())
                policy.feedback(after, emu.frame)
                row = {"frame": emu.frame, "buttons": keys, "reason": policy.reason,
                       "item_phase": policy.items.phase}
                actions.append(row)
                stream.write(json.dumps(row) + "\n")
                if emu.frame % 600 == 0:
                    emu.picture().save(snapshot_dir / f"frame-{emu.frame:07d}.png")
                if after["victory"] or after["game_over"]:
                    break
            if after["victory"] or after["game_over"]:
                break
    fingerprint = emu.fingerprint()
    final_state = emu.save()
    emu.picture().save(snapshot_dir / "final.png")
    elapsed = time.perf_counter() - began
    # Replay without calling the policy and compare core state, RAM, and pixels.
    emu.restore(state)
    for row in actions:
        emu.step(row["buttons"])
    replay = emu.fingerprint()
    return {"frames": len(actions), "wall_seconds": elapsed, "before": before, "after": after,
            "reward": reward(before, after), "victory_observed": bool(after["victory"]),
            "full_game_clear_verified": False, "scope": "checkpoint_practice",
            "item_events": policy.items.events,
            "replay_equal": fingerprint == replay, "expected": fingerprint, "replay": replay}, final_state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", default=str(ROOT / "roms/kovsh.zip"))
    parser.add_argument("--profile", default=str(ROOT / "observation.json"))
    parser.add_argument("--state", required=True)
    parser.add_argument("--frames", type=int, default=18000)
    parser.add_argument("--mpc", action="store_true")
    args = parser.parse_args()
    if args.frames < 1:
        parser.error("--frames must be positive")
    observer = Observer(args.profile)
    state = Path(args.state).read_bytes()
    out = ROOT / "runs" / time.strftime("search-%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=False)
    emu = Emulator(args.rom)
    try:
        verify_profile(observer, emu)
        meta = {"core_sha256": sha(emu.core_path), "rom_sha256": sha(args.rom),
                "profile_sha256": sha(args.profile), "state_sha256": sha(args.state),
                "source_sha256": {name: sha(ROOT / name) for name in ("emulator.py", "policy.py", "items.py", "train.py")},
                "scope": "checkpoint_practice", "frames_budget": args.frames}
        (out / "manifest.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        (out / "initial.state").write_bytes(state)
        winners = []
        for index, (period, distance, jump) in enumerate(itertools.product((6, 10), (32, 48), (0, 120))):
            config = {"attack_period": period, "attack_on": period // 2,
                      "attack_range": distance, "jump_period": jump, "mpc": args.mpc}
            directory = out / f"candidate-{index:02d}"
            directory.mkdir()
            report, final = episode(emu, observer, Heuristic(config), state, args.frames,
                                    directory / "inputs.jsonl", directory)
            report["config"] = config
            (directory / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            (directory / "final.state").write_bytes(final)
            print(json.dumps({"candidate": index, "reward": report["reward"], "replay_equal": report["replay_equal"]}), flush=True)
            if report["replay_equal"]:
                winners.append((report["reward"], index, config))
        if not winners:
            raise RuntimeError("所有候选回放不一致，不部署策略")
        _, index, config = max(winners, key=lambda item: item[0])
        (out / "best-policy.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
        (out / "summary.json").write_text(json.dumps({"best_candidate": index, "scope": "checkpoint_practice",
                                                       "full_game_clear_verified": False}, indent=2), encoding="utf-8")
        print(str(out))
    finally:
        emu.close()


if __name__ == "__main__":
    main()
