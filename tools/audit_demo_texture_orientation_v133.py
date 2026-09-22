#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import argparse
import hashlib
import json
import sys

import numpy as np
from PIL import Image

from tools.remaster_framework.gltf_raw import (
    accessor_array,
    node_world_matrices,
    primitive_base_color_image,
    read_glb,
)

ROOT = Path(__file__).resolve().parents[1]
ROOM_IDS = ("R1", "R7", "R8")
ROOM_DIR = ROOT / "assets/rooms"
TEX_DIR = ROOT / "assets/textures/classic"
CONTRACT = ROOT / "data/tests/kg001_texture_orientation_contract_v133.json"
RESTORE_EVIDENCE = ROOT / ".tmp/kg001/candidate4_texture_restore_v133.json"
DEFAULT_OUT = ROOT / "data/runtime_generated/demo_texture_orientation_v133.json"
TAPESTRY_SCRIPT = ROOT / "scripts/r8_tapestry_interaction.gd"

def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def float32_sha(values: np.ndarray) -> str:
    return hashlib.sha256(
        np.asarray(values, dtype="<f4").tobytes()
    ).hexdigest()

def rgba_sha(image: Image.Image) -> str:
    return hashlib.sha256(
        np.asarray(image.convert("RGBA"), dtype=np.uint8).tobytes()
    ).hexdigest()

