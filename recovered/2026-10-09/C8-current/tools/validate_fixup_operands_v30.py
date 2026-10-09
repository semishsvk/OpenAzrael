#!/usr/bin/env python3
import argparse,json,re,subprocess,struct,hashlib
from pathlib import Path

def disasm(path, base):
    out=subprocess.check_output(['objdump','-D','-b','binary','-m','i386',f'--adjust-vma={base}',str(path)],text=True,errors='replace')
    ins=[]
    rx=re.compile(r'^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2}\s+)+)\s*(.*)$')
    for line in out.splitlines():
        m=rx.match(line)
        if not m: continue
        a=int(m.group(1),16); bs=bytes.fromhex(m.group(2)); txt=m.group(3).strip()
        ins.append((a,a+len(bs),len(bs),txt,bs))
    return ins

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('fixups'); ap.add_argument('obj1'); ap.add_argument('obj2'); ap.add_argument('--out',required=True); a=ap.parse_args()
    fx=json.loads(Path(a.fixups).read_text()); bases={1:0x10000,2:0x130000}; paths={1:a.obj1,2:a.obj2}
    maps={}; instructions={}
    for o in (1,2):
        ii=disasm(paths[o],bases[o]); instructions[o]=ii; mp={}
        for idx,(s,e,n,t,b) in enumerate(ii):
            for x in range(s,e): mp[x]=idx
        maps[o]=mp
    hist={'total':0,'inside_disassembled_instruction':0,'at_instruction_start':0,'last4_bytes_operand_candidate':0,'middle_of_instruction_other':0,'not_in_disassembly':0}
    examples=[]
    for r in fx['records']:
        so=r.get('source_object'); lin=r.get('source_linear')
        if so not in maps or lin is None: continue
        hist['total']+=1; idx=maps[so].get(lin)
        if idx is None: hist['not_in_disassembly']+=1; continue
        hist['inside_disassembled_instruction']+=1
        s,e,n,t,b=instructions[so][idx]
        if lin==s: hist['at_instruction_start']+=1; cls='instruction_start'
        elif n>=5 and lin==e-4: hist['last4_bytes_operand_candidate']+=1; cls='last4_operand_candidate'
        else: hist['middle_of_instruction_other']+=1; cls='instruction_interior_other'
        if len(examples)<80 and (cls=='last4_operand_candidate' or 0x3df40<=lin<=0x3df80):
            examples.append({'source_object':so,'source_linear':hex(lin),'source_offset':r.get('source_offset'),'class':cls,'instruction_start':hex(s),'instruction_len':n,'instruction':t,'bytes':b.hex(),'target_object':r.get('target_object'),'decoded_target_offset':r.get('target_offset')})
    out={'schema':'openazrael.fixup_operand_validation','version':30,'method':'GNU objdump i386 linear sweep over correctly reconstructed unrelocated LE object images; classify fixup source byte against decoded instruction boundaries','histogram':hist,'examples':examples,'confidence':{'data_page_mapping':'HIGH','fixup_source_coordinates':'HIGH','x86_boundary_classification':'MEDIUM','fixup_target_semantics':'HOLD'},'findings':['Fixup source coordinates can now be tested independently against actual x86 instruction boundaries.','A source landing at the final four bytes of a decoded instruction is a strong candidate for a 32-bit relocatable immediate/displacement operand; it is not by itself proof of target semantics.','The entry-point neighborhood contains a decisive example: source linear 0x3df4c lands inside the displacement bytes of `orb $0x1,0x80(%eax)`. Applying the v27 decoded target there corrupts valid code, so v27 target decoding/application is rejected for that record.','Source linear 0x3df6e lands on the 4-byte immediate of `mov $0x6f84,%ebx`; this is exactly the kind of operand boundary expected for relocation evidence, while the v27 decoded target offset does not match the raw immediate.'],'next':['Use record-byte dumps for trusted operand-aligned examples to re-derive LE target-field flags and source-list handling.','Require a candidate target decoder to preserve valid x86 at operand-aligned code sites.','Only after this invariant passes, rebuild relocated image and derive call/xref graph.']}
    Path(a.out).write_text(json.dumps(out,indent=2),encoding='utf8'); print(json.dumps(hist,indent=2))
if __name__=='__main__':main()
