# 三国战纪：风云再起 AI 直播实验

目标：kovsh，原版 V104 CN，IGS PGM。真实 FBNeo 模拟核心 + 启发式控制 + 短期模型前瞻 + 网页直播。

## 当前状态

已经实现逐帧按键、截图、存档恢复、RAM 读取、参数搜索、纯按键回放核对和 1080×1920 直播页。前端接口用独立开源 2048 核心完成原生执行测试，80 帧回放的状态与像素一致，模拟分支结束后恢复原状态的测试通过。证据：runs/selftest.json。

**ROM 已下载并通过 12 个芯片文件 CRC 校验，真实游戏已推进到第七关司马懿，尚未一币通关。** 当前路线已击败吕蒙、许褚、黄盖、曹丕、魏延。全程只投初始一币，不续币、不改血量/计时/道具。分段搜索允许反复训练，最终验收必须从开机连续按键重放到结局。

最新完整开机前缀核验为 `runs/kovsh/roof-entry-cold/report.json`：166,690 帧、1 次投币，所有连接节点 RAM、观察结果和画面一致。后续屋顶存档路线在完整开机回放中发生分歧（`two-life-sima-poweron/report.json`），因此局部击败司马懿不算有效进度证明，且该局未清完房间。已增加 `kovsh.py --poweron-prefix <inputs.jsonl>`，从开机连续执行已验证前缀后直接接策略，正式实例不读档，结束后从开机独立复核。

预演使用独立模拟器进程，正式对局仅提交普通按键，不修改游戏 RAM。每轮结束后独立回放，`replay_equal` 记录完整哈希核对，`trajectory_equal` 记录抽样画面及冻结观察器字段核对。终局尚未校准，不能把场景码当作通关证明。

训练直播运行 `python arcade/training_live.py --port 8795`，访问 http://127.0.0.1:8795/live.html?capture=1 。只显示正式执行帧，不显示预演分支。已完成轮次的得分曲线：`runs/kovsh/score-curve.png`。

```powershell
python arcade/kovsh.py --bootstrap
python arcade/kovsh.py --frames 300000 --config '{"period":4,"distance":32,"align":8,"jump":0,"route_v2":true,"focus_boss":true,"mpc":true,"horizon":180,"commit":60,"fast_preview":true,"vision_navigation":true}'
```

各轮目录保存输入、源码快照、核心/ROM/起点哈希、每 600 帧截图与存档、得分样本及独立回放结果。缺少终局证据时不会宣称通关。当前直播无声音。

## 无画面批量训练

`kovsh_batch.py` 并行运行原生核心，每个试局只在起点载入一次状态，之后只提交按键。禁用画面生成，不按墙钟限速；最佳候选再开启渲染重放验证。纯规则粗筛与前瞻搜索分开统计，不能把节点试局数当作整局通关次数。

```powershell
python arcade/kovsh_batch.py --state arcade/runs/kovsh/two-life-roof-001/frame-017400.state --output arcade/runs/kovsh/new-batch --workers 4 --trials 256 --frames 10000 --boss-slot 1 --randomize
```

强策略试局可用 `--techniques --ground-alignment` 或 `--committed`，省略 `--randomize`。当前面板：http://127.0.0.1:8795/batch.html 。各批目录保存配置、逐帧输入、样本、得分、状态和 `training-curve.png`。基础 48 次粗筛用时 21.5 秒，合计 66,044 帧（约 52 倍游戏速度）；全部失败，速度提升不等于策略成功。前瞻搜索开销单独计量。

观察器现在区分画面 y、地面 y 和跳跃高度；`ground_alignment` 用地面位置对齐，避免追逐跳起敌人的画面高度。训练路线另包含已实测的升降台斜跳、河岸侧移和栏杆跳跃动作。最终完整路线由 `kovsh_verify_chain.py` 从开机验证，不能以恢复存档的局部回放替代。

## 启动直播

```powershell
python -m pip install -r arcade/requirements.txt
python arcade/serve.py
```

访问 http://127.0.0.1:8788/live.html 。OBS 使用 http://127.0.0.1:8788/live.html?capture=1 ，宽 1080，高 1920。Esc 返回控制台。