def correlation(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if len(a) < 2 or np.ptp(a) < 1e-8 or np.ptp(b) < 1e-8:
        return None
    return float(np.corrcoef(a, b)[0, 1])

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    failures: list[str] = []
    warnings: list[str] = []

    if not RESTORE_EVIDENCE.is_file():
        failures.append("original_source_restore_evidence_missing")
        restore = {}
    else:
        restore = json.loads(RESTORE_EVIDENCE.read_text(encoding="utf-8"))
        if (
            restore.get("schema") != "openazrael.kg001.candidate4_texture_restore"
            or restore.get("version") != 133
            or restore.get("status") != "PASS"
        ):
            failures.append("original_source_restore_evidence_invalid")

    pngs = sorted(TEX_DIR.glob("*.png"))
    if len(pngs) != int(contract["expected_classic_texture_count"]):
        failures.append(f"classic_texture_count:{len(pngs)}")
    png_index = {p.stem.upper(): p for p in pngs}

    restore_texture_rows = {
        row["texture"]: row for row in restore.get("textures", [])
    }
    if len(restore_texture_rows) != 86:
        failures.append(
            f"restore_texture_evidence_count:{len(restore_texture_rows)}"
        )

    texture_inventory = []
    for png in pngs:
        row = restore_texture_rows.get(png.name)
        hash_ok = (
            row is not None
            and file_sha(png) == str(row.get("runtime_png_sha256", ""))
        )
        if not hash_ok:
            failures.append("restored_png_hash:" + png.name)
        texture_inventory.append({
            "file": png.name,
            "sha256": file_sha(png),
            "source_azf": None if row is None else row.get("source_azf"),
            "source_azf_sha256": (
                None if row is None else row.get("source_azf_sha256")
            ),
            "restore_hash_match": hash_ok,
        })

    expected_adapter = contract["uv_export_adapter"]["mode"]
    used_textures: set[str] = set()
    primitive_rows = []
    strong_vertical = []
    source_uv_exact = 0
    embedded_exact = 0
    textured_primitive_count = 0
    room_restore_rows = {
        row["room"]: row for row in restore.get("rooms", [])
    }

    for room_id in ROOM_IDS:
        glb_path = ROOM_DIR / f"{room_id}.glb"
        manifest_path = ROOT / "data" / f"{room_id}.textured.v44.manifest.json"
        if not glb_path.is_file():
            failures.append("missing_glb:" + room_id)
            continue
        if not manifest_path.is_file():
            failures.append("missing_room_manifest:" + room_id)
            continue

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        room_restore = room_restore_rows.get(room_id)
        if room_restore is None:
            failures.append(room_id + ":restore_room_evidence_missing")
        else:
            if file_sha(glb_path) != room_restore.get("runtime_glb_sha256"):
                failures.append(room_id + ":restored_glb_hash_changed")
            if (
                manifest.get("source_xaf_sha256")
                != room_restore.get("source_xaf_sha256")
            ):
                failures.append(room_id + ":source_xaf_identity_mismatch")

        if manifest.get("uv_export_policy") != expected_adapter:
            failures.append(room_id + ":uv_export_policy")

        source_primitives = {
            str(row["node"]): row for row in manifest.get("primitives", [])
        }

        gltf, binary = read_glb(glb_path)
        worlds = node_world_matrices(gltf)

        for node_index, node in enumerate(gltf.get("nodes", [])):
            mesh_index = node.get("mesh")
            if mesh_index is None:
                continue
            mesh = gltf["meshes"][mesh_index]
            extras = mesh.get("extras", {}) or {}
            tex_name = extras.get("xaf_texture")
            if not tex_name:
                continue
            if len(mesh.get("primitives", [])) != 1:
                failures.append(
                    f"{room_id}/{node.get('name','')}:unexpected_primitive_count"
                )
                continue

            primitive = mesh["primitives"][0]
            node_name = str(node.get("name", ""))
            source_row = source_primitives.get(node_name)
            if source_row is None:
                failures.append(f"{room_id}/{node_name}:source_manifest_missing")
                continue

            textured_primitive_count += 1
            texture_stem = Path(str(tex_name)).stem.upper()
            used_textures.add(texture_stem)
            png = png_index.get(texture_stem)
            if png is None:
                failures.append(
                    f"{room_id}/{node_name}:missing_texture:{tex_name}"
                )
                continue

            position_accessor = primitive.get("attributes", {}).get("POSITION")
            uv_accessor = primitive.get("attributes", {}).get("TEXCOORD_0")
            if position_accessor is None or uv_accessor is None:
                failures.append(f"{room_id}/{node_name}:position_or_uv_missing")
                continue

            positions = accessor_array(gltf, binary, position_accessor)
            uv = accessor_array(gltf, binary, uv_accessor)
            uv_count_ok = len(uv) == len(positions)
            uv_finite = bool(np.isfinite(uv).all())
            if not uv_count_ok:
                failures.append(f"{room_id}/{node_name}:uv_count")
            if not uv_finite:
                failures.append(f"{room_id}/{node_name}:uv_nonfinite")

            source_uv_hash = str(source_row.get("source_uv_sha256", ""))
            raw_uv_hash = float32_sha(uv)
            uv_source_exact = (
                len(source_uv_hash) == 64
                and source_uv_hash == raw_uv_hash
                and int(source_row.get("source_uv_count", -1)) == len(uv)
            )
            if not uv_source_exact:
                failures.append(f"{room_id}/{node_name}:raw_uv_not_source_exact")
            else:
                source_uv_exact += 1

            if source_row.get("uv_correction") != expected_adapter:
                failures.append(
                    f"{room_id}/{node_name}:unexpected_export_adapter:"
                    + str(source_row.get("uv_correction"))
                )

            embedded = primitive_base_color_image(gltf, binary, primitive)
            if embedded is None:
                failures.append(f"{room_id}/{node_name}:embedded_texture_missing")
                embedded_match = False
            else:
                with Image.open(png) as restored_png:
                    restored_png.load()
                    embedded_match = rgba_sha(embedded) == rgba_sha(restored_png)
                if not embedded_match:
                    failures.append(
                        f"{room_id}/{node_name}:embedded_texture_mismatch:{png.name}"
                    )
                else:
                    embedded_exact += 1

            world = worlds[node_index]
            world_positions = (
                np.c_[positions, np.ones(len(positions))] @ world.T
            )[:, :3]
            cyu = correlation(world_positions[:, 1], uv[:, 0])
            cyv = correlation(world_positions[:, 1], uv[:, 1])
            y_span = float(np.ptp(world_positions[:, 1]))
            u_span = float(np.ptp(uv[:, 0]))
            v_span = float(np.ptp(uv[:, 1]))

            row = {
                "room": room_id,
                "node": node_name,
                "texture": texture_stem,
                "png": png.name,
                "vertices": int(len(positions)),
                "uv_count": int(len(uv)),
                "y_span": y_span,
                "u_span": u_span,
                "v_span": v_span,
                "corr_world_y_u": cyu,
                "corr_world_y_v": cyv,
                "source_uv_exact": uv_source_exact,
                "embedded_texture_match": embedded_match,
            }
            primitive_rows.append(row)

            is_strong = (
                y_span >= 10.0
                and v_span >= 0.25
                and cyv is not None
                and abs(cyv) >= 0.75
                and (cyu is None or abs(cyv) >= abs(cyu))
            )
            if is_strong:
                strong_vertical.append({
                    **row,
                    "orientation": (
                        "UPRIGHT" if cyv < 0 else "SOURCE_REVERSED"
                    ),
                })

    if len(used_textures) != int(contract["expected_used_texture_count"]):
        failures.append(f"used_texture_count:{len(used_textures)}")
    if textured_primitive_count != int(
        contract["expected_textured_primitive_count"]
    ):
        failures.append(
            f"textured_primitive_count:{textured_primitive_count}"
        )
    if source_uv_exact != textured_primitive_count:
        failures.append(
            f"source_uv_exact_count:{source_uv_exact}/{textured_primitive_count}"
        )
    if embedded_exact != textured_primitive_count:
        failures.append(
            f"embedded_texture_exact_count:{embedded_exact}/"
            f"{textured_primitive_count}"
        )

    unused = sorted(
        p.name for p in pngs if p.stem.upper() not in used_textures
    )
    if unused != sorted(contract.get("expected_unused_textures", [])):
        failures.append("unused_texture_inventory_changed")

    expected_strong = int(contract["expected_strong_vertical_mappings"])
    expected_upright = int(contract["expected_direct_upright_vertical_mappings"])
    if len(strong_vertical) != expected_strong:
        failures.append(f"strong_vertical_count:{len(strong_vertical)}")
    direct_upright = [r for r in strong_vertical if r["orientation"] == "UPRIGHT"]
    reversed_rows = [
        r for r in strong_vertical if r["orientation"] == "SOURCE_REVERSED"
    ]
    if len(direct_upright) != expected_upright:
        failures.append(f"direct_upright_count:{len(direct_upright)}")

    expected_variants = {
        (row["room"], row["node"], row["texture"])
        for row in contract.get("source_authored_state_variants", [])
    }
    actual_variants = {
        (row["room"], row["node"], row["texture"])
        for row in reversed_rows
    }
    if actual_variants != expected_variants:
        failures.append(
            "source_orientation_variants:"
            + json.dumps(sorted(actual_variants))
        )

    by_key = {(r["room"], r["node"]): r for r in primitive_rows}

    # Candidate 3 keyhole regression sentinel: small object, so audit it even
    # though it does not meet the generic y-span threshold.
    keyhole = by_key.get(("R1", "doorcor2__1KEYHOLE"))
    if (
        keyhole is None
        or keyhole["texture"] != "KEYHOLE#"
        or keyhole["corr_world_y_v"] is None
        or keyhole["corr_world_y_v"] >= -0.75
    ):
        failures.append("R1/keyhole:not_upright")

    window_textures = {"BAPBACK1", "BAPFRNT1", "BAPLEFT1", "BAPRGHT1"}
    window_rows = [
        r for r in strong_vertical
        if r["room"] == "R8" and r["texture"] in window_textures
    ]
    if not window_rows:
        failures.append("R8/window_rows_missing")
    for row in window_rows:
        if row["orientation"] != "UPRIGHT":
            failures.append(
                f"R8/{row['node']}:window_upside_down:{row['texture']}"
            )

    # The hidden readable message is authored as the vertically reversed back
    # face of tapestry2.  It is NOT a UV defect.  The production reveal must
    # rotate the parent around the horizontal X axis by PI, which reveals the
    # back and flips its world-Y orientation to upright.
    message = by_key.get(("R8", "tapestry2a__mesh"))
    script = (
        TAPESTRY_SCRIPT.read_text(encoding="utf-8")
        if TAPESTRY_SCRIPT.is_file() else ""
    )
    if (
        message is None
        or message["texture"] != "BAPMSG"
        or message["corr_world_y_v"] is None
        or message["corr_world_y_v"] <= 0.75
    ):
        failures.append("R8/BAPMSG:source_backface_orientation_changed")
    if (
        'rotate_x(PI)' not in script
        or '"rotation:x"' not in script
        or '"rotation:y"' in script
    ):
        failures.append("R8/BAPMSG:horizontal_reveal_transform_missing")

    result = {
        "schema": "openazrael.kg001.texture_orientation_audit",
        "version": 133,
        "status": "PASS" if not failures else "FAIL",
        "gltf_texture_origin": "upper_left",
        "uv_export_adapter": expected_adapter,
        "classic_texture_count": len(pngs),
        "used_texture_count": len(used_textures),
        "unused_texture_count": len(unused),
        "unused_textures": unused,
        "textured_primitive_count": textured_primitive_count,
        "source_uv_exact_count": source_uv_exact,
        "embedded_texture_exact_count": embedded_exact,
        "strong_vertical_count": len(strong_vertical),
        "direct_upright_vertical_count": len(direct_upright),
        "source_state_variant_count": len(reversed_rows),
        "source_state_variants": reversed_rows,
        "r8_window_sentinel_count": len(window_rows),
        "failures": failures,
        "warnings": warnings,
        "texture_inventory": texture_inventory,
        "strong_vertical": strong_vertical,
        "primitives": primitive_rows,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        key: result[key] for key in (
            "status",
            "classic_texture_count",
            "used_texture_count",
            "unused_texture_count",
            "textured_primitive_count",
            "source_uv_exact_count",
            "embedded_texture_exact_count",
            "strong_vertical_count",
            "direct_upright_vertical_count",
            "source_state_variant_count",
            "r8_window_sentinel_count",
            "failures",
        )
    }, indent=2))
    return 0 if not failures else 1

if __name__ == "__main__":
    raise SystemExit(main())
