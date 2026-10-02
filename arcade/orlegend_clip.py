"""Export a labelled checkpoint-based viewing excerpt; full proof remains cold replay."""
import argparse,json,subprocess
from pathlib import Path
from emulator import Emulator,ROOT
from orlegend import ROM,sha
parser=argparse.ArgumentParser()
parser.add_argument('folder',type=Path)
parser.add_argument('--output',type=Path,default=ROOT/'runs/orlegend/ending.mp4')
args=parser.parse_args();folder=args.folder;out=args.output
start=json.loads((folder/'latest.json').read_text())['frame'];rows=(folder/'inputs.jsonl').read_text().splitlines()[start:]
e=Emulator(ROM,deterministic=True);e.restore((folder/'latest.state').read_bytes())
p=None;count=0
try:
 for i,line in enumerate(rows):
  e.step(json.loads(line)['buttons'])
  if i%2==1:
   pic=e.picture().convert('RGB')
   if p is None:p=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{pic.width}x{pic.height}','-framerate',str(e.fps/2),'-i','-','-an','-vf','scale=720:540:flags=neighbor','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],stdin=subprocess.PIPE)
   p.stdin.write(pic.tobytes());count+=1
 p.stdin.close();assert p.wait()==0
 (out.with_suffix('.json')).write_text(json.dumps({'source':str(folder),'start_frame':start,'end_frame':start+len(rows),'source_state_sha256':sha(folder/'latest.state'),'source_inputs_sha256':sha(folder/'inputs.jsonl'),'video_sha256':sha(out),'method':'checkpoint-based excerpt for viewing; not independent cold replay proof','audio':False,'duration_seconds':count/(e.fps/2)},indent=2))
 print(out)
finally:e.close()