当前会话的新版预览运行在 http://127.0.0.1:8789/live.html ，启动命令为 `python arcade/serve.py --port 8789`。

### 街机面板外观

内置 ImageGen 生成了单人四键街机面板素材：红色球头摇杆，A/B/C/D 四颗圆按钮，带纹理的金属面板、边框和螺丝。采用常见九十年代街机风格，未声称复刻某一台指定厂牌机柜。原始 PNG 在 `web/assets/arcade-panel-v1.png`，完整提示词及来源说明在 `web/assets/arcade-panel-v1.prompt.txt`。

网页叠加与实体按钮对齐的透明交互区域。手动模式支持鼠标/触摸按住按钮、拖动摇杆、键盘与鼠标组合输入；松开、移出窗口和切至后台会释放输入。AI 和回放模式只展示输入反馈，不接受面板操作。

按钮光圈根据已提交给模拟器的输入亮起，短按光圈保留 140ms 方便观看；摇杆方向和“按下”文字使用当前帧按键，短按余光不会合并成额外组合键。没有 ROM 时按钮禁用，也不会展示伪造操作。前端布局与交互反馈测试见 `runs/web-verification.json`，交互测试使用明确标记的模拟状态，不是游戏通关证明。

将已有 kovsh.zip 和 pgm.zip 放入 arcade/roms/，点击“重新检测 ROM”。也可指定 --rom C:\Games\roms\kovsh.zip；BIOS 放在 ROM 同目录。

方向键移动，J 攻击，K 跳跃，U 对应按钮 C，I 对应按钮 D，5 投币，Enter 开始。映射基于 FBNeo 默认 RetroPad 布局，具体道具菜单和使用按键需在游戏中核对。旧记录的 item/menu 别名保留原有物理按键含义，不能把名称当作使用成功的证据。打开页面不自动投币。手动进入首关后可保存截图、RAM、当前存档和逐帧按键记录。

### 道具闭环控制

items.py 实现读取库存、判断适用条件、打开菜单、按已验证的光标转换选取、确认选中项、提交使用按键、核对数量与效果变化。逐帧决策、按键间释放，选错或超时会取消。只提交普通按键，不能写库存或直接调用游戏内部效果。

观察器 items.enabled 默认为 false。启用必须填入真实证据，并校准 item_menu_open、item_cursor、selected_item_id、can_use_item、hp_max、character、stage、player_facing；catalog 中每项指定真实 id、count_field、cursor、适用角色/关卡/朝向、保留数量、资源价值和效果观察字段。菜单 navigation 是已核对的 from/to/button 转换图，不假设菜单是固定顺序。

使用条件支持低血量遇敌、敌群进入有效范围、Boss 可受击；未知 Boss 可受击状态不会触发对应规则。目录中的道具名称、ID、数量偏移和效果不会根据猜测填入。评分扣除消耗的道具资源价值，用于避免仅为刷分滥用有限库存。

每次尝试记录 input_submitted / consumed_effect_observed / consumed_unconfirmed_effect / use_unconfirmed 等状态。死亡、换角色或切关导致的库存变化不会直接算作成功使用。效果变化仅表示观察窗口内发生了对应变化，不能单独证明是该道具造成；实战还需看录像及无道具对照。

普通策略和 MPC 不再把 attack+jump 同帧作为“跳跃攻击”。跳跃候选单独提交；具体连招与角色机制仍需 ROM 实测。道具控制仅运行在提交路径，前瞻分支不会污染库存使用记录。

python arcade/test_items.py 验证选择、空库存/保留量、Boss 无敌、失败使用、数量减少但无效果、死亡清库存、菜单卡住和按键组合等流程。证据在 runs/item-tests.json；这是合成状态测试，不是风云再起道具实战验证。

## 校准和训练

