from pathlib import Path
import hashlib, json, re, shutil, zipfile

root=Path(__file__).resolve().parents[1]
out=root/'dist'/'FC-AI-Live'
out.mkdir(parents=True,exist_ok=True)
files=['live.html','live.css','live-theme.css','live.js','controller-feedback.js','strategy-narrative.js',
       'live-engine.html','live-engine.js','live-fire.js','live-mpc.js','live-progress.js','live-policy.json']
files += ['reference/web/'+f for f in ['levels.js','sound.js','game.js','strategy.js','safety.js','ai.js','checkpoint.js','tiles/chr_all.png']]
files += ['design/assets/'+f for f in ['famicom-controller-v1.png','famicom-dpad-v1.png','famicom-fire-v1.png','famicom-utility-v1.png']]
files += ['training/human-speed-v4/'+f for f in ['index.html','comparison.json','REPORT.md','full-1790835776647-replay.json']]
for name in files:
    target=out/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/name,target)
for name in ['serve.ps1','Start-Windows.cmd','serve.py','Start-Mac-Linux.command']:
    shutil.copy2(root/'packaging'/name,out/name)
# The hidden engine's decorative external fonts are unnecessary for offline play
p=out/'live-engine.html';s=p.read_text(encoding='utf8');s=re.sub(r'\s*<link[^>]*https://fonts\.[^>]*>','',s);p.write_text(s,encoding='utf8')
p=out/'training/human-speed-v4/index.html';s=p.read_text(encoding='utf8');s=re.sub(r'<a href="../human-speed/index.html">.*?</a> · ','',s);p.write_text(s,encoding='utf8')
(out/'使用说明.txt').write_text('''FC 坦克大战 AI 直播便携版

Windows 10 / 11
1 解压整个压缩包，不能在压缩包内部直接运行
2 双击 Start-Windows.cmd，会自动打开默认浏览器
3 保持启动窗口打开，关闭窗口或按 Ctrl+C 即停止服务
无需安装 Node.js、Python、npm，也无需联网或另外寻找 ROM
建议使用近期的 Microsoft Edge、Chrome 或 Firefox
企业电脑如果禁用了 PowerShell，可安装 Python 3 后在解压目录运行 python serve.py

macOS / Linux
需要已安装 Python 3，在终端进入解压目录运行 python3 serve.py
也可执行 sh Start-Mac-Linux.command
此平台启动脚本已包含，未在实机上验证

直播
默认种子 4004，从第 1 关正常速度开始
系统会选择 8787～8806 内可用端口，准确地址见启动窗口
OBS 浏览器来源使用该端口的 /live.html?capture=1，宽 1080、高 1920
纯净画布按 Esc 返回控制栏
声音需点击控制栏开启，结束结算后默认等待 20 秒重开
概率和决策文字是启发式策略的可视化说明，无需 GPT API 或账号
已验证种子 4004 全 35 关，169300 分、剩余 14 命，游戏时间 44 分 36 秒
不同硬件可能影响实际运行速度，可看控制栏的实际速度
其他种子不保证通关；对局记录保存在当前浏览器，可用页面导出

内容与来源
这是当前直播使用的网页复刻版，不是运行原版 NES ROM 的模拟器
游戏来源 https://github.com/vgrichina/battlecity
固定来源提交 1f31d0d332413a11455ebf0835f5ef0f6c23d714
原始游戏逻辑保留，AI 只提交普通控制按键
包内包含策略、图像、离线服务器、复验摘要，不包含本机历史浏览器数据
原始项目说明见 THIRD-PARTY-README.md
文件校验信息见 manifest.json
''',encoding='utf-8-sig')
shutil.copy2(root/'reference/README.md',out/'THIRD-PARTY-README.md')
manifest={str(p.relative_to(out)).replace('\\','/'):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in out.rglob('*') if p.is_file() and p.name!='manifest.json'}
(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
archive=root/'dist'/'FC-AI-Live-Windows-Mac-Linux.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in out.rglob('*'):
        if p.is_file():z.write(p,Path('FC-AI-Live')/p.relative_to(out))
print(json.dumps({'archive':str(archive),'bytes':archive.stat().st_size,'files':len(manifest)+1},ensure_ascii=False))
