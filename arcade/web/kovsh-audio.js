// Stereo signed 16-bit PCM from FBNeo; audio starts only after a user click.
(() => {
  const button = document.getElementById('sound-toggle');
  let context, gain, enabled = false, cursor = -1, epoch = -1, nextTime = 0;
  const sources = new Set();

  function flush() {
    for (const source of sources) { try { source.stop(); } catch {} }
    sources.clear();
    nextTime = context?.currentTime ?? 0;
  }

  button.addEventListener('click', async () => {
    try {
      if (!context) {
        context = new AudioContext();
        gain = context.createGain();
        gain.connect(context.destination);
        gain.gain.value = 0;
      }
      if (enabled) {
        enabled = false;
        gain.gain.value = 0;
        flush();
      } else {
        await context.resume();
        enabled = true;
        gain.gain.value = .8;
        cursor = epoch = -1;
        nextTime = context.currentTime;
      }
      button.textContent = enabled ? '声音：开' : '声音：关';
      button.setAttribute('aria-pressed', String(enabled));
    } catch (error) {
      button.textContent = '声音不可用';
      document.getElementById('notice').textContent = error.message;
    }
  });

  async function pollAudio() {
    try {
      if (!enabled || document.hidden) {
        if (sources.size) flush();
        cursor = epoch = -1;
        return;
      }
      const response = await fetch(`/audio.pcm?after=${cursor}&epoch=${epoch}`);
      if (!response.ok) throw Error('音频连接失败');
      const nextEpoch = Number(response.headers.get('X-Audio-Epoch'));
      if (nextEpoch !== epoch) flush();
      epoch = nextEpoch;
      cursor = Number(response.headers.get('X-Audio-Cursor'));
      const pcm = await response.arrayBuffer();
      if (!enabled || document.hidden) return;
      if (response.headers.get('X-Audio-Playing') !== '1') { flush(); return; }
      if (!pcm.byteLength) return;
      const frames = pcm.byteLength / 4;
      const rate = Number(response.headers.get('X-Audio-Rate'));
      const speed = Number(response.headers.get('X-Audio-Speed'));
      const buffer = context.createBuffer(2, frames, rate);
      const samples = new DataView(pcm);
      for (let channel = 0; channel < 2; channel++) {
        const output = buffer.getChannelData(channel);
        for (let i = 0; i < frames; i++) output[i] = samples.getInt16(i * 4 + channel * 2, true) / 32768;
      }
      // Limit backlog after a background tab, pause, seek or connection stall.
      if (nextTime - context.currentTime > .25) flush();
      const source = context.createBufferSource();
      source.buffer = buffer;
      source.playbackRate.value = speed;
      source.connect(gain);
      sources.add(source);
      source.onended = () => { sources.delete(source); source.disconnect(); };
      nextTime = Math.max(nextTime, context.currentTime + .03);
      source.start(nextTime);
      nextTime += frames / rate / speed;
    } catch {
      flush();
      cursor = epoch = -1;
    } finally {
      setTimeout(pollAudio, 40);
    }
  }
  document.addEventListener('visibilitychange', () => { if (document.hidden) flush(); });
  pollAudio();
})();
