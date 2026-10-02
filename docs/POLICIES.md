# 策略、数据与继续训练

| 游戏 | 部署策略 | 已执行轨迹与验收 |
|---|---|---|
| 坦克 | `live-policy.json` + `live-mpc.js` / `live-fire.js`；`reference/web/strategy.js` | `training/human-speed-v4/full-1790835776647.json`；同目录 replay / comparison / episodes |
| 魂斗罗 | `contra/native-train.py`；MPC、只读 RAM、零死亡优先、炮台清除收益 | `contra/runs/native-20261001-201819/result.json`：压缩动作与采样决策；independent/combat/process/video audit |
| 西游 | `arcade/orlegend-bt-deployed.json` + `behavior_tree.py` / `orlegend_bt.py` | `arcade/runs/orlegend/bt/full-v4-screen-01/64-16/`：inputs、tree、manifest、result、replay、clearance audit |
| 风云 | `arcade/kovsh.py` / `kovsh_behavior.py`；首领优先、连击、寻路和前瞻 | `arcade/runs/kovsh/one-life-chapter4-best-prefix-045.jsonl`；`data/kovsh/proof.json` |

策略是代码与 JSON 参数共同构成。执行轨迹是确定性复现证据，不是能适应任何 ROM、种子和敌情的通用模型。历史成绩不代表跨版本成功率。

## 训练命令（在仓库根目录）

先按照 README 安装依赖、核心、ROM。所有候选输出目录必须是新目录。

```sh
# 坦克：直播所用速度/开火策略；具体参数见 --help 或脚本头部
node live-train.cjs
# 魂斗罗：从开机重练一命目标；计算量明显大于固定按键回放
python contra/native-train.py --frames 95000 --stop-stage 8 --zero-death --aggressive
# 重练已部署西游行为树，普通续币开启
python arcade/orlegend_bt_train.py --tree arcade/orlegend-bt-deployed.json --output outputs/orlegend-new --stop-stage 8 --allow-continue --record --frames 700000
python arcade/orlegend_bt_train.py --output outputs/orlegend-new --replay
# 风云：先核验已发布前缀，再根据 --help 继续训练
python tools/replay.py kovsh
python arcade/kovsh.py --help
```

魂斗罗训练曲线保留已认证完整局和原生基线局；西游保存行为树改进的统计与正式验收；风云保存 RAM 数值训练曲线与过段证明。被否决候选、临时截图、存档、视频和大量探针输出留在本地，不放进 Git 历史。需要新的训练起点时从公开输入重新执行产生本地存档，不依赖作者机器里的 checkpoint。

魂斗罗页面的弹幕是预先编排的文本与 AI 相关文案，不是真实在线观众。历史文本来源与改写标记保留在弹幕 JSON 中；未发布外部采集工具、账号凭证或用户 ID。
