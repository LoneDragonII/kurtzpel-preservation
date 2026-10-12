"""Map each s2c packet name to its Deserialize function in the Dec 2019 client.

    python tools/re/handlers2019.py <exe> > notes/re/handlers2019.tsv

Handlers log L"-- [H] <NAME>" after a successful parse. Just before that, the code does
    Reader r; Struct s; r.Init(packet->body) [0x3bb800]; Deserialize(&s, &r) [target]; r.Done() [0x3c19d0]
so the deserializer is the call between 0x3bb800 and 0x3c19d0 preceding the log string reference.
"""
import sys, re, struct, collections, pefile, capstone
from capstone import x86

INIT, DONE = 0x3bb800, 0x3c19d0
exe = sys.argv[1]
pe = pefile.PE(exe, fast_load=True)
data = open(exe, 'rb').read()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)

strs = {}
for m in re.finditer(rb'-\x00-\x00 \x00\[\x00H\x00]\x00 \x00((?:[A-Z_]\x00)+)\x00\x00', data):
    strs[pe.get_rva_from_offset(m.start())] = m.group(1).decode('utf-16-le')
text = next(s for s in pe.sections if s.Name.startswith(b'.text'))
t = data[text.PointerToRawData:text.PointerToRawData + text.SizeOfRawData]; tva = text.VirtualAddress
res = collections.defaultdict(set)
for m in re.finditer(rb'[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]', t):
    p = m.start(); tgt = tva + p + 7 + struct.unpack_from('<i', t, p + 3)[0]
    if tgt not in strs: continue
    site = tva + p
    back = 0x200
    calls = [i for i in md.disasm(pe.get_data(site - back, back), site - back) if i.mnemonic == 'call' and i.op_str.startswith('0x')]
    tg = [int(c.op_str, 16) for c in calls]
    found = None
    for k in range(len(tg) - 1, -1, -1):
        if tg[k] == DONE:
            j = max(x for x in range(k) if tg[x] == INIT) if INIT in tg[:k] else None
            if j is not None and k - j >= 2:
                found = tg[k - 1]
            break
    res[strs[tgt]].add(f'{found:#x}' if found else '?')
for name in sorted(res):
    print(f'{name}\t{",".join(sorted(res[name]))}')
