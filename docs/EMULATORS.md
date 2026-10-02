# 模拟器与兼容边界

| 游戏 | 策略执行后端 | 网页后端 | 可复现范围 |
|---|---|---|---|
| 坦克大战 | vendored JS 浏览器复刻 | Canvas / WebAudio | 固定种子与浏览器规则；不是原版 NES 成绩 |
| 魂斗罗 US | FCEUmm libretro | 有声 MP4 + 原生按键/遥测；另有 JSNES 手动入口 | 锁定 Windows x64 核心、ROM SHA256；八关零死亡 |
| 西游 V126 | FBNeo libretro | Python HTTP 服务 + JPEG 帧 + 手柄状态 | 完整路线，允许普通续币；123 死亡 / 61 续币 |
| 风云再起 V104 CN | FBNeo PGM statefix libretro | Python HTTP 服务 + JPEG / PCM 音频 | 前四关一币零死亡；尚未整局通关 |

网页使用标准 HTTP，可在 Windows/macOS/Linux 的 Chromium/Edge/Firefox 打开；浏览器禁自动播放时先点 START/声音。街机服务保持与页面同源，另开端口，不需要浏览器跨域配置。OBS 使用各游戏直播 URL 加 `?capture=1`，1080×1920。

## 固定核心

`python tools/setup.py` 安装 Release `v1.0.0` 的 Windows x64 核心，下载包和每个 DLL 都做 SHA256 校验。`tools/cores-lock.json` 保存二进制版本；`games.json` 保存各游戏核心/ROM/输入/证明对应关系。

- FCEUmm `7a542dab1e87679921962a9f056186eca425c0c2`，核心自报 `(SVN) 7a542da`。
- FBNeo `a4012b161e48b33b94940f07987323574c237448`，核心自报 `v1.0.0.03 260928 GITa4012b1`。
- PGM 修复只在 `pgmScan` 加入 `SCAN_VAR(nCyclesDone)`，补全 CPU 跨帧余量的序列化；没有改 `pgmFrame`、游戏 ROM、生命或伤害。补丁在 `arcade/reference/pgm-statefix.patch`。

Release 同时提供原始源码、完整修复源码、winpthreads 源码及完整许可证。修复版原始构建：MinGW x64/MSYS，源码目录执行 `make platform=win SUBSET=pgm -j6 SHELL=sh.exe`。源码重编译不承诺二进制逐字节相同；严格成绩复验使用锁定二进制。

macOS/Linux 可以运行所有静态直播页、魂斗罗视频、浏览器坦克策略和 Python 行为树单元测试。共享前端支持 `.so`/`.dylib`，可用 `FC_CORE` 环境变量指定自行编译的核心，风云再起训练用 `--core`。**这些平台的原生 ROM 成绩尚未认证**；序列化格式、核心版本和像素输出可能不同，严谨核验不会跳过核心 SHA256。不要把 FCEUmm 的动作轨迹直接当成 JSNES 通关策略。

## 原生回放核验

`python tools/replay.py contra|orlegend|kovsh` 每次重新开机，只发送已记录普通按键，没有初始存档、内存写入或作弊。输出在 `outputs/`，输入校验、帧数、死亡数及状态/RAM 指纹必须匹配，否则退出码 1。魂斗罗另比对画面；街机录制时关闭绘制，网页播放开启绘制，所以网页终点比对状态/RAM，画面不用于伪造认证。

ROM、BIOS、原生存档、RAM dump 不随仓库或 Release 发布。文件版本以 `data/*/proof.json` 为准。PGM BIOS 放在街机 ROM 同目录；西游已认证集合是含 BIOS 的 non-merged 版本。不同压缩重打包也会改变 SHA256，应先确认芯片清单再作新认证。

## 重新生成魂斗罗视频

安装 FFmpeg 并将 `ffmpeg` 放到 PATH，准备锁定核心与 ROM 后执行：

```sh
python contra/native-video.py contra/runs/native-20261001-201819/result.json
```

视频编码可能随 FFmpeg 版本改变文件 SHA256，游戏终点按状态/RAM/画面指纹认证。官方已生成视频由 `python tools/setup.py --video` 下载并校验。
