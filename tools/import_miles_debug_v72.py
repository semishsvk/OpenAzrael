#!/usr/bin/env python3
import argparse,json,pathlib,re
PAN=re.compile(r'AIL_set_sample_pan\(0x([0-9A-Fa-f]+),\s*(-?\d+)\)')
VOL=re.compile(r'AIL_set_sample_volume\(0x([0-9A-Fa-f]+),\s*(-?\d+)\)')

def parse_map(items):
    out={}
    for x in items:
        slot_s,handle_s=x.split('=',1)
        out[int(handle_s,0)] = int(slot_s,0)
    return out

def main():
    ap=argparse.ArgumentParser(description='Import independently generated Miles AIL_DEBUG pan/volume trace into OpenAzrael v71/v72 observation JSON.')
    ap.add_argument('log',type=pathlib.Path)
    ap.add_argument('--room-id',type=int,required=True)
    ap.add_argument('--slot-handle',action='append',default=[],metavar='SLOT=HANDLE',help='Explicit legacy slot to Miles sample handle mapping, e.g. 0=0x1234. Repeat per slot.')
    ap.add_argument('--out',type=pathlib.Path,required=True)
    a=ap.parse_args(); mapping=parse_map(a.slot_handle)
    latest={}; events=[]
    for n,line in enumerate(a.log.read_text(errors='replace').splitlines(),1):
        m=PAN.search(line)
        if m:
            h=int(m.group(1),16); v=int(m.group(2)); latest.setdefault(h,{})['pan']=v; events.append({'line':n,'kind':'pan','handle':hex(h),'value':v}); continue
        m=VOL.search(line)
        if m:
            h=int(m.group(1),16); v=int(m.group(2)); latest.setdefault(h,{})['volume']=v; events.append({'line':n,'kind':'volume','handle':hex(h),'value':v})
    observations=[]
    for h,vals in sorted(latest.items()):
        slot=mapping.get(h)
        observations.append({'room_id':a.room_id,'legacy_3d_slot':slot,'sample_handle':hex(h),'status':'OBSERVED' if slot is not None and 'pan' in vals and 'volume' in vals else 'UNMAPPED','pan':vals.get('pan'),'volume':vals.get('volume'),'provenance':'ORIGINAL_R_EXE_AIL_DEBUG','mapping_provenance':'EXPLICIT_SLOT_HANDLE' if slot is not None else None})
    out={'schema':'openazrael.miles_debug_observations','version':72,'source_log':str(a.log),'room_id':a.room_id,'events_parsed':len(events),'explicit_handle_mappings':len(mapping),'observations':observations,'events':events,'confidence_rule':'AIL values are independent original-runtime observations. Slot identity is accepted only when supplied explicitly; this importer never guesses handle-to-slot mapping.'}
    a.out.write_text(json.dumps(out,indent=2)+'\n')
    print('events',len(events),'handles',len(latest),'mapped_complete',sum(o['status']=='OBSERVED' for o in observations))
if __name__=='__main__': main()
