// Visual persistence only. No game input or simulation timing is changed.
class ControllerFeedback {
  constructor(root=document){this.pad=root.querySelector('.dpad');this.keys=[...root.querySelectorAll('.key')];this.fire=root.querySelector('#fire');this.prob=root.querySelector('#fire-prob');this.bProb=root.querySelector('#b-prob');this.reset();}
  reset(){this.direction=4;this.directionUntil=0;this.fireUntil=0;this.previous='';this.bucket=-1;this.render();}
  consume(state,now=performance.now()){
    const direction=state.keys.indexOf(true);
    if(direction>=0){this.direction=direction;this.directionUntil=now+100;}
    if(state.fire)this.fireUntil=now+120;
  }
  render(now=performance.now()){
    const direction=now<this.directionUntil?this.direction:4,fire=now<this.fireUntil;
    const bucket=Math.floor(now/350),signature=direction+':'+fire+':'+bucket;if(signature===this.previous)return;this.previous=signature;
    // Presentation randomness stays in the parent page, isolated from game RNG.
    if(bucket!==this.bucket){this.bucket=bucket;this.noise=Array.from({length:5},()=>Math.random());this.aNoise=Math.random();this.bNoise=Math.random();}
    // Synthetic softmax: selected direction has a strictly greater logit.
    const weights=this.noise.map((n,i)=>Math.exp(i===direction?2.8+n: -.5+n*1.8)),sum=weights.reduce((a,b)=>a+b,0),prob=weights.map(w=>Math.floor(w/sum*100));
    prob[direction]+=100-prob.reduce((a,b)=>a+b,0);
    this.keys.forEach(key=>{const i=Number(key.dataset.direction);key.classList.toggle('active',i===direction);key.querySelector('span').textContent=prob[i]+'%';key.setAttribute('aria-label',['上','左','下','右','停留'][i]+' '+prob[i]+'%');});
    this.pad.dataset.direction=direction;this.fire.classList.toggle('active',fire);this.prob.textContent=(fire?78+Math.round(this.aNoise*19):5+Math.round(this.aNoise*31))+'%';
    if(this.bProb)this.bProb.textContent=(2+Math.round(this.bNoise*21))+'%';
  }
}
