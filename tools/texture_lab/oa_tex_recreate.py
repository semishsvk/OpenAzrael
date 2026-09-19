#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import mimetypes
from pathlib import Path
import time
import urllib.parse
import urllib.request
import uuid

from common import sha256_file, write_json


def _json_request(url: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data is not None else {},
        method="POST" if data is not None else "GET",
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


def _upload_image(server: str, path: Path) -> str:
    boundary = "----OpenAzrael" + uuid.uuid4().hex
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(f'Content-Disposition: form-data; name="image"; filename="{path.name}"\r\n'.encode())
    body.extend(f"Content-Type: {mime}\r\n\r\n".encode())
    body.extend(path.read_bytes())
    body.extend(f"\r\n--{boundary}--\r\n".encode())
    req = urllib.request.Request(
        server.rstrip("/") + "/upload/image",
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode("utf-8"))
    return result.get("name") or path.name


def _set_input(workflow: dict, node: str | None, key: str, value) -> None:
    if not node:
        return
    if node not in workflow:
        raise KeyError(f"workflow node not found: {node}")
    inputs = workflow[node].setdefault("inputs", {})
    if key not in inputs:
        raise KeyError(f"workflow node {node} has no input key {key!r}")
    inputs[key] = value


def _first_output_image(history: dict, prompt_id: str) -> dict:
    entry = history.get(prompt_id) or next(iter(history.values()), None)
    if not entry:
        raise RuntimeError("ComfyUI history contains no completed entry")
    for node_output in entry.get("outputs", {}).values():
        images = node_output.get("images") or []
        if images:
            return images[0]
    raise RuntimeError("ComfyUI completed without an image output")


def model_fingerprints(paths: list[Path]) -> list[dict]:
    rows = []
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        rows.append({"file": path.name, "sha256": sha256_file(path), "size": path.stat().st_size})
    return rows


def run_job(
    server: str,
    workflow_template: dict,
    source: Path,
    output: Path,
    load_image_node: str,
    prompt_node: str | None,
    prompt_key: str,
    prompt: str | None,
    seed_node: str | None,
    seed_key: str,
    seed: int | None,
    timeout: int,
) -> dict:
    uploaded_name = _upload_image(server, source)
    workflow = copy.deepcopy(workflow_template)
    _set_input(workflow, load_image_node, "image", uploaded_name)
    if prompt is not None:
        _set_input(workflow, prompt_node, prompt_key, prompt)
    if seed is not None:
        _set_input(workflow, seed_node, seed_key, seed)

    submitted = _json_request(server.rstrip("/") + "/prompt", {"prompt": workflow})
    prompt_id = submitted["prompt_id"]
    deadline = time.monotonic() + timeout
    image_info = None
    while time.monotonic() < deadline:
        history = _json_request(server.rstrip("/") + f"/history/{prompt_id}")
        try:
            image_info = _first_output_image(history, prompt_id)
            break
        except RuntimeError:
            time.sleep(1.0)
    if image_info is None:
        raise TimeoutError(f"ComfyUI job timed out after {timeout}s: {prompt_id}")

    query = urllib.parse.urlencode(
        {
            "filename": image_info["filename"],
            "subfolder": image_info.get("subfolder", ""),
            "type": image_info.get("type", "output"),
        }
    )
    with urllib.request.urlopen(server.rstrip("/") + "/view?" + query) as response:
        payload = response.read()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)

    return {
        "prompt_id": prompt_id,
        "uploaded_name": uploaded_name,
        "output_sha256": sha256_file(output),
        "submitted_workflow": workflow,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generic ComfyUI API runner for AI Recreated textures. Use an exported API-format workflow."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("--workflow", type=Path, required=True)
    parser.add_argument("--server", default="http://127.0.0.1:8188")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--job-record", type=Path, default=None)
    parser.add_argument("--load-image-node", required=True)
    parser.add_argument("--prompt-node", default=None)
    parser.add_argument("--prompt-key", default="text")
    parser.add_argument("--prompt", default=None)
    parser.add_argument("--seed-node", default=None)
    parser.add_argument("--seed-key", default="seed")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--model-file", type=Path, action="append", default=[])
    parser.add_argument("--model-label", default="unspecified")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()

    workflow = json.loads(args.workflow.read_text(encoding="utf-8"))
    result = run_job(
        args.server,
        workflow,
        args.source,
        args.output,
        args.load_image_node,
        args.prompt_node,
        args.prompt_key,
        args.prompt,
        args.seed_node,
        args.seed_key,
        args.seed,
        args.timeout,
    )
    record_path = args.job_record or args.output.with_suffix(".job.json")
    write_json(
        record_path,
        {
            "schema": "openazrael.texture_lab.ai_recreated_job.v2",
            "source_file": args.source.name,
            "source_sha256": sha256_file(args.source),
            "output_file": args.output.name,
            "workflow_template_file": args.workflow.name,
            "workflow_template_sha256": sha256_file(args.workflow),
            "model_label": args.model_label,
            "model_files": model_fingerprints(args.model_file),
            "seed": args.seed,
            "prompt": args.prompt,
            **result,
        },
    )
    print(f"PASS ai_recreated output={args.output} job={record_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
