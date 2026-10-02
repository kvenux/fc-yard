const assert=require('node:assert/strict'),fs=require('fs'),path=require('path'),{createServer}=require('../server.cjs');
(async()=>{const server=createServer();await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));try{
 const meta=JSON.parse(fs.readFileSync(path.join(__dirname,'runs/latest-video.json'))),p='/contra/runs/'+meta.video,b=fs.readFileSync(path.join(__dirname,'runs',meta.video)),url=`http://127.0.0.1:${server.address().port}${p}`;
 const r=await fetch(url,{headers:{Range:'bytes=100-199'}});assert.equal(r.status,206);assert.equal(r.headers.get('content-type'),'video/mp4');assert.equal(r.headers.get('content-range'),`bytes 100-199/${b.length}`);assert.deepEqual(Buffer.from(await r.arrayBuffer()),b.subarray(100,200));
 const suffix=await fetch(url,{headers:{Range:'bytes=-10'}});assert.deepEqual(Buffer.from(await suffix.arrayBuffer()),b.subarray(-10));
 assert.equal((await fetch(url,{headers:{Range:`bytes=${b.length}-`}})).status,416);
 assert.equal((await fetch(url,{method:'HEAD'})).headers.get('content-length'),String(b.length));
 console.log('Video byte ranges, suffix ranges, HEAD and invalid ranges verified.');
}finally{server.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
