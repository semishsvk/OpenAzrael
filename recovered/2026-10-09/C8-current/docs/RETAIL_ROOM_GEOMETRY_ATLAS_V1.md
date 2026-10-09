# Retail Room Geometry Atlas v1

This tool prepares the retail OpenAzrael room-map geometry layer without committing commercial game payloads.

## Purpose

`tools/build_retail_room_geometry_atlas.py` scans a local directory of restored/generated `R*.glb` room assets and emits:

- one top-down X/Z wireframe PNG per room;
- compact geometry metadata (vertex/triangle counts and XYZ/XZ bounds);
- a machine-readable `room_geometry_atlas.json` coverage manifest.

The tool is intentionally source-safe: GLB/XAF payloads stay local and are not copied into Git.

## Evidence rule

Asset IDs such as `R1.glb` MUST NOT be automatically equated with retail walkthrough/runtime IDs such as `r01`.

Canonical room bindings are accepted only through an explicit `--bindings` JSON file. This prevents false assignments between demo asset IDs and retail runtime IDs.

Example:

```json
{
  "bindings": {
    "R1": ["Entry corridor"],
    "R7": ["Well"],
    "R8": ["Baptistery"]
  }
}
```

For the current preview these three bindings mean **demo-equivalent geometry only**. They do not claim direct retail-XAF identity.

## Usage

```bash
python tools/build_retail_room_geometry_atlas.py \
  /path/to/local/retail_glb_rooms \
  .tmp/retail_geometry_atlas \
  --inventory /path/to/retail_room_inventory_v0.2.json \
  --bindings /path/to/evidence_bindings.json
```

If the local room directory eventually contains the complete retail corpus, the same command produces thumbnails and geometry metadata for every available room automatically.

## Current coverage

The archived OpenAzrael build corpus currently exposes full GLB geometry for demo rooms R1, R7 and R8 only. Their canonical equivalents are Entry corridor, Well and Baptistery.

All other retail locations remain **PENDING_RETAIL_XAF** until the local retail XAF/GLB corpus is mounted and processed. The map should never invent missing room geometry.

## State variants

The canonical retail inventory keeps topology/geometry-changing room states separate from ordinary puzzle flags. Examples include:

- Ziggurat base/dry vs flooded;
- Grain silo / Execution Room base vs flooded;
- Orrery vs Perilous Chapel transformation;
- Grail sanctum pre/post Grail transition;
- Aqueduct flooded/drained topology.

When both state meshes become available, the atlas/map layer should render them as explicit sibling variants rather than silently replacing one with the other.
