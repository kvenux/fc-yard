"""Synthetic control-flow tests, not gameplay or item-effect evidence."""
from copy import deepcopy
import json
import unittest
from emulator import ROOT, BUTTONS
from items import ItemController, validate_items
from policy import Heuristic


def fixture():
    item = {"id": 7, "name": "synthetic-item", "cursor": 1, "count_field": "count7", "count": 2,
            "trigger": "crowd", "min_enemies": 2, "characters": [1], "stages": [1], "directions": [1],
            "reserve": 1, "priority": 1, "evidence": ["SYNTHETIC TEST ONLY"],
            "effects": [{"field": "enemy_hp_sum", "change": "decrease"}]}
    spec = {"enabled": True, "verified": True, "evidence": ["SYNTHETIC TEST ONLY"],
            "controls": {"open": ["c"], "confirm": ["c"], "use": ["d"], "cancel": ["c"]},
            "navigation": [{"from": 0, "to": 1, "button": "right"}], "catalog": [item],
            "pulse_gap": 4, "timeout_frames": 20, "effect_window": 10, "cooldown_frames": 60}
    o = {"hp": 100, "hp_max": 100, "lives": 2, "character": 1, "stage": 1, "player_facing": 1,
         "victory": False, "game_over": False, "can_use_item": True, "item_menu_open": False,
         "item_cursor": 0, "selected_item_id": 0, "inventory": [item], "player_x": 0, "player_y": 0,
         "enemies": [{"x": 30, "y": 0}, {"x": 40, "y": 0}], "enemy_hp_sum": 100}
    c = ItemController()
    c.configure(spec)
    return c, o


class ItemTests(unittest.TestCase):
    def test_menu_selection_and_actual_feedback(self):
        c, o = fixture()
        self.assertEqual(c.choose(o, 0), ["c"])
        o.update(item_menu_open=True, can_use_item=False)
        self.assertEqual(c.choose(o, 1), [])
        self.assertEqual(c.choose(o, 4), ["right"])
        o["item_cursor"] = 1
        self.assertEqual(c.choose(o, 8), ["c"])
        o.update(item_menu_open=False, can_use_item=True, selected_item_id=7)
        self.assertEqual(c.choose(o, 12), ["d"])
        self.assertEqual(c.events[-1]["status"], "input_submitted")
        self.assertFalse(c.events[-1]["consumed"])
        o["inventory"][0]["count"] -= 1
        o["enemy_hp_sum"] = 50
        c.feedback(o, 13)
        self.assertEqual(c.events[-1]["status"], "consumed_effect_observed")
        self.assertIsNone(c.choose(o, 14))

    def test_empty_reserve_and_changed_target(self):
        c, o = fixture()
        o["inventory"][0]["count"] = 1
        self.assertIsNone(c.choose(o, 0))
        o["inventory"][0]["count"] = 2
        c.choose(o, 1)
        o["enemies"] = []
        self.assertEqual(c.choose(o, 2), [])
        self.assertEqual(c.events[-1]["status"], "selection_aborted")

    def test_boss_must_be_vulnerable(self):
        c, o = fixture()
        o["inventory"][0]["trigger"] = "boss"
        o["enemies"] = [{"x": 20, "y": 0, "boss": True, "vulnerable": False}]
        self.assertIsNone(c.choose(o, 0))
        o["enemies"][0]["vulnerable"] = True
        self.assertEqual(c.choose(o, 1), ["c"])

    def test_no_inventory_change_is_not_success(self):
        c, o = fixture()
        o["selected_item_id"] = 7
        self.assertEqual(c.choose(o, 0), ["d"])
        for t in range(1, 10):
            self.assertEqual(c.choose(o, t), [])
        c.feedback(o, 10)
        self.assertEqual(c.events[-1]["status"], "use_unconfirmed")
        self.assertIsNone(c.choose(o, 11))

    def test_consumption_without_effect_and_death(self):
        c, o = fixture()
        o["selected_item_id"] = 7
        c.choose(o, 0)
        o["inventory"][0]["count"] = 1
        c.feedback(o, 10)
        self.assertEqual(c.events[-1]["status"], "consumed_unconfirmed_effect")
        c, o = fixture()
        o["selected_item_id"] = 7
        c.choose(o, 0)
        o["lives"] -= 1
        o["inventory"][0]["count"] = 0
        c.feedback(o, 1)
        self.assertEqual(c.events[-1]["status"], "context_changed_unconfirmed")
        self.assertFalse(c.events[-1]["consumed"])

    def test_stuck_menu_never_uses_wrong_item(self):
        c, o = fixture()
        c.choose(o, 0)
        o.update(item_menu_open=True, item_cursor=99)
        for t in range(1, 20):
            self.assertNotIn("d", c.choose(o, t))
        c.choose(o, 20)
        self.assertEqual(c.events[-1]["status"], "selection_aborted")

    def test_unverified_controls_rejected(self):
        c, _ = fixture()
        spec = deepcopy(c.spec)
        spec["verified"] = False
        with self.assertRaises(ValueError):
            validate_items(spec, {})

    def test_no_unintentional_attack_jump_combination(self):
        _, o = fixture()
        o["enemies"][0]["attacking"] = True
        keys = Heuristic().action(o, 0)
        self.assertFalse({"attack", "jump"} <= set(keys))
        self.assertEqual(BUTTONS["c"], 1)
        self.assertEqual(BUTTONS["d"], 9)


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ItemTests))
    (ROOT / "runs/item-tests.json").write_text(json.dumps({"scope": "synthetic_item_controller",
        "tests": result.testsRun, "passed": result.wasSuccessful(), "kovsh_gameplay_tested": False}, indent=2), encoding="utf-8")
    raise SystemExit(0 if result.wasSuccessful() else 1)
