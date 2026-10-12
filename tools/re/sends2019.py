"""Map c2s opcodes to their Serialize functions in the Dec 2019 client.

    python tools/re/sends2019.py <exe> <opnames_2019.json>

Every outgoing packet goes through a per-struct send template:
    Writer w; w.Init(buf) [0x3bb800]; Serialize(&s, &w) [target]; w.Done() [0x3c19d0]; ... encrypt [0x5b10c0]
and callers pass the opcode in dx (`mov edx, imm16` shortly before the call).
"""
import sys, re, struct, json, collections, pefile, capstone
from capstone import x86

INIT, DONE, ENCRYPT = 0x3bb800, 0x3c19d0, 0x5b10c0
exe = sys.argv[1]
names = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else {}
pe = pefile.PE(exe, fast_load=True)
data = open(exe, 'rb').read()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64); md.detail = True
text = next(s for s in pe.sections if s.Name.startswith(b'.text'))
t = data[text.PointerToRawData:text.PointerToRawData + text.SizeOfRawData]; tva = text.VirtualAddress

calls = collections.defaultdict(list)  # target -> [site]
for m in re.finditer(rb'\xe8', t):
    p = m.start(); tgt = tva + p + 5 + struct.unpack_from('<i', t, p + 1)[0]
    if tgt in (INIT, DONE, ENCRYPT): calls[tgt].append(tva + p)

def func_start(site):
    """Walk back to the previous int3/padding boundary."""
    p = site - tva
    while p > 0 and not (t[p - 1] == 0xcc and t[p] != 0xcc):
        p -= 1
    return tva + p

templates = {}
for enc in calls[ENCRYPT]:
    f = func_start(enc)
    inits = [s for s in calls[INIT] if f <= s < enc]
    dones = [s for s in calls[DONE] if f <= s < enc]
    if not inits or not dones: continue
    seg = pe.get_data(inits[0], dones[0] + 5 - inits[0])
    cs = [i for i in md.disasm(seg, inits[0]) if i.mnemonic == 'call' and i.op_str.startswith('0x')]
    if len(cs) >= 3:
        templates[f] = int(cs[-2].op_str, 16)

# callers of each template with an immediate opcode in edx
tcalls = collections.defaultdict(list)
for m in re.finditer(rb'\xe8', t):
    p = m.start(); tgt = tva + p + 5 + struct.unpack_from('<i', t, p + 1)[0]
    if tgt in templates: tcalls[tgt].append(tva + p)
out = {}
for tpl, sites in tcalls.items():
    for s in sites:
        back = pe.get_data(s - 48, 48)
        op = None
        for k in range(len(back) - 5, -1, -1):
            if back[k] == 0xba:  # mov edx, imm32
                op = struct.unpack_from('<I', back, k + 1)[0]; break
            if back[k:k + 2] == b'\x66\xba':
                op = struct.unpack_from('<H', back, k + 2)[0]; break
        if op is not None and op < 0x200:
            out.setdefault(op, set()).add((tpl, templates[tpl]))
for op in sorted(out):
    n = names.get(f'0x{op:04x}', '?')
    print(f'0x{op:04x}\t{n}\t' + ','.join(f'tpl={a:#x} ser={b:#x}' for a, b in sorted(out[op])))

if '--debug' in sys.argv:
    miss = [e for e in calls[ENCRYPT] if func_start(e) not in templates]
    print('encrypt sites', len(calls[ENCRYPT]), 'templates', len(templates), 'unmatched', [hex(x) for x in miss[:40]], file=sys.stderr)
    for tpl in templates:
        if tpl not in tcalls: print('template without imm caller', hex(tpl), hex(templates[tpl]), file=sys.stderr)
