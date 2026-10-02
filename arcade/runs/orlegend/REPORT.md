# 西游释厄传 V126 通关训练记录

最新行为树记录已更新为 **123 次死亡、第 124 条命通关、续币 61 次**，详见 [行为树训练报告](bt/REPORT.md)。以下保留首次验证通关记录说明；8791直播已更新为新记录。

2026-10-01。**已完成整局通关，正常续关 76 次，非一币通关。** 孙悟空，从开机、投币至结局连续运行；成绩局与独立回放均为零读档。证据目录：`full-policy-cold-05/`。

## 结果

|项目|核验结果|
|---|---|
|整局输入|463,420 帧，130.51 游戏分钟（含开机及结局）|
|正常投币|77 次：开局 1 次，续关 76 次|
|最终整局策略运行耗时|1070.11 秒；不代表全部探索耗时|
|独立回放|全新模拟器从开机执行同一输入；零读档；状态、RAM、画面 SHA256 全部一致|
|终局|最终首领击败，进入佛祖与结局经文画面；已查看独立回放截图|
|成绩边界|一个完整策略局及其独立回放，不代表跨版本稳定通关或一币通关|

## 查看

- [直播回放](http://127.0.0.1:8791/live.html)，OBS 加 `?capture=1`；网页可暂停和调速。回放执行已录制按键，不重新调用策略。
- [结局片段](verified-ending.mp4)：便于观看的存档起点片段，无声；完整通关证明是下面的从开机独立回放。
- [通关审核](full-policy-cold-05/clearance-audit.json)、[独立回放](full-policy-cold-05/replay.json)、[逐帧输入](full-policy-cold-05/inputs.jsonl)。
- [独立回放结局截图](full-policy-cold-05/verified-ending-0461400.png)。

## 方法与关键修正

沿用坦克项目的“分段练习—整局执行—关闭策略后按键回放”验收方式。坦克直播运行 JavaScript 游戏逻辑；西游使用真实 FBNeo / PGM 模拟核心，网页只显示模拟器画面和实际输入。

训练采用 RAM 只读观察与规则策略筛选，不是神经网络强化学习。练习允许存档；最终成绩局不读档。只提交方向、攻击、跳跃、投币和开始等正常按键，未改写游戏 RAM、ROM、血量或伤害，未加载作弊配置。

主要修正：敌人槽生命周期过滤、带符号坐标、推佛像、破门和洞穴出口、迷宫回程、巨型蜘蛛站位、树精 16 次命中机关，以及火焰桥分段纵向路线。最终参数在 `arcade/orlegend-policy.json`，策略源码快照在成绩目录中。此次成绩局没有在线参数改动。

## 逐关记录

以下按真实关卡状态分组；单个场景码变化不等于过关。游戏帧包含关内续关等待，结局动画单独保留。

|关卡|进入帧|下一关/结局帧|游戏耗时|续关次数|
|---|---:|---:|---:|---:|
|第 1 关|2,584|22,442|5.59 分钟|0|
|第 2 关|22,442|44,309|6.16 分钟|2|
|第 3 关|44,309|88,556|12.46 分钟|5|
|第 4 关|88,556|132,498|12.38 分钟|4|
|第 5 关|132,498|180,831|13.61 分钟|6|
|第 6 关|180,831|250,048|19.49 分钟|6|
|第 7 关|250,048|326,769|21.61 分钟|14|
|第 8 关|326,769|459,820|37.47 分钟|39|

## 复现

在项目根目录运行（输出目录必须不存在）：

```powershell
python arcade/orlegend_campaign.py --config (Get-Content arcade/orlegend-policy.json -Raw) --frames 600000 --output arcade/runs/orlegend/reproduce-clear --verify
python arcade/orlegend_campaign.py --replay arcade/runs/orlegend/full-policy-cold-05
python arcade/serve.py --rom arcade/roms/orlegend.zip --profile arcade/orlegend-observation.json --replay arcade/runs/orlegend/full-policy-cold-05 --port 8791
```

通用观察器未启用，`orlegend-observation.json` 无需创建；服务对西游使用已校准的只读基础字段。直播当前无声音。回放结束后重启服务以重新从开机播放。

## 审计与历史

ROM / BIOS 18 个文件大小和 CRC 均通过审计，见 `audit.json` 与 `../orlegend-download.json`。使用固定模拟时钟和独立临时持久存储，避免宿主时钟和旧 PGM RAM 污染。

曾拼接分段输入形成 66 次续关的候选，但从开机回放在接缝处发生状态分歧，已否决，见 `clear-cold-replay-01/replay-failed.json`；它不是本次成绩。随后 `full-policy-cold-04` 在火焰桥入口卡住，主动终止。最终采用修正后的 `full-policy-cold-05` 从开机完整执行并独立核验。最初未通关的 12 次评估保留于 `REPORT-initial.md`。

ROM SHA256：`acdc632a0b67fead83ae1ca96d964b4344d2590b56c31e3b341da3381f3f58b3`。

完整状态 SHA256：`b1f52284ed08c5e54fe08dbb296076a65c3c5e11a69fc62c931b8b9461e49380`。其他指纹、输入和截图哈希见通关审核 JSON。

## 来源

- [FBNeo 游戏驱动](https://github.com/finalburnneo/FBNeo/blob/master/src/burn/drv/pgm/d_pgm.cpp)。
- [ROM 下载集合](https://archive.org/details/fbneo-1g1r-non-merged-rom-set_202605)，精确下载地址保存在来源记录。
- [RAM 地址线索](https://github.com/finalburnneo/FBNeo-cheats/blob/master/cheats/orlegend.ini)，仅作只读参考。
- [玩家操作指南](https://arkwright1.blog.fc2.com/blog-entry-1475.html)与[路线指南](https://arkwright1.blog.fc2.com/blog-entry-1476.html)，用于提出候选，最终路线以本地实测为准。
