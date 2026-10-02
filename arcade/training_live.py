"""Read-only broadcast of committed training frames (never search branches)."""
import argparse
import json
import os
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from emulator import ROOT

BASE=ROOT/'runs/kovsh'
def shared_read(path):
    if os.name!='nt':return path.read_bytes()
    import ctypes as C
    from ctypes import wintypes as W
    kernel=C.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[W.LPCWSTR,W.DWORD,W.DWORD,C.c_void_p,W.DWORD,W.DWORD,W.HANDLE]
    kernel.CreateFileW.restype=W.HANDLE
    kernel.GetFileSizeEx.argtypes=[W.HANDLE,C.POINTER(C.c_longlong)]
    kernel.ReadFile.argtypes=[W.HANDLE,C.c_void_p,W.DWORD,C.POINTER(W.DWORD),C.c_void_p]
    kernel.CloseHandle.argtypes=[W.HANDLE]
    handle=kernel.CreateFileW(str(path.resolve()),0x80000000,7,None,3,0,None)
    if handle==C.c_void_p(-1).value:raise C.WinError(C.get_last_error())
    try:
        size=C.c_longlong()
        if not kernel.GetFileSizeEx(handle,C.byref(size)):raise C.WinError(C.get_last_error())
        buf=C.create_string_buffer(size.value);count=W.DWORD()
        if not kernel.ReadFile(handle,buf,size.value,C.byref(count),None):raise C.WinError(C.get_last_error())
        return buf.raw[:count.value]
    finally:kernel.CloseHandle(handle)
def current():
    return Path(json.loads((BASE/'active-training.json').read_text())['directory'])

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_POST(self):
        self.send_response(409);self.send_header('Content-Type','application/json');self.end_headers()
        self.wfile.write(json.dumps({'error':'训练直播为只读；操作由训练进程执行'},ensure_ascii=False).encode())
    def do_GET(self):
        path=urlparse(self.path).path
        try:
            if path=='/api/search':
                p=Path(json.loads((BASE/'active-search.json').read_text())['directory'])
                d=json.loads((p/'status.json').read_text());d['search']=p.name
                manifest=json.loads((p/'manifest.json').read_text());d['scope']=manifest.get('scope')
                if manifest.get('step'):
                    d['native_simulated_frames']=d['rollouts']*manifest['step']
                    d['aggregate_fps']=d['native_simulated_frames']/max(1,d['seconds'])
                d['finished']=(p/'history.json').exists();d['candidate']=(p/'result.json').exists()
                body=json.dumps(d).encode();kind='application/json'
            elif path=='/api/batch':
                p=Path(json.loads((BASE/'active-batch.json').read_text())['directory'])
                d=json.loads((p/'status.json').read_text()) if (p/'status.json').exists() else {'completed':0}
                if 'total' not in d:d['total']=json.loads((p/'manifest.json').read_text()).get('requested_trials')
                d['cohort']=p.name
                d['all_completed_trials']=sum(1 for f in BASE.glob('*/trial-*/result.json'))
                d['running_trials']=[json.loads(f.read_text()) for f in p.glob('trial-*/progress.json') if not (f.parent/'result.json').exists()]
                d['strategy_results']=[]
                for f in sorted(p.glob('trial-*/result.json')):
                    r=json.loads(f.read_text());c=r['config']
                    d['strategy_results'].append({'name':c.get('strategy_label',c.get('behavior_tree','行为树前瞻选择' if c.get('behavior_forest') else '规则策略')),
                        'frames':r['frames'],'damage':r.get('enemy_damage',0) if c.get('room_exit') else r['boss_start_hp']-r['boss_min_hp'],
                        'hp':r['after']['hp'],'room_clear':r.get('room_exit_candidate',r.get('room_clear_candidate',False)),
                        'branches':r.get('behavior_branch_visits',{})})
                body=json.dumps(d).encode();kind='application/json'
            elif path=='/batch-curve.png':
                p=Path(json.loads((BASE/'active-batch.json').read_text())['directory'])
                f=p/'training-curve.png'
                if not f.exists():f=BASE/'batch-sima-002/training-curve.png'
                body=f.read_bytes();kind='image/png'
            elif path=='/api/status':
                p=current()
                if (p/'live.json').exists():d=json.loads(shared_read(p/'live.json'))
                else:
                    o=json.loads((p/'status.json').read_text());d={'frame':o['frame'],'observation':o,'seconds':0,'buttons':[]}
                o=d['observation'];finished=(p/'result.json').exists()
                manifest=json.loads((p/'manifest.json').read_text());headless=manifest.get('headless',False)
                inv=[dict(id=k,name={'1':'袖箭','4':'回旋镖','5':'炸弹','7':'道具 7'}.get(k,'道具 '+k),count=v) for k,v in o.get('inventory',{}).items()]
                s=dict(ready=True,game='kovsh',playing=not finished,mode='training',speed=1,
                       frame=d['frame'],recorded_frames=d['frame'],fps=59.18,
                       actual_speed=d['frame']/max(1,d['seconds'])/59.18 if d['seconds'] else 0,
                       reason=f"{p.name} · {'本轮结束' if finished else '启发式训练 / 仅显示已执行动作'}",
                       error='',buttons=d['buttons'],calibrated=True,items_calibrated=True,item_events=d.get('item_events',[]),
                       observation={**o,'inventory':inv,'progress':f"第 {o['chapter']+1} 关 · 尚未通关" if 'chapter' in o else '未校准'},
                       headless=headless,has_video=not headless,forecast_native_frames=d.get('forecast_native_frames'),
                       forecast_rollouts=d.get('forecast_rollouts'),full_game_clear_verified=False,replay_result=None)
                body=json.dumps(s,ensure_ascii=False).encode();kind='application/json'
            elif path=='/frame.jpg':
                p=current();f=p/'live.jpg'
                if json.loads((p/'manifest.json').read_text()).get('headless'):
                    self.send_response(204);self.send_header('Cache-Control','no-store');self.end_headers();return
                if f.exists():body=shared_read(f);kind='image/jpeg'
                else:
                    f=sorted(p.glob('frame-*.png'))[-1];body=f.read_bytes();kind='image/png'
            elif path in ('/score-curve.png','/campaign-progress.png','/chapter4-score-curve.png','/ram-training-curve.png'):
                body=(BASE/path[1:]).read_bytes();kind='image/png'
            elif path in ('/','/live.html','/batch.html','/live.css','/live.js','/assets/arcade-panel-v1.png'):
                name='live.html' if path=='/' else path[1:];body=(ROOT/'web'/name).read_bytes()
                kind={'.html':'text/html; charset=utf-8','.css':'text/css','.js':'text/javascript','.png':'image/png'}[Path(name).suffix]
                if name=='live.html':
                    body=body.decode().replace('<h1>直播控制台</h1>','<h1>训练直播</h1><a href="/batch.html" target="_blank">并行训练</a> · <a href="/score-curve.png" target="_blank">整局评估曲线</a> · <a href="/campaign-progress.png" target="_blank">当前路线得分与血量</a>').encode()
            else:self.send_error(404);return
            self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        except (OSError,ValueError,IndexError):self.send_error(503,'Training frame not ready')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8795);a=p.parse_args()
    print(f'http://127.0.0.1:{a.port}/live.html?capture=1',flush=True)
    ThreadingHTTPServer(('127.0.0.1',a.port),Handler).serve_forever()
