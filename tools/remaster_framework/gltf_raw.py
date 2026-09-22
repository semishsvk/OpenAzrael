from __future__ import annotations

import io
import json
import math
import struct
from pathlib import Path

import numpy as np
from PIL import Image

_COMPONENT_DTYPE = {
    5120: np.int8,
    5121: np.uint8,
    5122: np.int16,
    5123: np.uint16,
    5125: np.uint32,
    5126: np.float32,
}
_COMPONENTS = {
    "SCALAR": 1,
    "VEC2": 2,
    "VEC3": 3,
    "VEC4": 4,
    "MAT2": 4,
    "MAT3": 9,
    "MAT4": 16,
}

def read_glb(path: Path) -> tuple[dict, bytes]:
    data = Path(path).read_bytes()
    if len(data) < 20:
        raise ValueError("short GLB")
    magic, version, total = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or total != len(data):
        raise ValueError("invalid GLB 2.0 header")
    offset = 12
    gltf = None
    binary = b""
    while offset < len(data):
        length, kind = struct.unpack_from("<II", data, offset)
        offset += 8
        chunk = data[offset:offset + length]
        offset += length
        if kind == 0x4E4F534A:
            gltf = json.loads(chunk.decode("utf-8").rstrip("\x00 "))
        elif kind == 0x004E4942:
            binary = chunk
    if gltf is None:
        raise ValueError("GLB JSON chunk missing")
    return gltf, binary

def accessor_array(gltf: dict, binary: bytes, accessor_index: int) -> np.ndarray:
    acc = gltf["accessors"][accessor_index]
    view = gltf["bufferViews"][acc["bufferView"]]
    dtype = np.dtype(_COMPONENT_DTYPE[acc["componentType"]]).newbyteorder("<")
    width = _COMPONENTS[acc["type"]]
    count = int(acc["count"])
    offset = int(view.get("byteOffset", 0)) + int(acc.get("byteOffset", 0))
    stride = int(view.get("byteStride", dtype.itemsize * width))
    if stride == dtype.itemsize * width:
        return np.frombuffer(
            binary, dtype=dtype, count=count * width, offset=offset
        ).reshape(count, width).copy()
    out = np.empty((count, width), dtype=dtype)
    for row in range(count):
        out[row] = np.frombuffer(
            binary, dtype=dtype, count=width, offset=offset + row * stride
        )
    return out

def _quat_matrix(q) -> np.ndarray:
    x, y, z, w = (float(v) for v in q)
    n = x*x + y*y + z*z + w*w
    if n <= 1e-20:
        return np.eye(4)
    s = 2.0 / n
    xx, yy, zz = x*x*s, y*y*s, z*z*s
    xy, xz, yz = x*y*s, x*z*s, y*z*s
    wx, wy, wz = w*x*s, w*y*s, w*z*s
    return np.array([
        [1-(yy+zz), xy-wz, xz+wy, 0],
        [xy+wz, 1-(xx+zz), yz-wx, 0],
        [xz-wy, yz+wx, 1-(xx+yy), 0],
        [0, 0, 0, 1],
    ], dtype=float)

def node_local_matrix(node: dict) -> np.ndarray:
    if "matrix" in node:
        # glTF serializes matrices column-major.
        return np.asarray(node["matrix"], dtype=float).reshape(4, 4).T
    t = np.eye(4)
    t[:3, 3] = np.asarray(node.get("translation", [0, 0, 0]), dtype=float)
    r = _quat_matrix(node.get("rotation", [0, 0, 0, 1]))
    s = np.eye(4)
    scale = np.asarray(node.get("scale", [1, 1, 1]), dtype=float)
    s[0,0], s[1,1], s[2,2] = scale
    return t @ r @ s

def node_world_matrices(gltf: dict) -> dict[int, np.ndarray]:
    parents: dict[int, int] = {}
    for index, node in enumerate(gltf.get("nodes", [])):
        for child in node.get("children", []):
            parents[int(child)] = index
    cache: dict[int, np.ndarray] = {}
    def world(index: int) -> np.ndarray:
        if index not in cache:
            local = node_local_matrix(gltf["nodes"][index])
            parent = parents.get(index)
            cache[index] = world(parent) @ local if parent is not None else local
        return cache[index]
    return {i: world(i) for i in range(len(gltf.get("nodes", [])))}

def image_rgba(gltf: dict, binary: bytes, image_index: int) -> Image.Image:
    item = gltf["images"][image_index]
    if "bufferView" not in item:
        raise ValueError("external/data-URI images are not accepted in canonical GLB")
    view = gltf["bufferViews"][item["bufferView"]]
    start = int(view.get("byteOffset", 0))
    end = start + int(view["byteLength"])
    with Image.open(io.BytesIO(binary[start:end])) as image:
        image.load()
        return image.convert("RGBA").copy()

def primitive_base_color_image(
    gltf: dict, binary: bytes, primitive: dict
) -> Image.Image | None:
    material_index = primitive.get("material")
    if material_index is None:
        return None
    material = gltf["materials"][material_index]
    pbr = material.get("pbrMetallicRoughness", {})
    base = pbr.get("baseColorTexture")
    if not base:
        return None
    texture = gltf["textures"][base["index"]]
    source = texture.get("source")
    return image_rgba(gltf, binary, source) if source is not None else None
