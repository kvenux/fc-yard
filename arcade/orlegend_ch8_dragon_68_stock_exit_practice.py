import sys,json,argparse
from pathlib import Path
sys.path.insert(0,'arcade')
from emulator import Emulator
from orlegend import ROM
from orlegend_bt_train import observation
from orlegend_bt import Controller
from orlegend_beam_parallel import static_loot_keys
parser=argparse.ArgumentParser();parser.add_argument('--state');parser.add_argument('--output');parser.add_argument('--allowed',default='6,9,18,22');parser.add_argument('--priority',action='store_true');args=parser.parse_args()
out=Path(args.output or 'arcade/runs/orlegend/bt/one-life-ch8-dragon-68-exit-practice-02');out.mkdir(exist_ok=False);e=Emulator(ROM,deterministic=True,headless=True);e.restore(Path(args.state or 'arcade/runs/orlegend/bt/one-life-ch8-dragon-ground-wave-clear-probe-01/True-3.state').read_bytes());initial=o=observation(e);ctrl=Controller(json.loads(Path('arcade/orlegend-bt-ch8-search-policy-14.json').read_text()));inputs=[];trace=[];last=None
for f in range(4200):
 r=e.ram_view();allowed=list(map(int,args.allowed.split(',')));has=any(r[0xc266+0x98*i+1]==2 and r[0xc266+0x98*i+4]==28 and r[0xc266+0x98*i+0x7f] in allowed for i in range(80))
 if has and args.priority:
  allowed=[next(ident for ident in allowed if any(r[0xc266+0x98*i+1]==2 and r[0xc266+0x98*i+4]==28 and r[0xc266+0x98*i+0x7f]==ident for i in range(80)))]
 k=static_loot_keys(o,r,f,allowed) if has and o['player_state']==2 and not o['enemies'] else ctrl.choose(o,f)
 e.step(k);inputs.append(k);o=observation(e)
 sig=(o['stage_raw'],str(o['resources']['inventory']))
 if sig!=last:trace.append({'frame':f+1,'o':o,'clock':e.ram_view()[0xc06f]});last=sig
 if o['hp']<=0 or o['lives']<2 or o['stage_raw']==1795:break
result={'frames':len(inputs),'after':o,'clock':e.ram_view()[0xc06f],'trace':trace};(out/'result.json').write_text(json.dumps(result,indent=2));(out/'final.state').write_bytes(e.save());(out/'exit-plan.json').write_text(json.dumps({'initial':initial,'after':o,'macros':[{'name':'dragon_68_stock_exit','inputs':inputs}]}));print(json.dumps(result));e.close()
