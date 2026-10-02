"""Plot numerical samples from the adopted training path; no game images."""
import json
from kovsh import OUT

def main():
    pieces=[('one-life-bamboo-tempo-021',6496),('bamboo-exit-recheck-024/diagonal_down_174',243),
            ('one-life-next-room-026',1619),('one-life-cave-027',4200),
            ('one-life-cave-scoped-028',600),('cave-door-037/door_865_136',328),
            ('one-life-corridor-038',2881)]
    boss_round=OUT/'one-life-chapter4-boss-priority-043/result.json'
    if boss_round.exists():
        boss_result=json.loads(boss_round.read_text())
        if boss_result['termination']=='chapter_exit' and boss_result.get('replay_equal'):
            pieces += [('one-life-chapter4-final-040',5400),('one-life-chapter4-boss-priority-043',boss_result['frames'])]
    if len(pieces)==7 and (OUT/'one-life-chapter4-final-040/result.json').exists():
        r=json.loads((OUT/'one-life-chapter4-final-040/result.json').read_text())
        if r['termination']=='chapter_exit' and r.get('replay_equal'):pieces.append(('one-life-chapter4-final-040',r['frames']))
    points=[];offset=0;segments=[]
    for name,limit in pieces:
        p=OUT/name;r=json.loads((p/'result.json').read_text())
        samples=json.loads((p/'samples.json').read_text()) if (p/'samples.json').exists() else r.get('samples',[])
        if not points:points.append(dict(frame=0,hp=r['before']['hp'],score=r['before']['score']))
        points += [dict(frame=offset+o['frame'],hp=o['hp'],score=o['score']) for o in samples if o['frame']<=limit]
        if r.get('frames')==limit:points.append(dict(frame=offset+limit,hp=r['after']['hp'],score=r['after']['score']))
        segments.append(dict(source=name,offset=offset,frames=limit));offset+=limit
    points.sort(key=lambda p:p['frame'])
    audit=OUT/'one-life-cave-cold-039/prefix-audit.json'
    verified_prefix=json.loads(audit.read_text()) if audit.exists() else None
    cold_cutoff=13486
    best_audit=OUT/'one-life-next-chapter-cold-045/prefix-audit.json'
    if best_audit.exists():
        verified=json.loads(best_audit.read_text())
        if verified.get('ram_equal') and verified['coins']==1 and not verified['deaths']:cold_cutoff=verified['frames']-86890
    report=dict(scope='adopted_training_path_numeric_samples',points=points,segments=segments,
                initial_poweron_prefix_frames=86890,cold_verified_policy_frames=cold_cutoff,
                cold_prefix_audit=verified_prefix,full_game_clear_verified=False,no_game_images_read=True)
    (OUT/'adopted-route-metrics.json').write_text(json.dumps(report,indent=2))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif']=['Microsoft YaHei','DejaVu Sans']
    fig,axes=plt.subplots(2,1,figsize=(10,6),sharex=True,layout='constrained')
    x=[p['frame'] for p in points]
    axes[0].plot(x,[p['score']-points[0]['score'] for p in points],'.-',color='#248b87')
    axes[0].set(title='风云再起 · 已采用训练路线的真实游戏得分',ylabel='游戏得分增加')
    axes[1].plot(x,[p['hp'] for p in points],'.-',color='#bc8242')
    axes[1].set(xlabel='进入原竹林卡点后的实际游戏帧（非完整通关局数）',ylabel='血量',ylim=(0,85))
    for ax in axes:
        ax.axvline(cold_cutoff,color='#777',linestyle='--',alpha=.6)
        ax.grid(alpha=.2)
    axes[0].text(.02,.96,'虚线前已从开机核验一币零死亡；虚线后为独立重放通过的局部试局',transform=axes[0].transAxes,va='top',fontsize=9)
    fig.savefig(OUT/'adopted-route-score-curve.png',dpi=140);plt.close(fig)
    print(json.dumps(dict(frames=offset,points=len(points),score_gain=points[-1]['score']-points[0]['score'],hp=points[-1]['hp'])))

if __name__=='__main__':main()
