"""Interface tests using the open-source 2048 core, not the target game's ROM."""
import json
from emulator import Emulator, ROOT
from policy import Observer, Heuristic
from calibrate import find_fields


def main():
    report = {"scope": "frontend_only_2048", "kovsh_gameplay_tested": False}
    e = Emulator(core=ROOT / "cores/2048_libretro.dll")
    try:
        e.step([], 10)
        initial = e.save()
        actions = [["right"], [], ["down"], [], ["left"], [], ["up"], []] * 10
        e.restore(initial)
        for keys in actions:
            e.step(keys)
        expected = e.fingerprint()
        e.picture().save(ROOT / "runs/host-test.png")
        e.restore(initial)
        for keys in actions:
            e.step(keys)
        actual = e.fingerprint()
        assert expected == actual, "state/pixels replay mismatch"
        report["native_replay"] = {"frames": len(actions), "equal": True, "fingerprint": actual}
        observation = {"hp": 100, "lives": 2, "score": 0, "progress": 0,
                       "victory": False, "game_over": False, "player_x": 10, "player_y": 20,
                       "enemies": [{"x": 50, "y": 60}]}
        heuristic = Heuristic()
        assert "down" in heuristic.action(observation, 1)
        assert "coin" not in heuristic.action(observation, 1)
        class SyntheticObserver:
            def read(self, _):
                return observation
        # Test that speculative branches do not mutate the committed core state.
        before = e.save()
        frame = e.frame
        Heuristic({"mpc": True, "horizon": 12}).choose(e, SyntheticObserver())
        assert e.save() == before and e.frame == frame
        report["speculative_state_restored"] = True
        try:
            Observer(ROOT / "observation.template.json")
            raise AssertionError("unverified profile was accepted")
        except ValueError:
            report["unverified_profile_rejected"] = True
        assert find_fields([(b"\x00\x64\x00", 100), (b"\x00\x5a\x00", 90)], 2, "little") == [1]
        report["calibration_scan"] = True
    finally:
        e.close()
    (ROOT / "runs/selftest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
