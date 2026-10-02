# 魂斗罗：NES 策略训练

现有坦克直播的可迁移部分是：真实按键驱动、候选参数搜索、完整输入记录、独立回放审计。本目录使用 JSNES 2.1.0 提供网页模拟器，并使用原生 FCEUmm 加速前瞻训练。

当前美版初代 ROM 的 MD5 为 `7bdad8b4a7a56a634c9649d20bd3011b`，与 [Contra US 反汇编项目](https://github.com/vermiceli/nes-contra-us) 记录一致。来源与哈希见 `runs/calibration/provenance.json`。切关和最终胜利已在原生核心实际观测并通过独立回放验证。这里的“训练”是参数搜索与模拟器前瞻搜索。

**主动清炮版八关一命通关已核验**：`runs/native-20261001-201819/result.json`。从开机共 77417 帧，依次经过全部八关，死亡 **0 次**；独立进程从开机重放也记录死亡 0 次、全部八关，最终 `GAME_ROUTINE_INDEX = 6`。模拟状态、RAM、画面哈希全部一致，`oneLifeClearVerified = true`。证据见该目录的 `independent-audit.json`。这是当前 ROM 的确定性一命路线，未做跨版本稳定性评估。

本轮保留旧路线前 58988 帧，重新搜索第六关后段至结局。`--aggressive` 在安全候选中奖励实际伤害与击毁，增加转身瞄准、蹲射、向上射击和换层动作；零死亡约束仍优先。独立逐帧核验的炮台击毁数从 **14 增至 17**（第六关 1 → 4），架枪狙击手从 9 增至 10；用时增加 230 帧，约 3.8 秒。击毁要求同一敌人槽位、类型的 HP 从正数降到 0 且当帧实际加分，排除离屏消失。两条路线的 `combat-audit.json` 留存原始事件。曲线单独标注“主动清炮”，回放同步显示清炮动作和累计击毁数。

核心改进：坦克战先退开再转身点射；第六关先越障，再从中层下落走底层通道；区分单次跳跃与连续跳跃，并检查动作结束后 120 帧的生存空间。完整曲线保留失败候选和停滞路径。之前的 5 次死亡通关记录仍保留在 `runs/native-20261001-174625/`。

通关视频：http://127.0.0.1:8787/contra/replay.html ，默认 1× 播放，可切换倍速。视频包含从开机到结局的所有输入，结局追加 1800 帧空输入，导出时再次从开机核对哈希。复核命令：`python contra/native-replay.py contra/runs/native-20261001-201819/result.json`。一命网页验证：`node contra/verify-clear.cjs --one-life`。

回放支持 1×、1.5×、2×、3×、4×；勾选“游戏声音”播放原生核心产生的音乐和音效。`native-video.py` 捕获 48 kHz 双声道音频，与 30 fps 回放时长对齐并合成 `full-clear-audio.mp4`，拖动进度与倍速由同一视频元素同步处理，倍速保持音高。初始静音以支持自动播放。

底部为三轨滚动弹幕，随视频帧移动，暂停、拖动、倍速同步；不代表本直播间的实时观众消息或热度。当前共 **276 条**：来自用户本机 B 站弹幕文件的 **162 条**、基于这些真人弹幕扩写的 **72 条**，以及原有 **42 条 AI 相关预设文案**；其余 216 条自写弹幕已移除。全文不重复、逗号换空格，过滤含“稳”“硬”的文案；每轨前一条离开后才进入下一条。源视频是 BV12t411n7wg《93超级魂》改版，目标是 Contra US 原版，已排除改版地形、无敌撞 Boss、不丢枪、水下八关、UP 主、封面、引流和不匹配规则等内容。931 条原始弹幕筛出 200 条候选，162 条排入；其余候选因轨道容量排除。通用反应按源弹幕推断的关卡范围重新分布，**不是源视频逐帧同步**；武器和具体走位匹配目标回放的实际状态，通关庆祝置于已核验结局之后。

导入命令：`node contra/import-bilibili-danmaku.cjs "contra/danmaku-sources/BV12t411n7wg/original.txt" contra/runs/native-20261001-201819`。筛选清单见 `bilibili-danmaku-selection.json`；原文件副本、SHA256、每条去留理由、原时间与映射时间见 `danmaku-sources/BV12t411n7wg/migration-report.json` 和 `original.txt`。每条导入弹幕保存原文及来源行号。`danmaku-ai-retained.json` 保留原有 42 条 AI 文案和时间，`danmaku-migration.json` 固定本次迁移配置；`build-danmaku.cjs` 对当前运行自动走迁移流程，避免恢复旧的非 AI 自写内容。

扩写库为 `bilibili-danmaku-adaptations.json`：每组记录参考原弹幕和适用范围；部署条目用 `category: adapted`、`authored: true` 区别于直接导入，并保留参考原文、行号和文件哈希。新增文案优先填充安静段，关卡话题留在对应关卡、庆祝留在结局之后，不移动原有 162 条导入弹幕或 42 条 AI 接话。当前平均间隔约 4.7 秒、最长空档 9 秒；扩写去留明细保存于迁移报告的 `adaptationAudit`。

`audit-process.py <result.json>` 独立开机重放，记录逐帧起跳、落地、武器和关卡变化，以及每秒位置和附近敌人快照，末端核对完整状态哈希；本轮记录 1031 个事件、1290 个快照。`verify-danmaku.cjs` 验证导入原文、扩写来源、AI 文案保留、轨道间隔、移动、暂停、跳转清理和手机布局。

训练曲线：http://127.0.0.1:8787/contra/training.html 。每完成一个候选自动更新，展示最远关卡、生命损失、模拟帧数及同关进度曲线，并区分候选原始表现与回放通过的历史最好表现。数据和 CSV 在 `runs/learning-curve.json`、`runs/episodes.csv`，`node contra/report.cjs` 可重建。没有数据时显示空态，不生成示例成绩。ROM、核心、观察器与预算不同的实验分别成组。

通关回放页面沿用坦克直播页的红白机机身与完整手柄，按视频帧同步显示真实方向、B 射击和 A 跳跃。START 播放或暂停，SELECT 跳到下一关；支持八关选择、倍速、进度拖动、纯净画布、全屏和循环播放。当前关卡、得分、武器来自独立开机回放导出的 `replay-telemetry.json`，导出末端再次核对完整状态哈希；策略卡展示逐关路线说明。`python contra/export-replay-telemetry.py <result.json>` 重建数据，`node contra/verify-famicom-replay.cjs` 验证真实按键同步、手柄操作及手机布局。

2026-10-01 首次实训：两轮共 24 个候选，24/24 独立回放的状态、RAM、像素哈希一致，完整通关 0/24，均未通过第一关。第一轮最高首关滚动进度 2263，第二轮为 2481（提升约 9.6%，不是通关比例）。第二轮使用 `refinement-grid.json`；优胜参数为射击周期 8、保持 3 帧，跳跃周期 30、保持 8 帧。`runs/deployed-policy.json` 保留优胜候选来源，网页“载入项目 ROM 与策略”读取 `runs/latest-policy.json`。同一起点的确定性搜索不等于独立成功率抽样。

## 直播与校准

运行 `npm start`，打开 http://127.0.0.1:8787/contra/live.html 。选择本地 `.nes`，手动开始游戏；Z 对应 A、X 对应 B。保存校准样本会下载截图、2 KB RAM、模拟器存档、ROM/核心 SHA256 与从开机开始的输入。网页不上传 ROM，无音频输出。

当前 `observation.json` 适配上述美版原版，`node contra/calibrate.cjs` 重跑首关/自然死亡校准。更换 ROM 时需复制 `observation.template.json` 为 `observation.json`，重新核对不同场景样本。模板不可直接训练。必须核对：

- `stage` 为关卡标识；`stageOrder` 是实际 ROM 的通关顺序，`stageModes` 映射为 `side`（横版）、`base`（纵深）、`vertical`（向上攀登）。
- `progress` 是同一关内越大越好的进度，当前为屏幕序号 × 256 + 滚动偏移；`x/y` 为玩家坐标；当前 `lives` 是备用生命（0 表示最后一命），失败由独立字段判定，死亡次数按死亡状态进入次数记录。
- `status`、`playing`、`terminal` 分别识别游戏中、Game Over、最终胜利；终局不可只由分数或时间推测。
- 纵深场景可添加归一化的 `barrierOpen` 字段（1 表示屏障开放）；攀登场景可添加 `targetAbove`（1 表示可向上射击）。缺少这些观察量时，策略能力有限。
- 开局等待与 START 序列必须在目标 ROM 实测。`evidence` 区分实际运行样本和对应版本源码依据。当前 `verified` 代表地址映射已核对，并不代表每种状态都已经实战经历；具体边界见 `verificationScope`。完整通关仍要求真实运行及独立回放，不能拿源码依据冒充通关成绩。

## 搜索与核验

```powershell
node contra/train.cjs --rom "C:\Games\Contra.nes" --preflight
node contra/train.cjs --rom "C:\Games\Contra.nes" --frames 18000 --candidates 12
node contra/train.cjs --frames 18000 --candidates 12 --grid contra/refinement-grid.json
```

`--frames` 是每候选开局后游戏帧预算，18000 帧约 5 分钟，仅适合初筛。默认组合为射击周期 6/10 帧 × 跳跃周期 45/70/100 帧 × 跳跃保持 8/20 帧。从同一 ROM 开机状态独立运行全部候选，比较已验证胜利、最远关卡、该关进度、生命损失和时间。不续关、不修改 RAM、不自动增加生命。

每个候选在另一台新建 JSNES 实例中重放全部按键，对比模拟状态、RAM、像素哈希。只有回放一致的候选参与优选；`fullGameClearVerified` 还要求从首关顺序经过所有关卡并观察到经校准的最终胜利状态。开发中单 ROM 的确定性结果不代表跨版本稳定性。

`runs/search-*/` 保存源码快照、清单、候选参数、压缩逐帧输入、每 120 帧观察轨迹、回放哈希和优选结果。网页可载入 `best-policy.json` 实时执行，或载入 `candidate-N.json` 纯按键回放。配置 `stagePolicies` 可逐关覆盖参数。

## 精确模拟器前瞻

`node contra/mpc-run.cjs --frames 8000 --stop-stage 1` 从开机运行短期动作搜索，在复制的模拟器状态中比较移动、射击和不同起跳相位。优先避免死亡，结合实际滚动、位置、得分和目标血量选择动作。只提交普通按键，不改变游戏 RAM、规则或生命。存档恢复进行深拷贝，避免模拟器反向修改用于其他候选的快照；实际 ROM 三次分支重复验证见 `runs/branch-verification.json`。

`--resume <已有 result.json> --prefix-frames N` 先从开机重放已有核验路径的前 N 帧，再继续搜索，适合断崖、Boss 等局部训练。真实提交轨迹始终连续，最后在全新的模拟器里重放整个路径，核对状态、RAM、像素。`--frames` 是含前缀的总帧上限；到达 `--stop-stage`（0 起始的目标关卡）是阶段练习终点，不是完整通关。

`runs/mpc-*/` 保存前瞻源码、候选评分、阶段截图、完整按键与核验结果。训练曲线将前瞻与早期参数搜索分组展示，`model-status.json` 提供最近进度。浏览器可以载入其 `result.json` 纯按键回放；实时 MPC 搜索在 Node 进程中执行。

JSNES 首次前瞻训练无伤通过首关，并从开机回放验证状态、RAM、像素一致：`runs/mpc-2026-10-01T08-07-55-820Z/result.json`（5421 帧，含开局）。进一步保留的第二关路径见 `runs/latest-model.json`；直播页“JSNES 前瞻回放”读取该核心的最远路径。八关完整路径使用下面的原生核心。

第二关的激光射击对照见 `runs/laser-fire-comparison.json`：同一状态和 160 帧窗口，8 帧连点周期使核心血量保持 8，持续按住开火使血量下降到 3。`reference/bank6.asm` 的 `fire_weapon_routine_l` 说明新按下 B 会重建激光；前瞻因此对 L 武器持续按住 B，其余武器沿用脉冲射击。纵深瞄准还考虑弹道向中央收束，并以实际模拟伤害验证动作。

当前原生前瞻搜索已得到完整八关路径。模拟分支会评估死亡、弹道伤害、跳跃时机和落点；各轮源码快照和完整输入保留在运行目录中。

## 原生模拟器训练

一命训练使用 `--zero-death`：首个死亡事件立即结束该候选，得分加命不能抵消死亡。通过条件为全八关结局、训练记录死亡 0 次，且独立进程从开机重放也统计到死亡 0 次和全部关卡。`oneLifeClearVerified` 单独记录此结论，普通通关结果不等于一命通关。实验组按 `objective` 分开，原通关路径的五个死亡位置见 `runs/death-audit.json`。

当前策略采用安全动作前瞻、动作终点之后的生存检查、16 帧组合躲避、平台下落、武器对应的开火方式及 Boss 原地转身射击。纵深房间会比较所有核心与瞄准偏移，避免长期锁定无法命中的单一目标。

一命路线的坦克战会比较“退到安全距离 → 转身 → 点射”完整组合，并验证击毁后仍可生存。零死亡模式把动作末端的继续生存检查延长到 120 帧，第六关保留最多 24 条分层路线。高度读取包含 `PLAYER_HIDDEN` 高字节，避免把跳出屏幕上沿误判为掉入深坑。失败路径和独立回放结果同样留档；加命不改变死亡次数。

`python contra/native-train.py --resume contra/runs/native-20261001-164106/result.json --horizon 240 --frames 20000 --stop-stage 3` 从开机重放已核验的原生路径后继续瀑布关训练。`--horizon` 是每个候选动作的前瞻帧数，`--frames` 包含已有路径。运行目录内创建 `stop.request` 可在规划边界停止并完成核验。

原生 FCEUmm 与 JSNES 的帧行为不同，不能互换输入路径。原生结果放在 `runs/native-*/`，每次结束由独立 Python 进程从开机重放，比较模拟状态、RAM、画面哈希。`runs/native-20261001-163735/result.json` 已连续无伤通过前两关（10623 帧），三项哈希一致。曲线按模拟器和训练预算分组，原生最新结果见 `runs/latest-native.json`。浏览器内的 JSNES 回放按钮只载入 JSNES 路径。

前三关核验记录：`runs/native-20261001-165430/result.json`，从开机共 22165 帧，关卡顺序 `[0,1,2,3]`，死亡 2 次，进入第四关时剩 3 条命；独立回放三项哈希一致。瀑布关使用较长动作前瞻和最多四段的组合搜索跨平台，Boss 使用开口时的实际 HP 与闭口时的保存 HP 计算伤害。此记录尚未完整通关。

前四关核验记录：`runs/native-20261001-170717/result.json`，33262 帧，累计死亡 2 次，剩 3 条命、激光武器；独立开机回放三项哈希一致。双头 Boss 的 HP 读取 `ENEMY_VAR_4`，结合固定合体位置瞄准与分段攻击/躲避搜索。

前五关核验记录：`runs/native-20261001-171509/result.json`，43097 帧，累计死亡 4 次，进入第六关时剩 2 条命；独立开机回放三项哈希一致。第六关火焰区采用较长前瞻、分段躲避、末端继续生存检查，以及游戏原有的“下 + 跳”平台下落动作。实际新进展以曲线和 `native-status.json` 为准。

第四关探索曾出现声音滤波器 `FAC2` 累加值不一致（RAM 和像素一致），原失败记录保留。`native-recertify.py` 只允许该已识别字段内的差异，再比较两次独立开机回放的全部状态字节；生成的记录标记为“同路径复核”，不代表新的策略改善。不掩码或忽略存档差异来伪装哈希通过。

`node contra/selftest.cjs` 使用自制小型 NES 测试程序验证按键进入模拟核心及确定性回放，并检查无校准时拒绝训练；不使用魂斗罗 ROM，不是游戏成绩测试。