1. python arcade/probe.py 检查当前核心信息和 ROM 文件大小、CRC。ROM 通过审计不等于已启动；BIOS 此脚本只检查存在性。
2. 在网页保存至少两组已知血量、位置等状态的画面与 RAM。
3. python arcade/calibrate.py --samples captureA/ram.bin=100 captureB/ram.bin=90 --size 2 搜索候选偏移；分别检查 little/big 字节序，不能直接把 CPU 地址当作导出 RAM 偏移。
4. 复制 observation.template.json 为 observation.json，补齐血量、生命、分数、关卡进展、坐标、终局判定；敌人按 enemy0_x/y/active/hp 等字段定义，配置 enemy_slots。需核对切关、死亡和最终胜利的状态，记录独立证据与核心、ROM SHA256，再标记 verified。
5. 从同一个起始存档比较 8 个攻击节奏、接敌距离、跳跃频率组合；加 --mpc 使用精确核心向前搜索。策略只提交普通按键，无自动续币、无内存修改。

```powershell
python arcade/train.py --state arcade/runs/capture-xxx/current.state --frames 18000 --mpc
```

训练目录保留初始存档、核心/ROM/观察器/策略代码哈希、每帧输入、关键截图、结果及独立回放的状态/RAM/像素核对。只有回放一致的候选才参与优胜策略筛选。

**当前搜索入口为存档起点的局部练习，结果不会标成整局通关。** ROM 可用后仍需完成角色和场景校准、按关训练，再实现并运行从投币开局到最终胜利的全程验证。一次开发场景获胜也不等于稳定通关。

## 播放训练结果

```powershell
# 实时运行优胜策略，需已校准 observation.json
python arcade/serve.py --policy arcade/runs/search-xxx/best-policy.json
# 原样播放一次候选的输入；不调用 AI，结束时核对最终状态
python arcade/serve.py --replay arcade/runs/search-xxx/candidate-00
```

## 接口验证

```powershell
python arcade/selftest.py
node arcade/verify-web.cjs
```

第一个使用独立开源 2048 核心验证前端，不是风云再起成绩测试。第二个验证缺 ROM 状态、按钮、桌面/手机/直播画幅，需本地服务运行。

主要文件：emulator.py 模拟器接口；policy.py 观察器和规则策略；train.py 参数搜索与回放；serve.py 本地服务；web/ 直播画面。

## 来源

- FBNeo：https://buildbot.libretro.com/nightly/windows/x86_64/latest/fbneo_libretro.dll.zip
- 游戏驱动：https://github.com/finalburnneo/FBNeo/blob/master/src/burn/drv/pgm/d_pgm.cpp
- libretro：https://github.com/libretro/RetroArch/blob/master/libretro-common/include/libretro.h
- RAM：https://github.com/libretro/FBNeo/blob/master/src/burner/libretro/retro_memory.cpp
- 按键：https://github.com/libretro/FBNeo/blob/master/src/burner/libretro/retro_input.cpp
- 测试核心：https://buildbot.libretro.com/nightly/windows/x86_64/latest/2048_libretro.dll.zip

核心版本和 SHA256 见 runs/probe.json。驱动源码为下载时的参考快照，运行验证以已记录哈希的二进制为准。FBNeo 许可证见 cores/LICENSE-FBNeo.md。游戏文件来源与校验记录见各游戏报告。


## 西游释厄传 V126（2026-10-01）

最新行为树版本已核验完整通关：**123次死亡、续币61次**，比上一纪录少27次死亡。前四关逐关新增行为并通过局部复验，再做整局筛选；原完整纪录保留在下文。正式树为 `orlegend-bt-deployed.json`，见 [行为树报告](runs/orlegend/bt/REPORT.md)。8791直播已更新为新回放。

已下载 `roms/orlegend.zip`（包含 BIOS 的 non-merged 集合），18 个游戏/BIOS 文件大小和 CRC 全部符合本地 FBNeo 驱动。下载来源及 SHA256 在 `runs/orlegend-download.json`，文件审计在 `runs/orlegend/audit.json`。

**已通关，正常续关 76 次，非一币通关。** 孙悟空，从开机连续执行 463,420 帧；成绩局与独立回放均零读档。完整状态、RAM、画面哈希一致，并已查看独立回放的佛祖结局画面。成绩目录 `runs/orlegend/full-policy-cold-05/`，见 [训练报告](runs/orlegend/REPORT.md) 与 [通关审核](runs/orlegend/full-policy-cold-05/clearance-audit.json)。一个完整策略局及其回放不代表普遍成功率。

