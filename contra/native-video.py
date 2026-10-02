"""Render the verified controller trace, then a short untouched ending sequence."""
import sys,json,subprocess,hashlib,wave
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'arcade'))
from emulator import Emulator
path=Path(sys.argv[1]);record=json.loads(path.read_text())
assert record['fullGameClearVerified'] and record['replayEqual']
rom=ROOT/'roms/contra.nes';core=ROOT/'cores/fceumm_libretro.dll'
assert hashlib.sha256(rom.read_bytes()).hexdigest()==record['romSha256']
assert hashlib.sha256(core.read_bytes()).hexdigest()==record['coreSha256']
e=Emulator(rom,core,deterministic=True);encoder=None;count=0
output=path.parent/'full-clear-audio.mp4'
silent=path.parent/'video-render.tmp.mp4';pcm=path.parent/'audio-render.tmp.wav'
e.capture_audio=True;sample_rate=round(e.av.timing.sample_rate);audio_frames=0
audio=wave.open(str(pcm),'wb');audio.setnchannels(2);audio.setsampwidth(2);audio.setframerate(sample_rate)
def render():
    global encoder,count,audio_frames
    if e.audio:
        audio.writeframesraw(e.audio);audio_frames+=len(e.audio)//4;e.audio.clear()
    if e.frame%2:return
    pic=e.picture().convert('RGB')
    if encoder is None:
        w,h=pic.size
        encoder=subprocess.Popen(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{w}x{h}','-framerate','30','-i','pipe:0','-an','-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(silent)],stdin=subprocess.PIPE)
    encoder.stdin.write(pic.tobytes());count+=1
try:
    for mask,n in record['actions']:
        e.mask=(mask&252)|((mask&1)<<8)|((mask&2)>>1)
        for _ in range(n):
            e.core.retro_run();e.frame+=1;render()
            if e.frame%10000==0:print(f'Replayed {e.frame} frames',flush=True)
    actual=e.fingerprint();assert actual==record['expected'],actual
    assert e.ram()[0x18]==6
    ending=0;e.mask=0
    for i in range(1800):
        e.core.retro_run();e.frame+=1;ending+=1;render()
        if ending in [300,600,900,1200,1800]:e.picture().save(path.parent/f'ending-{ending}.png')
    encoder.stdin.close();assert encoder.wait()==0
    audio.close();duration=count/30;tempo=(audio_frames/sample_rate)/duration
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(silent),'-i',str(pcm),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','128k','-af',f'atempo={tempo},apad,atrim=duration={duration}','-movflags','+faststart',str(output)],check=True)
    silent.unlink();pcm.unlink()
    info={'run':path.parent.name,'video':path.parent.name+'/'+output.name,'strategyFrames':record['frames'],'endingIdleFrames':ending,'videoFPS':30,'videoFrames':count,'normalSpeed':True,'audio':True,'audioSampleRate':sample_rate,'audioFrames':audio_frames,'audioTempo':tempo,'replayEqual':True,'actual':actual,'videoSha256':hashlib.sha256(output.read_bytes()).hexdigest()}
    (path.parent/'video-audit.json').write_text(json.dumps(info,indent=2));(ROOT/'runs/latest-video.json').write_text(json.dumps(info,indent=2))
    print(json.dumps(info),flush=True)
finally:
    if encoder and encoder.poll() is None:encoder.kill()
    audio.close()
    e.close()
