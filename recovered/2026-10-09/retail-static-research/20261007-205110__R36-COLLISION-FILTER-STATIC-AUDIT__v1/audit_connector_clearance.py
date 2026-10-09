from pathlib import Path
import json,math,hashlib
repo=Path(r"F:\OpenRemaster\OpenAzrael")
faces=json.loads((repo/"evidence/retail/k001/r36_tun_conn01_faces_v1.json").read_text(encoding="utf-8-sig"))
matrix=json.loads((repo/"evidence/retail/object_matrix/retail_object_enriched_matrix_v1.json").read_text(encoding="utf-8-sig"))["objects_matrix"]
verts=faces["vertices"]
# Source frame boundaries are the repeated inner X/Y coordinates in the 8-vertex frame.
xs=sorted(set(round(v[0],7) for v in verts))
ys=sorted(set(round(v[1],7) for v in verts))
# Hole is bounded by inner X pair and middle Y pair.
inner_x=[x for x in xs if x not in (min(xs),max(xs))]
inner_y=[y for y in ys if y not in (min(ys),max(ys))]
assert len(xs)==4 and len(ys)==4 and len(inner_x)==2 and len(inner_y)==2
hole_w=inner_x[1]-inner_x[0]
hole_h=inner_y[1]-inner_y[0]
radius=11.0;height=52.0
horizontal_center_span=hole_w-2*radius
vertical_slack=hole_h-height
instances=[]
for r in matrix:
    n=str(r.get("name",""))
    if n.lower().startswith("tun_conn"):
        instances.append({k:r.get(k) for k in ("source_xaf","object_index","name","vertex_count","materials","roles","collision","evidence_state")})
out={
 "schema":"OpenAzrael.R36ConnectorCapsuleClearance.v1",
 "source_faces":"evidence/retail/k001/r36_tun_conn01_faces_v1.json",
 "source_xaf_sha256":"b542835adda16da2f6f9a945a255cee2cf52ccf5017450e978b6874bcae91c5e",
 "plane_z_range":[min(v[2] for v in verts),max(v[2] for v in verts)],
 "frame":{"outer_x":[min(xs),max(xs)],"inner_x":inner_x,"outer_y":[min(ys),max(ys)],"inner_y":inner_y,
          "opening_width":hole_w,"opening_height":hole_h},
 "production_capsule":{"radius":radius,"diameter":2*radius,"height":height},
 "minkowski_clearance":{"horizontal_center_span":horizontal_center_span,
                         "vertical_slack":vertical_slack,
                         "fits_width":horizontal_center_span>=0,
                         "fits_height":vertical_slack>=0,
                         "fits_full_opening":horizontal_center_span>=0 and vertical_slack>=0},
 "bidirectional_collision_implication":{
   "all_faces_normal_approx_minus_z":all(f["normal"][2] < -0.999 for f in faces["faces"]),
   "whole_frame_two_sided_or_bidirectional_collision":"CANNOT_PASS_WITH_11x52_CAPSULE" if vertical_slack<0 else "NOT_FALSIFIED",
   "one_sided_full_frame":"CANNOT_SATISFY_BIDIRECTIONAL_ROUTE_IF_FRONT_SIDE_BLOCKS_ONE_DIRECTION",
   "claim":"Current source frame plus required production capsule falsifies a simple whole-object, bidirectionally blocking collider as the final Retail traversal semantics. It does NOT by itself prove whole-object exclusion; selective face membership or other original collision semantics remain possible."
 },
 "corpus_tun_conn_instances":instances,
 "corpus_tun_conn_count":len(instances),
 "all_tun_conn_collision_unknown":all(r.get("collision")=="UNKNOWN_RETAIL_COLLISIONIR_BINDING" for r in instances),
 "evidence_state":"STRUCTURAL_FALSIFICATION",
 "fidelity":"NOT_VERIFIED"
}
p=Path(__file__).with_name("connector_capsule_clearance.json")
p.write_text(json.dumps(out,indent=2),encoding="utf-8")
print(json.dumps(out,indent=2))
