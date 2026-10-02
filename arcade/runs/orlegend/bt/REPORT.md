# 行为树逐关迭代

最新完整成绩为 **123次死亡，第124条命通关，续币61次**。相比前一条已验证纪录150次死亡，减少27次，约18%。正式树为 `arcade/orlegend-bt-deployed.json`，训练中的逐关接受树为 `arcade/orlegend-bt-policy.json`。前四关已新增并复验行为，后四关仍沿用原路线和战斗逻辑。

完整执行与独立回放均从开机开始，零读档。独立回放的RAM、完整存档、死亡计数和逐关死亡数一致；已查看佛祖与结局经文画面。证据：[完整结果](full-v4-screen-01/64-16/result.json)、[独立回放](full-v4-screen-01/64-16/replay.json)、[通关审核](full-v4-screen-01/64-16/clearance-audit.json)。

## 已接受的小步改动

|轮次|同一父策略的局部基线死亡|修改后死亡|改动|
|---|---:|---:|---|
|第1关|1|0|近距离纵向对齐的高血量敌人出现时，优先纵向移动最多8帧，再恢复攻击|
|第2关|4|3|冻结第1关，增加洞穴关段的独立躲避分支，使用该关段的纵向范围|
|第3关|10|7|冻结前两关，给三个首领场景增加纵向躲避分支|
|第4关|18|11|冻结前三关，对近距离普通敌人增加独立躲避分支，最多16帧|

第1关没有消耗道具，过关剩余血量10；冷启动重复和独立回放同为19,851帧、零死亡。第2关新增改动没有改变第1关的19,851帧输入；第3关新增改动没有改变前两关的47,567帧输入。各候选只修改当前关段的分支，较差候选未进入正式树。

四个阶段累计结果为0、3、10、21次死亡。局部表中的基线取自各自的父策略，不能把不同起点的局部基线直接相加。第4关新增改动没有改变前三关的91,428帧输入。

## 整局门槛与结果

前三关的树第一次执行整局为153次死亡，超过前一条已验证纪录150次，已被 `orlegend_bt_global_gate.py` 拒绝。第四关改进后，三个整局候选为123、134、150次死亡；123次的候选通过独立回放和结局验收后才成为正式版本。134次候选未做独立回放，150次候选没有严格改善，未保留为通关版本。

|关卡|前一条完整纪录|行为树完整纪录|
|---|---:|---:|
|1|1|0|
|2|4|3|
|3|9|7|
|4|8|11|
|5|13|14|
|6|12|11|
|7|27|20|
|8|76|57|
|合计|150|123|

第4、5关相对原完整纪录仍有退步，整体改善不等于每一关都更强。因此分为“逐关训练接受”与“整局正式接受”两层门槛，不能用局部成绩替代整局结果。当前也仍不是一命通关。

此前开场/首领房间使用火道具，以及给使用动作增加角色状态条件的候选，均未超过基线，已拒绝。没有为了让行为树看起来有效而保留这些行为。

## 策略如何执行

树由每帧重新检查优先级的 Selector、保存跨帧进度的 Sequence、条件节点和动作节点组成。每帧只产生一组普通按键。高优先级行为能中断低优先级任务；换场景会清理跨帧节点状态。躲避条件使用已读取的敌人血量和相对位置，是距离判断，尚不是Boss出招识别。

例如第1关条件为高血量敌人HP至少100、水平距离小于64、纵向距离小于20；最多移动8帧，目标纵向偏移24，结束后冷却90帧。范围、持续时间、冷却和关段集合都写在JSON里。库存动作有普通按键使用、消耗确认和超时处理，但目前接受的树没有启用道具分支。

原路线迁移为13个动作叶节点。`migration-full-01` 重放原通关的463,420帧输入，并在同一观察和决策帧下比较新旧控制器，零输出差异，13个动作叶节点均有覆盖，最后RAM/存档与原记录一致。这是迁移兼容性证据，不是新策略重新决策通关的成绩。第1关另外由新树直接控制游戏，逐帧与旧控制器比较，也完全一致。

## 自动保留门槛

`orlegend_bt_promote.py` 必须同时满足：

1. 当前关段已通过，累计死亡数严格低于同一父策略基线。
2. 更早接受的关卡输入逐帧完全不变。
3. 关尾库存没有减少。
4. 候选从开机零读档执行，独立回放RAM/存档和死亡计数一致。
5. 再次冷启动执行的RAM/存档和死亡计数相同。

局部门槛不通过就不覆盖训练JSON；整局门槛不通过就不覆盖正式JSON。记录见 `promotions.jsonl`、`summary.json` 与候选目录中的 `global-gate.json`。这些保证仅覆盖当前ROM和已测试开局，不保证其他开局自动更强。

## 代码与复现

- `arcade/behavior_tree.py`：节点执行、跨帧记忆、中断。
- `arcade/orlegend_bt.py`：条件与动作实现。
- `arcade/orlegend-bt-baseline.json`：等价迁移树。
- `arcade/orlegend-bt-policy.json`：逐关接受的训练树。
- `arcade/orlegend-bt-deployed.json`：整局核验后的正式树。
- `arcade/orlegend_bt_train.py`：逐关执行、录像、来源快照、独立回放。
- `arcade/orlegend_bt_promote.py`：严格接受门槛。
- `arcade/orlegend_bt_global_gate.py`：独立的整局接受门槛。

项目根目录执行，输出目录必须不存在：

```powershell
python arcade/test_behavior_tree.py
python arcade/orlegend_bt_train.py --tree arcade/orlegend-bt-policy.json --output arcade/runs/orlegend/bt/reproduce-three --stop-stage 3 --allow-continue --record --frames 150000
python arcade/orlegend_bt_train.py --output arcade/runs/orlegend/bt/reproduce-three --replay
python arcade/orlegend_bt_train.py --tree arcade/orlegend-bt-deployed.json --output arcade/runs/orlegend/bt/reproduce-full --stop-stage 8 --allow-continue --record --frames 700000
python arcade/orlegend_bt_train.py --output arcade/runs/orlegend/bt/reproduce-full --replay
```

独立回放关闭策略，只重放方向、攻击、跳跃、投币、开始等正常输入，不写游戏RAM。训练不渲染画面，整局回放最后结局窗口才渲染供验收。