```powershell
# 从开机执行已训练策略，结束后独立回放；输出目录必须不存在
python arcade/orlegend_campaign.py --config (Get-Content arcade/orlegend-policy.json -Raw) --frames 600000 --output arcade/runs/orlegend/reproduce-clear --verify
# 复核整局输入
python arcade/orlegend_campaign.py --replay arcade/runs/orlegend/full-policy-cold-05
# 直播已录制的实战；点击“开始运行”
python arcade/serve.py --rom arcade/roms/orlegend.zip --profile arcade/orlegend-observation.json --replay arcade/runs/orlegend/full-policy-cold-05 --port 8791
```

直播地址 http://127.0.0.1:8791/live.html ，OBS 加 `?capture=1`，1080×1920。一次回放结束后重新启动服务再播；同实例重复读档仍可能出现核心内部状态差异，不能把仅 RAM/画面相同当作完整核验。

西游使用 FBNeo 的 rollback/netplay 确定性时钟模式及独立临时存储目录，避免宿主时钟和 PGM 持久 RAM 污染实验。核心、游戏 ROM、生命、血量、伤害没有修改。RAM 地址线索只用于读取；未加载作弊文件。画面中的生命栏显示含当前角色的生命总数；场景码不单独作为通关证明。普通通用观察器保持关闭，直播使用西游专用只读基础字段。

[结局片段](runs/orlegend/verified-ending.mp4) 方便快速观看，当前无声；片段由存档起点导出，完整证明以从开机的独立回放为准。历史失败与被否决的拼接候选保留在训练报告中。

## 确定性行为树

新增 8 套有状态行为树，按受伤、夹击、地面站位、攻击反馈、道具库存决定实际按键；每次分支变化记录审计。`--behavior-trees` 逐棵试验，`--behavior-forest` 用原生前瞻比较整棵树，未通关。详见 [策略与验证记录](runs/kovsh/BEHAVIOR-STRATEGIES.md)。

## 只读 RAM 与一命验收

新增 `kovsh.py --headless --no-life-loss`：AV 视频位关闭，不捕获/分析任何画面；任何死亡立即结束。`--poweron-prefix` 会逐帧审计前缀的一币、零死亡；`--expect-prefix-ram` 要求进入策略前 RAM 精确一致。结束后独立从开机重放，检查 RAM 与本机状态，视频字段为 null。最新完成的 `one-life-bamboo-001` 前缀 86,890 帧零死亡、RAM 完全一致，后续 7,087 帧因竹林计时耗尽失败，未通关。

库存观察已修复：`0x12971` 为有效槽位数，`0x12973` 为选择索引；只读取有效槽位，排除残留数据。通过无视频实际按键确认 ID 7、4、5 消耗。朝向读取 `0x114cd` 的 `0x20` 位，已用转向、释放和攻击命令校准。详细迭代证据在 `runs/kovsh/one-life-optimization-history.json`。

## 风云再起无画面迭代

训练只读 RAM，关闭视频和画面分析。`bamboo-mechanisms-009` 的 8 种命名机制合计模拟 17,424 帧，6.95 秒，约 42.4 倍实时帧率；均未过段。前瞻还要模拟候选分支，其实际对局推进速度单独统计。[局部得分曲线](runs/kovsh/ram-training-curve.png) 和 [原始数值](runs/kovsh/ram-training-metrics.json) 由数值日志生成，没有读取游戏图像。

独立 PGM 核心仅补全存档中的 CPU 跨帧余量 `nCyclesDone[3]`；未改帧执行代码或 ROM。相同连续开机 86,890 帧后的节点，基线恢复后第 25 帧 RAM 偏离；修复后未来 600 帧 RAM 和最终本机状态一致。编译来源、哈希与验证范围在 [构建记录](cores/pgm-statefix-build.json)。用 `--core` 显式选择，原通用核心保持可用，回放按运行清单里的核心路径及哈希核对。

