"""Plot recorded numerical training results; never read game images."""
import json
from pathlib import Path
from kovsh import OUT

def main():
    names=['one-life-bamboo-001','one-life-bamboo-practice-002','one-life-bamboo-practice-003',
           'one-life-bamboo-practice-004','one-life-bamboo-fixed-005','one-life-bamboo-fast-011',
           'one-life-bamboo-cold-014','one-life-bamboo-adaptive-015',
           'one-life-bamboo-combat-020','one-life-bamboo-tempo-021']
    rounds=[]
    for name in names:
        p=OUT/name
        if not (p/'result.json').exists():continue
        r=json.loads((p/'result.json').read_text());samples=json.loads((p/'samples.json').read_text())
        rounds.append(dict(directory=name,score_gain=r['after']['score']-r['before']['score'],
                           frames=r['frames'],seconds=r['seconds'],actual_fps=r['frames']/r['seconds'],
                           forecast_native_frames=r.get('forecast_native_frames'),
                           maximum_x=max([r['after']['x']]+[o['x'] for o in samples]),
                           termination=r['termination'],replay_equal=r.get('replay_equal',False),
                           trajectory_equal=r.get('trajectory_equal',False),
                           hp_before=r['before']['hp'],hp_after=r['after']['hp'],
                           enemy_hp_remaining=sum(e['hp'] for e in r['after']['enemies']),
                           room_transitions=len(r.get('room_transitions',[]))))
    cohort=json.loads((OUT/'bamboo-mechanisms-009/status.json').read_text())
    summary=dict(scope='bamboo_checkpoint_iterations',rounds=rounds,fast_mechanism_cohort=cohort,
                 cohort_speed_scope='aggregate native frames across parallel local trials',
                 full_game_clear_verified=False,no_game_images_read=True)
    exit_proof=OUT/'bamboo-exit-one-life-verdict.json'
    if exit_proof.exists():summary['verified_bamboo_exit']=json.loads(exit_proof.read_text())
    (OUT/'ram-training-metrics.json').write_text(json.dumps(summary,indent=2))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif']=['Microsoft YaHei','DejaVu Sans']
    fig,axes=plt.subplots(3,1,figsize=(10,8),layout='constrained')
    x=list(range(1,len(rounds)+1))
    axes[0].plot(x,[r['score_gain'] for r in rounds],'o-')
    stage_pass=any(r['room_transitions'] and r['hp_after']>0 and r['replay_equal'] for r in rounds) or summary.get('verified_bamboo_exit',{}).get('verified',False)
    axes[0].set(title='风云再起 · 竹林局部策略迭代（'+('已验证过段' if stage_pass else '尚未过段')+'）',ylabel='实际游戏得分增加')
    if summary.get('verified_bamboo_exit',{}).get('verified'):
        proof=summary['verified_bamboo_exit']
        axes[0].text(.02,.96,f"修正出口后：第 {proof['bamboo_policy_frames']} 帧过段，剩 {proof['hp_remaining']} 血；从开机一币、零死亡",transform=axes[0].transAxes,va='top',fontsize=9)
    axes[1].plot(x,[r['maximum_x'] for r in rounds],'o-',color='#d4882b')
    axes[1].set(ylabel='最大推进坐标 x',xlabel='策略版本评估；并非完整通关局数')
    latest=rounds[-1];preview_fps=(latest.get('forecast_native_frames') or 0)/latest['seconds']
    axes[2].bar(['8种规则策略\n并行合计','最新前瞻\n分支模拟合计','前瞻策略\n实际对局推进'],
                [cohort['aggregate_fps']/59.18,preview_fps/59.18,latest['actual_fps']/59.18],color=['#33958c','#659aaa','#7188b8'])
    axes[2].set(ylabel='相对实时帧率的倍数',title='前瞻要额外模拟分支，实际推进速度单独统计')
    for ax in axes:ax.grid(axis='y',alpha=.2)
    fig.savefig(OUT/'ram-training-curve.png',dpi=140);plt.close(fig)
    print(json.dumps(summary))

if __name__=='__main__':main()
