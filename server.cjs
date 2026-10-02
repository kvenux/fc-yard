const http=require('http'),fs=require('fs'),path=require('path');
const root=__dirname;
function createServer(){return http.createServer((req,res)=>{
  let p;
  try{const url=req.url.split('?')[0];p=path.resolve(root,'.'+decodeURIComponent(url==='/'?'/hub.html':url));}
  catch{res.writeHead(400).end();return;}
  if(!p.startsWith(root+path.sep)||path.relative(root,p).split(path.sep).some(x=>x.startsWith('.'))) {res.writeHead(403).end();return;}
  fs.stat(p,(error,stat)=>{
    if(error||!stat.isFile()){res.writeHead(404).end('Not found');return;}
    const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript','.css':'text/css; charset=utf-8','.png':'image/png','.json':'application/json','.mp4':'video/mp4'};
    res.setHeader('Content-Type',mime[path.extname(p)]||'application/octet-stream');res.setHeader('Accept-Ranges','bytes');
    let start=0,end=stat.size-1,status=200;
    if(req.headers.range){
      const range=/^bytes=(\d*)-(\d*)$/.exec(req.headers.range);
      if(!range||(!range[1]&&!range[2])||!stat.size){res.writeHead(416,{'Content-Range':`bytes */${stat.size}`}).end();return;}
      if(!range[1])start=Math.max(0,stat.size-Number(range[2]));
      else{start=Number(range[1]);if(range[2])end=Math.min(end,Number(range[2]));}
      if(!Number.isSafeInteger(start)||!Number.isSafeInteger(end)||start>end||start>=stat.size){res.writeHead(416,{'Content-Range':`bytes */${stat.size}`}).end();return;}
      status=206;res.setHeader('Content-Range',`bytes ${start}-${end}/${stat.size}`);
    }
    res.setHeader('Content-Length',Math.max(0,end-start+1));res.writeHead(status);
    if(req.method==='HEAD'||!stat.size){res.end();return;}
    const stream=fs.createReadStream(p,{start,end});stream.on('error',()=>res.destroy());res.on('close',()=>stream.destroy());stream.pipe(res);
  });
});}
if(require.main===module){const port=Number(process.env.PORT||8787);createServer().listen(port,'127.0.0.1',()=>console.log(`http://127.0.0.1:${port}`));}
module.exports={createServer};