```powershell
# 8 种固定战斗机制；输出目录必须不存在
python arcade/kovsh_batch.py --core arcade/cores/fbneo_pgm_statefix_libretro.dll --state arcade/runs/kovsh/state-audit-fixed-002/checkpoint.state --output arcade/runs/kovsh/reproduce-ram-mechanisms --workers 4 --trials 8 --frames 10000 --boss-slot 0 --room-exit --mechanisms
# 跨多个未来步骤保留不同战术分支；局部候选要独立重放
python arcade/kovsh_room_search.py --core arcade/cores/fbneo_pgm_statefix_libretro.dll --state arcade/runs/kovsh/state-audit-fixed-002/checkpoint.state --output arcade/runs/kovsh/reproduce-ram-search --workers 4 --width 12 --step 180 --depth 55
python arcade/kovsh_training_report.py
```

网页 `http://127.0.0.1:8795/batch.html` 展示策略评估，`live.html` 在无视频运行时显示 RAM 状态与已执行按键，停止请求游戏帧。当前尚未一命通关，局部节点和短分支不计作完整通关局数。

## 竹林卡点已通过（2026-10-02）

加入锁定连击、先对齐再出手等状态规则，并按实际命中、击杀发生的早晚计分。相同起点的最后一波清场从第 6,798 帧提前到 6,496 帧。出口试验进一步确认：y≈153 时向下对齐再右行，243 帧进入下一段；向上或只右行仍超时。`exit_lower_lane` 已加入导航，竹林专用规则限定 RAM 房间字段 `0x1b1db == 0`，不套用到后续房间。原始动画字段仅用于经验规则，未宣称完整解码。

`one-life-bamboo-exit-cold-025` 从开机连续执行 93,629 帧，一次投币、零死亡；出口剩 57 血，RAM 与完整本机状态匹配试局，独立冷启动重放最终状态一致。短试局的核验也增加终点 RAM/状态检查，避免没有 600 帧采样被当成未核验。[过段证明](runs/kovsh/bamboo-exit-one-life-verdict.json)；[数值曲线](runs/kovsh/ram-training-curve.png)。随后 `one-life-next-room-026` 又零死亡通过一个房间，1,619 帧、剩 57 血，独立重放一致。**这些是第四关的分段进展，整局一命通关尚未完成。**

本轮包含 36 个固定节点战斗机制对比、6 个出口方向对比、完整竹林策略对比与后半段搜索；没有随机调参，也没有读取游戏图像。15 项保护检查覆盖库存、追击、连击方向、出口、房间隔离、洞穴回程与无有效选择索引时先打开道具菜单。`kovsh_combat_audit.py` 用真实输入重放测量追击和命中耗时，`kovsh_combat_probe.py` 比较命名动作机制。

后续洞穴出口由旧成功路线的 RAM/按键记录定位，实际回到 x=855..875 后向上至地面 y=136，328 帧进入下一段；相同存档的直行与多个水平通道均失败，证据在 `cave-door-037/`。新增 `cave_return_exit` 保存回程状态，避免走到触发坐标以下就失去路径。`one-life-cave-cold-039` 从开机 100,376 帧一币零死亡，RAM、本机状态与独立重放一致；[前缀证明](runs/kovsh/fourth-stage-prefix-verdict.json)。随后走廊 `one-life-corridor-038` 也零死亡通过，仍剩 57 血。

第四关首领的 `one-life-chapter4-final-040` 已零死亡进入后续关卡，剩 27 血。首领优先版 `one-life-chapter4-boss-priority-043` 降低对杂兵击杀的奖励、提高首领伤害权重，并比较直接攻击首领的命名动作；同一存档独立重放通过，结束剩 55 血，相比旧路线少 2,904 帧。训练路径的完整冷启动核验与后续关卡训练在 `one-life-next-chapter-cold-045`，以该目录的实际审计为准。[已采用路线的实际得分曲线](runs/kovsh/adopted-route-score-curve.png) 标明冷启动核验截止位置，不能作为整局通关证明。
