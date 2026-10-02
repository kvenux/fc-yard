"""Plot recorded candidate evaluations. Never infer a score from a reward proxy."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path, help="JSON list of completed candidate results")
    parser.add_argument("--metric", choices=("score", "reward"), default="score")
    parser.add_argument("--game", required=True, help="Actual game name, printed on the figure")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    records = json.loads(args.results.read_text(encoding="utf-8-sig"))
    if not isinstance(records, list):
        parser.error("results must be a list of completed evaluations")
    points, excluded = [], []
    for index, row in enumerate(records, 1):
        if row.get("replay_equal") is not True:
            excluded.append({"evaluation": index, "reason": "replay_not_verified"})
            continue
        value = row.get("after", {}).get("score", row.get("score")) if args.metric == "score" else row.get("reward")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            excluded.append({"evaluation": index, "reason": f"missing_{args.metric}"})
            continue
        points.append({"evaluation": index, "value": value, "config": row.get("config"),
                       "frames": row.get("frames"), "scope": row.get("scope", "unknown")})
    if not points:
        parser.error(f"没有经回放核验的 {args.metric} 数据；不能用 reward 代替游戏得分。")
    # Mixing different time budgets/starting states creates misleading comparisons.
    # This plot preserves all points and prints the observed budgets for assessment.
    output = args.output or args.results.parent / f"{args.metric}-curve"
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    xs = [p["evaluation"] for p in points]
    ys = [p["value"] for p in points]
    best = []
    for value in ys:
        best.append(max(value, best[-1]) if best else value)
    label = "游戏得分" if args.metric == "score" else "训练评价值（非游戏分数）"
    fig, ax = plt.subplots(figsize=(10, 5.4), constrained_layout=True)
    ax.plot(xs, ys, "o-", color="#31688e", linewidth=1.5, label="各候选实际记录")
    ax.step(xs, best, where="post", color="#b45232", linewidth=1.5, label="截至该次的最高值")
    ax.set(title=f"{args.game} · {label}", xlabel="候选评估序号（参数搜索）", ylabel=label)
    ax.grid(alpha=.2)
    ax.legend()
    scopes = sorted({p["scope"] for p in points})
    fig.text(.01, -.045, f"范围：{', '.join(scopes)}；仅含回放一致的记录；本图不证明整局通关。", fontsize=9)
    fig.savefig(output.with_suffix(".png"), dpi=160, bbox_inches="tight")
    fig.savefig(output.with_suffix(".svg"), bbox_inches="tight")
    plt.close(fig)
    report = {"game": args.game, "metric": args.metric, "source": str(args.results.resolve()),
              "source_sha256": hashlib.sha256(args.results.read_bytes()).hexdigest(),
              "points": points, "excluded": excluded, "full_game_clear_verified": False}
    output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(output.with_suffix(".png").resolve()))


if __name__ == "__main__":
    main()
