#!/usr/bin/env python3
import argparse,json,pathlib,re
PATS=[
 ('init',re.compile(r'AIL_init_sample\(0x([0-9A-Fa-f]+)\)')),
 ('file',re.compile(r'AIL_set_sample_file\(0x([0-9A-Fa-f]+),0x([0-9A-Fa-f]+),(-?\d+)\)')),
 ('address',re.compile(r'AIL_set_sample_address\(0x([0-9A-Fa-f]+),0x([0-9A-Fa-f]+),(\d+)\)')),
 ('start',re.compile(r'AIL_start_sample\(0x([0-9A-Fa-f]+)\)')),
 ('pan',re.compile(r'AIL_set_sample_pan\(0x([0-9A-Fa-f]+),\s*(-?\d+)\)')),
 ('volume',re.compile(r'AIL_set_sample_volume\(0x([0-9A-Fa-f]+),\s*(-?\d+)\)')),
 ('loop_count',re.compile(r'AIL_set_sample_loop_count\(0x([0-9A-Fa-f]+),\s*(-?\d+)\)')),
 ('status',re.compile(r'AIL_sample_status\(0x([0-9A-Fa-f]+)\)'))]
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('trace',type=pathlib.Path); ap.add_argument('--out',type=pathlib.Path,required=True); a=ap.parse_args()
 events=[]; handles={}
 for ln,line in enumerate(a.trace.read_text(errors='replace').splitlines(),1):
  for kind,rx in PATS:
   m=rx.search(line)
   if not m: continue
   h=int(m.group(1),16); ev={'line':ln,'kind':kind,'sample_handle':hex(h),'raw':m.group(0)}
   if kind in ('pan','volume','loop_count'): ev['value']=int(m.group(2))
   elif kind=='file': ev.update({'file_pointer':hex(int(m.group(2),16)),'block':int(m.group(3))})
   elif kind=='address': ev.update({'address':hex(int(m.group(2),16)),'length':int(m.group(3))})
   events.append(ev); handles.setdefault(hex(h),[]).append(len(events)-1); break
 out={'schema':'openazrael.miles_lifecycle_trace','version':73,'source':a.trace.name,'event_count':len(events),'handle_count':len(handles),'events':events,'handles':handles,'mapping_policy':'Per-handle grouping is observational. No AMB slot or filename is assigned without an independent anchor.','status':'OBSERVED_TRACE' if events else 'NO_EVENTS'}
 a.out.write_text(json.dumps(out,indent=2)+'\n'); print(out['status'],len(events),'events',len(handles),'handles')
if __name__=='__main__': main()
