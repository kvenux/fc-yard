'use strict';
window.ReplayDanmaku=class{
 constructor(data){this.data=data;this.nodes=new Map();this.track=document.getElementById('danmaku-track');}
 update(frame){
  const visible=this.data.entries.filter(e=>frame>=e.frame&&frame<e.frame+e.durationFrames),ids=new Set(visible.map(e=>e.id));
  for(const [id,node] of this.nodes)if(!ids.has(id)){node.remove();this.nodes.delete(id);}
  for(const e of visible){let node=this.nodes.get(e.id);if(!node){node=document.createElement('span');node.className='danmaku-message'+(e.accent?' accent':'');node.textContent=e.text;node.dataset.event=e.source.kind;node.style.top=`${e.lane*30+6}%`;this.track.append(node);this.nodes.set(e.id,node);}
   const progress=(frame-e.frame)/e.durationFrames;node.style.transform=`translateX(${this.track.clientWidth-(this.track.clientWidth+node.offsetWidth+20)*progress}px)`;
  }
 }
};
