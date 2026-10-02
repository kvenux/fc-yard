"""Read-only 68000 input-command inspection from the user's local ROM."""
import argparse,zipfile
from capstone import Cs,CS_ARCH_M68K,CS_MODE_BIG_ENDIAN,CS_MODE_M68K_000
from orlegend import ROM
p=argparse.ArgumentParser();p.add_argument('address',type=lambda x:int(x,16));p.add_argument('--bytes',type=int,default=400);a=p.parse_args()
with zipfile.ZipFile(ROM) as z:raw=bytearray(z.read('pgm_p0103.u2'))
raw[0::2],raw[1::2]=raw[1::2],raw[0::2]
md=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000)
for i in md.disasm(bytes(raw[a.address-0x100000:a.address-0x100000+a.bytes]),a.address):print(f'{i.address:06x} {i.mnemonic:10s} {i.op_str}')
