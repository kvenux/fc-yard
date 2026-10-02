"""State heuristics and short-horizon search; no game memory is modified."""
import json
from pathlib import Path
from items import ItemController, validate_items, inventory


class Observer:
    REQUIRED = {"hp", "lives", "score", "progress", "victory", "game_over", "player_x", "player_y"}

    def __init__(self, profile):
        self.profile = json.loads(Path(profile).read_text(encoding="utf-8"))
        if not self.profile.get("verified") or not self.profile.get("evidence"):
            raise ValueError("RAM 观察器未校准：需要实际游戏截图/内存对照证据，不能开始按成绩训练。")
        if not self.REQUIRED <= self.profile.get("fields", {}).keys():
            raise ValueError("观察器缺少血量、生命、得分、进展、胜败或坐标字段")
        for name in ("victory", "game_over"):
            spec = self.profile["fields"][name]
            if not isinstance(spec.get("equals"), int):
                raise ValueError(f"{name} 必须指定实际核对过的终局数值")
        for name, spec in self.profile["fields"].items():
            if not isinstance(spec.get("offset"), int) or spec["offset"] < 0:
                raise ValueError(f"未校准 RAM 偏移：{name}")
            if spec.get("endian", "little") not in ("little", "big"):
                raise ValueError(f"字节序无效：{name}")
        validate_items(self.profile.get("items", {}), self.profile["fields"])

    def read(self, ram):
        result = {}
        for name, spec in self.profile["fields"].items():
            offset, size = spec["offset"], spec.get("size", 1)
            if not isinstance(offset, int) or offset < 0 or size not in (1, 2, 4) or offset + size > len(ram):
                raise ValueError(f"RAM 字段越界或未校准：{name}")
            value = int.from_bytes(ram[offset:offset + size], spec.get("endian", "little"), signed=spec.get("signed", False))
            if "mask" in spec:
                value &= spec["mask"]
            if "equals" in spec:
                value = value == spec["equals"]
            result[name] = value
        for name in ("victory", "game_over"):
            if "equals" not in self.profile["fields"][name]:
                raise ValueError(f"{name} 需要明确的 equals 终局判定")
        result["enemies"] = [
            {"x": result[f"enemy{i}_x"], "y": result[f"enemy{i}_y"],
             "attacking": result.get(f"enemy{i}_attacking", False),
             "boss": result.get(f"enemy{i}_boss", False),
             "vulnerable": result.get(f"enemy{i}_vulnerable", False)}
            for i in range(self.profile.get("enemy_slots", 0))
            if result.get(f"enemy{i}_active") and result.get(f"enemy{i}_hp", 1) > 0
        ]
        result["inventory"] = inventory(self.profile.get("items", {}), result)
        return result


def reward(before, after):
    remaining = {item["id"]: item["count"] for item in after.get("inventory", [])}
    item_cost = sum(max(0, item["count"] - remaining.get(item["id"], item["count"])) * item.get("value", 0)
                    for item in before.get("inventory", []))
    return (1_000_000 * int(after["victory"]) - 1_000_000 * int(after["game_over"])
            + (after["progress"] - before["progress"]) * 10000
            + (after["lives"] - before["lives"]) * 20000
            + (after["hp"] - before["hp"]) * 100
            + (after["score"] - before["score"]) - item_cost)


class Heuristic:
    DEFAULTS = {"attack_period": 8, "attack_on": 4, "align_y": 8,
                "attack_range": 42, "jump_period": 120, "macro_frames": 12,
                "horizon": 36, "mpc": False}

    def __init__(self, config=None):
        self.config = {**self.DEFAULTS, **(config or {})}
        c = self.config
        if not (1 <= c["attack_on"] <= c["attack_period"] <= 120 and
                1 <= c["macro_frames"] <= c["horizon"] <= 300 and
                c["jump_period"] >= 0 and c["align_y"] >= 0 and c["attack_range"] > 0):
            raise ValueError("策略参数超出有效范围")
        self.reason = "等待对局状态"
        self.items = ItemController()

    def action(self, observation, frame):
        c = self.config
        if observation["victory"] or observation["game_over"]:
            self.reason = "对局结束"
            return []
        targets = observation.get("enemies", [])
        keys = []
        if targets:
            x, y = observation["player_x"], observation["player_y"]
            target = min(targets, key=lambda t: abs(t["x"] - x) + 2 * abs(t["y"] - y))
            dx, dy = target["x"] - x, target["y"] - y
            if abs(dy) > c["align_y"]:
                keys.append("down" if dy > 0 else "up")
                self.reason = "对齐最近敌人的纵向位置"
            elif abs(dx) > c["attack_range"]:
                keys.append("right" if dx > 0 else "left")
                self.reason = "接近敌人进入攻击距离"
            else:
                # Briefly face the target, then release movement during attacks.
                if frame % c["attack_period"] == 0:
                    keys.append("right" if dx > 0 else "left")
                self.reason = "面向敌人，节奏攻击"
        else:
            keys.append("right")
            self.reason = "向右推进，寻找下一批敌人"
        if frame % c["attack_period"] < c["attack_on"]:
            keys.append("attack")
        if c["jump_period"] and not observation.get("player_airborne", False) and frame % c["jump_period"] < 2 and any(
                e.get("attacking") and abs(e["x"] - observation["player_x"]) < c["attack_range"]
                and abs(e["y"] - observation["player_y"]) < c["align_y"] for e in targets):
            keys = [k for k in keys if k != "attack"] + ["jump"]
        return keys

    def feedback(self, observation, frame):
        self.items.feedback(observation, frame)

    def choose(self, emulator, observer):
        initial = observer.read(emulator.ram())
        self.items.configure(getattr(observer, "profile", {}).get("items", {}))
        item_keys = self.items.choose(initial, emulator.frame)
        if item_keys is not None:
            self.reason = self.items.reason
            return item_keys, 1
        nominal = self.action(initial, emulator.frame)
        if not self.config["mpc"] or initial["victory"] or initial["game_over"]:
            return nominal, 1
        state, frame = emulator.save(), emulator.frame
        choices = [nominal, ["attack"], ["jump"],
                   ["left", "attack"], ["right", "attack"], ["up"], ["down"], []]
        horizon = self.config["horizon"]
        duration = min(self.config["macro_frames"], horizon)
        best, best_score = nominal, float("-inf")
        audio = emulator.capture_audio
        emulator.capture_audio = False
        try:
            for action in choices:
                emulator.restore(state, frame)
                last = initial
                for t in range(horizon):
                    buttons = action if t < duration else self.action(last, frame + t)
                    emulator.step(buttons)
                    last = observer.read(emulator.ram())
                    if last["victory"] or last["game_over"]:
                        break
                value = reward(initial, last)
                if value > best_score:
                    best, best_score = action, value
        finally:
            emulator.restore(state, frame)
            emulator.capture_audio = audio
        self.reason = "短期前瞻：优先保命、推进和有效攻击"
        return best, duration
