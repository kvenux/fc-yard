import zipfile
from orlegend import ROM
with zipfile.ZipFile(ROM) as z:r=bytearray(z.read('pgm_p0103.u2'))
r[0::2],r[1::2]=r[1::2],r[0::2]
for pattern in ['119d','119c','118b','81118a','81118b','811100','00810000']:
 p=bytes.fromhex(pattern);start=0;found=[]
 while (idx:=r.find(p,start))>=0:found.append(hex(0x100000+idx));start=idx+1
 print(pattern,found[:120])
