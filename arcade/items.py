"""Closed-loop inventory controller. Requires game-verified RAM and controls.

Nothing here assumes concrete item IDs, menu geometry, or magic RAM addresses.
"""
from collections import deque
from copy import deepcopy

ITEM_FIELDS = {"item_menu_open", "item_cursor", "selected_item_id", "can_use_item", "hp_max", "character"}
SAFE_KEYS = {"up", "down", "left", "right", "attack", "jump", "c", "d"}


def validate_items(spec, fields):
    if not spec.get("enabled"):
        return
    if not spec.get("verified") or not spec.get("evidence"):
        raise ValueError("道具控制未经过实际游戏校准")
    if not ITEM_FIELDS <= fields.keys():
        raise ValueError("道具观察器缺少菜单、光标、选中项、可使用状态、血量上限或角色")
    for name in ("item_menu_open", "can_use_item"):
        if "equals" not in fields[name]:
            raise ValueError(f"{name} 需要明确 equals 状态判定")
    if not 1 <= spec.get("timeout_frames", 90) <= 600 or not 1 <= spec.get("pulse_gap", 4) <= 60:
        raise ValueError("道具等待和按键间隔无效")
    for name in ("open", "confirm", "use", "cancel"):
        keys = spec.get("controls", {}).get(name)
        if not isinstance(keys, list) or not keys or not set(keys) <= SAFE_KEYS or {"attack", "jump"} <= set(keys):
            raise ValueError(f"道具按键未校准或无效：{name}")
    for edge in spec.get("navigation", []):
        if not isinstance(edge.get("from"), int) or not isinstance(edge.get("to"), int) or edge.get("button") not in {"up", "down", "left", "right"}:
            raise ValueError("菜单导航必须是已验证的光标转换")
    seen = set()
    for item in spec.get("catalog", []):
        if not item.get("evidence") or not isinstance(item.get("id"), int) or item["id"] in seen:
            raise ValueError("道具 ID 缺失、重复或缺乏效果证据")
        seen.add(item["id"])
        if item.get("count_field") not in fields or not isinstance(item.get("cursor"), int):
            raise ValueError("道具数量或菜单位置未校准")
        if item.get("trigger") not in ("emergency", "crowd", "boss"):
            raise ValueError("道具使用条件无效")
        if item.get("reserve", 0) < 0 or item.get("value", 0) < 0:
            raise ValueError("道具保留数量/资源价值无效")
        if not item.get("characters") or not item.get("directions") or not item.get("stages"):
            raise ValueError("道具必须明确适用角色、朝向和关卡")
        if "player_facing" not in fields or "stage" not in fields:
            raise ValueError("需要读取实际关卡和人物朝向")
        for effect in item.get("effects", []):
            if effect.get("field") not in fields or effect.get("change") not in ("increase", "decrease", "different"):
                raise ValueError("道具效果验证字段无效")


def inventory(spec, values):
    if not spec.get("enabled"):
        return []
    return [{**item, "count": values[item["count_field"]]} for item in spec["catalog"]]


