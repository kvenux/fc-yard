# FC Yard · 四游戏 AI 策略实验场

策略代码、JSON、训练曲线、独立按键回放与直播网页。运行时执行本地策略，无需 GPT API 或账号。

| 游戏 | 已认证成绩 | 执行后端 | 直播地址 |
|---|---|---|---|
| 坦克大战 | 浏览器复刻 35 关；种子 4004；169300 分，剩余 14 命 | JavaScript 启发式/前瞻 | `http://127.0.0.1:8787/live.html` |
| 魂斗罗 US | 八关一命；77417 帧，零死亡 | FCEUmm 原生前瞻 | `http://127.0.0.1:8787/contra/replay.html` |
| 西游释厄传 V126 | 完整通关；123 死亡，61 次普通续币 | FBNeo JSON 行为树 | `http://127.0.0.1:8791/live.html` |
| 风云再起 V104 CN | 前四关一币零死亡；115445 帧；**尚未整局通关** | FBNeo PGM RAM 规则与搜索 | `http://127.0.0.1:8796/live.html` |

成绩对应固定环境的一条已核验路线，不代表跨版本成功率。坦克成绩属于浏览器复刻规则，不是原版 NES ROM 成绩。

## 快速看直播

需要 Node.js 22+。Windows/macOS/Linux 均可运行静态页面：

```sh
git clone https://github.com/kvenux/fc-yard.git
cd fc-yard
npm ci
npm start
```

打开 `http://127.0.0.1:8787/`，统一入口提供四游戏直播、训练曲线和 NES 手动模拟器。坦克浏览器版无需额外 ROM。

魂斗罗有声视频保存在 Release；安装 Python 3.13+ 后下载即可观看，无需 ROM：

```sh
python tools/setup.py --video
```

支持倍速、实际按键/占用率、系统时钟与编排弹幕。声音需要点击开启。

## 原生模拟器与成绩复验

已认证环境：Windows x64，Python 3.13+。

```sh
python -m venv .venv
# PowerShell: .venv/Scripts/Activate.ps1
python -m pip install -r requirements.txt
python tools/setup.py
```

安装器下载固定 Release 并核对包和 DLL 的 SHA256。自行准备对应版本 ROM：

| 文件位置 | ROM SHA256 |
|---|---|
| `contra/roms/contra.nes` | `26541a5550ee22deeb3d5484e4a96130219b58cff74d068fb1eb6567fa5e5519` |
| `arcade/roms/orlegend.zip`，含 BIOS 的 non-merged 集合 | `acdc632a0b67fead83ae1ca96d964b4344d2590b56c31e3b341da3381f3f58b3` |
| `arcade/roms/kovsh.zip` | `cb373b2fbdbb56d1a93338b246cb40f718b20e43fea43ae2668d464c97e73dba` |

风云再起需要同目录 `arcade/roms/pgm.zip` BIOS。ROM、BIOS、存档与 RAM dump 不发布。

```sh
python tools/setup.py --check
python tools/replay.py contra
python tools/replay.py orlegend
python tools/replay.py kovsh
```

从开机只执行公开按键，核对帧数、死亡数与状态/RAM（魂斗罗还有画面），不依赖作者存档、不写内存、不用作弊。报告保存在 `outputs/`；失败退出码 1。西游复验通常需要几分钟。

另开终端启动街机直播：

```sh
python tools/live.py orlegend
python tools/live.py kovsh
```

支持 `--port`。OBS 使用直播地址加 `?capture=1`，1080×1920。服务只监听本机。保留 `/index.html` 和 `/contra/live.html` 的 JSNES 手动入口；原生 FCEUmm 动作不承诺在 JSNES 下通关。

## 策略与验证

- [策略、公开数据与继续训练](docs/POLICIES.md)
- [模拟器版本、对应源码与兼容边界](docs/EMULATORS.md)
- [机器可读游戏入口](games.json)，`data/*/proof.json` 保存锁定指纹。
- `training/human-speed-v4/`：坦克策略、完整动作、曲线与核验。
- `contra/runs/`：魂斗罗正式局/基线、动作、只读插桩、战斗审核和视频遥测。
- `arcade/runs/orlegend/bt/`：正式树、完整按键和通关审核；`arcade/runs/kovsh/`：采用的前缀与数值曲线。

```sh
npx playwright install chromium
npm test
python arcade/test_behavior_tree.py
python arcade/test_kovsh_behavior.py
# 启动 npm start 后复验坦克完整路线
node live-replay-check.cjs training/human-speed-v4/full-1790835776647.json
```

默认使用 Playwright Chromium，可设置 `CHROME_PATH`。CI 在 Windows/macOS/Linux 验证网页和行为逻辑，不含 ROM；其他平台的原生成绩尚未认证。临时探针、海量候选和存档留在本地，不进入 Git 历史。历史报告保留当时的来源哈希。

新增代码使用 MIT；第三方代码、游戏素材、模拟器与历史弹幕遵循各自许可/版权，见 [NOTICE](NOTICE.md)。FBNeo 有非商业限制。Release 提供对应源码、完整许可证与 PGM 补丁。
