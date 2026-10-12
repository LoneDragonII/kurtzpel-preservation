"""Static packet-schema extractor for the Dec 2019 story client (TheChase-Win64-Shipping.exe, UE 4.19.1).

    python tools/re/schema2019.py <exe> <deserializer_rva_hex> [max_depth]

In the 2019 build, packet structs are read by straight-line Deserialize(struct* this, Reader* r) functions:
    call READ_RAW(r, &this->field, n)   -> raw n-byte little-endian primitive, no tag byte
    call READ_FSTRING(r, &this->field)  -> u32 byte_len + UTF-16LE (byte_len must be even)
    call <other>(r, &this->field)       -> nested struct / TArray reader (recursed into)
Loops (backward jumps) are shown as [loop ...]; a TArray reader is a u32 count followed by a loop over the element.
Output is a nested schema for writing serializers by hand; check it against the handler before trusting it.
"""
import sys, functools, pefile, capstone
from capstone import x86

READ_RAW, READ_FSTRING = 0x3e1610, 0x3c3940
exe = sys.argv[1]
pe = pefile.PE(exe, fast_load=True)
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64); md.detail = True


@functools.lru_cache(None)
def insns(rva, limit=1500):
    code = pe.get_data(rva, limit * 5)
    out = []
    for ins in md.disasm(code, rva):
        out.append(ins)
        if len(out) >= limit: break
    # cut at the last ret that is followed by int3 padding and has no jump beyond it
    far = rva
    res = []
    for i, ins in enumerate(out):
        res.append(ins)
        if ins.group(capstone.CS_GRP_JUMP) and ins.operands and ins.operands[0].type == x86.X86_OP_IMM:
            far = max(far, ins.operands[0].imm)
        if ins.mnemonic in ('ret', 'jmp') and ins.address >= far:
            if ins.mnemonic == 'ret' or (ins.operands and ins.operands[0].type == x86.X86_OP_IMM):
                if i + 1 < len(out) and out[i + 1].mnemonic == 'int3' or ins.mnemonic == 'jmp':
                    break
    return res


_cache, _stack = {}, set()


def analyze(rva, depth):
    if rva in _cache: return _cache[rva]
    if depth < 0 or rva in _stack: return ()
    _stack.add(rva)
    r = _analyze(rva, depth)
    _stack.discard(rva)
    _cache[rva] = r
    return r


SKIP = {0xe4eb20, 0x297e536, 0x297e53c, 0xdff0c0, 0xdfecd0, 0x556df0, 0x59a080, 0x297c470}


def _analyze(rva, depth):
    """Return list of items: ('raw', off, n) | ('str', off) | ('call', off, target, sub) | ('loop', start, end)."""
    items, r8, rdx_off = [], None, None
    body = insns(rva)
    for ins in body:
        m, ops = ins.mnemonic, ins.operands
        if m == 'mov' and len(ops) == 2 and ops[0].type == x86.X86_OP_REG and ins.reg_name(ops[0].reg) in ('r8d', 'r8') and ops[1].type == x86.X86_OP_IMM:
            r8 = ops[1].imm
        if m == 'lea' and ins.reg_name(ops[0].reg) == 'rdx' and ops[1].type == x86.X86_OP_MEM:
            rdx_off = ops[1].mem.disp
        if m == 'call' and ops[0].type == x86.X86_OP_IMM:
            t = ops[0].imm
            if t == READ_RAW:
                items.append(('raw', ins.address, rdx_off, r8))
            elif t == READ_FSTRING:
                items.append(('str', ins.address, rdx_off))
            elif depth > 0 and t not in SKIP:
                sub = analyze(t, depth - 1)
                if contains_read(sub):
                    items.append(('call', ins.address, rdx_off, t, sub))
            r8 = rdx_off = None
        if ins.group(capstone.CS_GRP_JUMP) and m != 'jmp' and ops and ops[0].type == x86.X86_OP_IMM and ops[0].imm < ins.address and ops[0].imm >= rva:
            items.append(('loop', ops[0].imm, ins.address))
    return tuple(items)


def contains_read(items):
    return any(i[0] in ('raw', 'str') or (i[0] == 'call' and contains_read(i[4])) for i in items)


def show(items, ind=0):
    loops = [i for i in items if i[0] == 'loop']
    for it in items:
        if it[0] == 'loop': continue
        inl = [l for l in loops if l[1] <= it[1] <= l[2]]
        tag = ' [in loop %#x-%#x]' % (inl[0][1], inl[0][2]) if inl else ''
        off = '+%#x' % it[2] if it[2] is not None else '+?'
        if it[0] == 'raw':
            print('  ' * ind + f'{off:8} raw{it[3]}{tag}')
        elif it[0] == 'str':
            print('  ' * ind + f'{off:8} fstring{tag}')
        else:
            print('  ' * ind + f'{off:8} call {it[3]:#x}{tag}')
            show(it[4], ind + 1)


if __name__ == '__main__':
    show(analyze(int(sys.argv[2], 16), int(sys.argv[3]) if len(sys.argv) > 3 else 6))
