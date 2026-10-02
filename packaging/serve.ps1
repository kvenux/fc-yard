param([int]$Port=8787,[switch]$NoBrowser)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath($PSScriptRoot)
$listener=$null
for($candidate=$Port;$candidate -lt $Port+20;$candidate++){
  try{$listener=[Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,$candidate);$listener.Start();$Port=$candidate;break}
  catch{if($listener){$listener.Stop()};$listener=$null}
}
if(!$listener){throw 'No available local port'}
$url="http://127.0.0.1:$Port/live.html"
Write-Host "FC AI Live: $url"
Write-Host 'Keep this window open while playing. Press Ctrl+C to stop.'
if(!$NoBrowser){Start-Process $url}
$types=@{'.html'='text/html; charset=utf-8';'.js'='text/javascript; charset=utf-8';'.css'='text/css; charset=utf-8';'.json'='application/json; charset=utf-8';'.png'='image/png';'.md'='text/plain; charset=utf-8'}
try{
  while($true){
    $client=$listener.AcceptTcpClient()
    try{
      $client.ReceiveTimeout=5000;$client.SendTimeout=5000
      $stream=$client.GetStream();$reader=[IO.StreamReader]::new($stream,[Text.Encoding]::ASCII,$false,1024,$true)
      $request=$reader.ReadLine();if(!$request){continue}
      while($reader.ReadLine()){}
      $parts=$request.Split(' ');$status='200 OK';$mime='text/plain; charset=utf-8';$body=[byte[]]@()
      if($parts[0] -notin @('GET','HEAD')){$status='405 Method Not Allowed'}
      else{
        $relative=[Uri]::UnescapeDataString(($parts[1].Split('?')[0])).TrimStart('/')
        if(!$relative){$relative='live.html'}
        $path=[IO.Path]::GetFullPath([IO.Path]::Combine($root,$relative.Replace('/',[IO.Path]::DirectorySeparatorChar)))
        if(!$path.StartsWith($root+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){$status='403 Forbidden'}
        elseif(![IO.File]::Exists($path)){$status='404 Not Found'}
        else{$body=[IO.File]::ReadAllBytes($path);$ext=[IO.Path]::GetExtension($path);$mime=$types[$ext];if(!$mime){$mime='application/octet-stream'}}
      }
      $header=[Text.Encoding]::ASCII.GetBytes("HTTP/1.1 $status`r`nContent-Type: $mime`r`nContent-Length: $($body.Length)`r`nCache-Control: no-store`r`nConnection: close`r`n`r`n")
      $stream.Write($header,0,$header.Length)
      if($parts[0] -ne 'HEAD' -and $body.Length){$stream.Write($body,0,$body.Length)}
      $stream.Flush()
    }catch{Write-Verbose $_}finally{$client.Close()}
  }
}finally{$listener.Stop()}