class ItemController:
    def __init__(self):
        self.spec = {}
        self.target = None
        self.phase = "idle"
        self.started = self.last_press = -100000
        self.retry_after = 0
        self.events = []
        self.pending_event = None
        self.reason = "道具控制未校准"

    def configure(self, spec):
        self.spec = spec or {}

    def _pulse(self, keys, frame):
        if frame - self.last_press < self.spec.get("pulse_gap", 4):
            return []
        self.last_press = frame
        return list(keys)

    def _eligible(self, item, o):
        if item["count"] <= item.get("reserve", 0) or (not o.get("can_use_item") and not o.get("item_menu_open")):
            return False
        if o.get("character") not in item["characters"] or o.get("stage") not in item["stages"] or o.get("player_facing") not in item["directions"]:
            return False
        near = [e for e in o.get("enemies", []) if abs(e["x"] - o["player_x"]) <= item.get("range_x", 96)
                and abs(e["y"] - o["player_y"]) <= item.get("range_y", 24)]
        trigger = item["trigger"]
        if trigger == "emergency":
            return o["hp_max"] > 0 and o["hp"] / o["hp_max"] <= item.get("hp_ratio", .25) and bool(near)
        if trigger == "crowd":
            return len(near) >= item.get("min_enemies", 3)
        return any(e.get("boss") and e.get("vulnerable") for e in near)

    def _next_key(self, current, target):
        queue, visited = deque([(current, None)]), {current}
        while queue:
            cursor, first = queue.popleft()
            if cursor == target:
                return first
            for edge in self.spec.get("navigation", []):
                if edge["from"] == cursor and edge["to"] not in visited:
                    visited.add(edge["to"])
                    queue.append((edge["to"], first or edge["button"]))
        return None

    def feedback(self, o, frame):
        event = self.pending_event
        if event is None:
            return
        if any(o.get(key) != event["context"][key] for key in ("character", "stage", "lives")):
            event.update(status="context_changed_unconfirmed", end_frame=frame)
            self.pending_event, self.target, self.phase = None, None, "idle"
            self.retry_after = frame + self.spec.get("cooldown_frames", 120)
            return
        current = next((i for i in o.get("inventory", []) if i["id"] == event["item_id"]), None)
        if current is not None:
            event["count_after"] = current["count"]
            event["consumed"] = current["count"] < event["count_before"]
        for effect in event["effects"]:
            now = o.get(effect["field"])
            if now is None:
                continue
            old = effect["before"]
            changed = now > old if effect["change"] == "increase" else now < old if effect["change"] == "decrease" else now != old
            if changed:
                effect.update(observed=True, after=now)
        event["effect_observed"] = any(e.get("observed", False) for e in event["effects"])
        if o["victory"] or o["game_over"] or frame - event["frame"] >= self.spec.get("effect_window", 90) or (event["consumed"] and event["effect_observed"]):
            event["status"] = "consumed_effect_observed" if event["consumed"] and event["effect_observed"] else "consumed_unconfirmed_effect" if event["consumed"] else "use_unconfirmed"
            event["end_frame"] = frame
            self.pending_event = None
            self.phase, self.target = "idle", None
            self.retry_after = frame + self.spec.get("cooldown_frames", 120)

    def choose(self, o, frame):
        if not self.spec.get("enabled"):
            return None
        self.feedback(o, frame)
        if o["victory"] or o["game_over"]:
            self.target, self.phase = None, "idle"
            return []
        if self.pending_event:
            self.reason = "已提交道具按键，等待库存与效果核验"
            return [] if not self.pending_event["consumed"] else None
        if self.phase == "idle":
            if o.get("item_menu_open"):
                # Do not attack blindly while the inventory UI owns the controls.
                self.reason = "收起道具栏后继续战斗"
                return self._pulse(self.spec["controls"]["cancel"], frame)
            if frame < self.retry_after:
                return None
            candidates = [i for i in o.get("inventory", []) if self._eligible(i, o)]
            if not candidates:
                return None
            self.target = deepcopy(max(candidates, key=lambda i: i.get("priority", 0)))
            self.started, self.phase = frame, "select"
        target = next((i for i in o.get("inventory", []) if i["id"] == self.target["id"]), None)
        if frame - self.started >= self.spec.get("timeout_frames", 90) or target is None or not self._eligible(target, o):
            self.events.append({"frame": frame, "item_id": self.target["id"], "status": "selection_aborted"})
            self.target, self.phase = None, "idle"
            self.retry_after = frame + self.spec.get("cooldown_frames", 120)
            self.reason = "道具条件已变化，取消使用"
            return self._pulse(self.spec["controls"]["cancel"], frame) if o.get("item_menu_open") else []
        self.reason = f"选取道具：{target.get('name', target['id'])}"
        if o.get("item_menu_open"):
            if o["item_cursor"] != target["cursor"]:
                key = self._next_key(o["item_cursor"], target["cursor"])
                return self._pulse([key], frame) if key else []
            return self._pulse(self.spec["controls"]["confirm"], frame)
        if o["selected_item_id"] != target["id"]:
            return self._pulse(self.spec["controls"]["open"], frame)
        keys = self._pulse(self.spec["controls"]["use"], frame)
        if keys:
            self.pending_event = {"frame": frame, "item_id": target["id"], "name": target.get("name"),
                                  "count_before": target["count"], "count_after": target["count"],
                                  "consumed": False, "effect_observed": False, "status": "input_submitted",
                                  "context": {key: o.get(key) for key in ("character", "stage", "lives")},
                                  "effects": [{**e, "before": o[e["field"]]} for e in target.get("effects", [])]}
            self.events.append(self.pending_event)
            self.phase = "await_effect"
            self.reason = f"使用道具：{target.get('name', target['id'])}（待核验）"
        return keys
