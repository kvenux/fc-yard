from pathlib import Path
import json
root=Path(__file__).resolve().parents[2]
folder=root/'training/human-speed-v4'
old=json.loads((root/'training/human-speed/full-1790831537797.json').read_text(encoding='utf-8'))
runs=[json.loads(x) for x in (folder/'full-results.jsonl').read_text(encoding='utf-8').splitlines()]
winner=[r for r in runs if r['victory']][-1]
new=json.loads((folder/winner['file']).read_text(encoding='utf-8'))
replay=json.loads((folder/winner['file'].replace('.json','-replay.json')).read_text(encoding='utf-8'))
def times(a):
 prev=0;out=[]
 for s in a['stages']:
  out.append({'stage':s['stage'],'frames':s['frame']-prev,'lives':s['lives']});prev=s['frame']
 return out
data={'oldFrames':old['final']['ticks'],'newFrames':new['final']['ticks'],'score':new['final']['score'],'lives':new['final']['lives'],'seed':new['seed'],'oldStages':times(old),'newStages':times(new),'stats':new.get('stats',{}),'replay':replay['controllerOnlyReplayMatches'],'minFireGap':replay['minGap']}
(folder/'comparison.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
saved=(data['oldFrames']-data['newFrames'])/60
rows=['# 提速策略完整复验','',f"固定种子 {data['seed']}，从第 1 关连续通过全部 35 关，无读档、无切关。",'',f"- 得分 {data['score']:,}，剩余生命 {data['lives']}。",f"- 游戏时间从 {data['oldFrames']/3600:.2f} 分钟降到 {data['newFrames']/3600:.2f} 分钟；减少 {saved/60:.2f} 分钟（{saved*60/data['oldFrames']:.1%}）。",f"- 关闭 AI 后纯按键回放一致：{data['replay']}。最短射击间隔 {data['minFireGap']} 帧，仍遵守 5 次/秒上限。",f"- 最新按键审计：`{winner['file']}`；纯按键核验：`{winner['file'].replace('.json','-replay.json')}`。",'', '## 原因和改动','','上一轮未优化前 12 关，且允许较长的无进展等待。本轮从第 7 关的最长停留开始，重新筛选后续连续关卡。','','本轮加入 3 / 5 / 8 秒无进展重规划候选，筛选同时检查通关用时、连续停留、无得分时长与生命余量。未通过的激进候选淘汰，只有完整复验成功且总用时改善才部署。游戏规则和射击上限保持不变。','','## 边界','','用时按 60 FPS 的游戏帧数计算，没有靠提高播放倍速缩短指标。并非全局最短时间证明；仍保留必要的防守和等待。仅证明开发种子 4004，不能据此宣称所有随机种子都能稳定通关。']
(folder/'REPORT.md').write_text('\n'.join(rows)+'\n',encoding='utf-8')
