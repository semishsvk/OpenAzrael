from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


STRING_IR_SCHEMA = "remaster.localization.string_ir"
STRING_IR_VERSION = 1
PACK_PACKAGE = "openazrael.localization"
SEMANTIC_ID_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
LOCALE_RE = re.compile(r"^[a-z]{2,3}(?:-[A-Z]{2})?$")


def validate_semantic_id(value: str) -> bool:
    return bool(SEMANTIC_ID_RE.fullmatch(value))


def validate_string_ir(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema") != STRING_IR_SCHEMA:
        errors.append("unsupported String IR schema")
    if payload.get("version") != STRING_IR_VERSION:
        errors.append("unsupported String IR version")

    rows = payload.get("strings")
    if not isinstance(rows, list):
        return errors + ["strings must be a list"]

    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"strings[{index}] must be an object")
            continue
        semantic_id = str(row.get("id", ""))
        if not validate_semantic_id(semantic_id):
            errors.append(f"strings[{index}]: invalid semantic id {semantic_id!r}")
        if semantic_id in seen:
            errors.append(f"duplicate semantic id: {semantic_id}")
        seen.add(semantic_id)

        fallback = row.get("english_fallback")
        if not isinstance(fallback, str) or not fallback.strip():
            errors.append(
                f"{semantic_id or f'strings[{index}]'}: english_fallback required"
            )

        source = row.get("source")
        if source is not None and not isinstance(source, dict):
            errors.append(f"{semantic_id}: source provenance must be an object")

        notes = row.get("notes", [])
        if not isinstance(notes, list):
            errors.append(f"{semantic_id}: notes must be a list")

    return errors


def _pack_namespace(locale: str) -> str:
    return f"res://localization/packs/{locale}/"


def _safe_pack_path(value: str, namespace: str) -> bool:
    if not value.startswith(namespace):
        return False
    relative = value[len(namespace):]
    if not relative or relative.startswith("/"):
        return False
    parts = relative.split("/")
    return all(part not in ("", ".", "..") for part in parts)


def validate_pack_manifest(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema") != 1:
        errors.append("unsupported language-pack manifest schema")
    if payload.get("package") != PACK_PACKAGE:
        errors.append("unsupported language-pack package")

    locale = str(payload.get("locale", ""))
    if not LOCALE_RE.fullmatch(locale):
        errors.append(f"invalid locale: {locale!r}")
        namespace = ""
    else:
        namespace = _pack_namespace(locale)

    fallback = str(payload.get("fallback", ""))
    if fallback != "en":
        errors.append("fallback must be en")

    revision = payload.get("string_revision")
    if not isinstance(revision, int) or revision < 1:
        errors.append("string_revision must be a positive integer")

    translation_resource = str(payload.get("translation_resource", ""))
    if namespace and not _safe_pack_path(translation_resource, namespace):
        errors.append(
            "translation_resource must remain inside the locale pack namespace"
        )

    resources = payload.get("resources", [])
    if resources is not None:
        if not isinstance(resources, list):
            errors.append("resources must be a list")
        elif namespace:
            for raw in resources:
                value = str(raw)
                if not _safe_pack_path(value, namespace):
                    errors.append(
                        f"pack resource escapes locale namespace: {value}"
                    )

    forbidden_prefixes = (
        "res://scripts/",
        "res://scenes/",
        "res://data/",
        "res://assets/rooms/",
        "res://project.godot",
    )
    for value in [translation_resource, *(resources if isinstance(resources, list) else [])]:
        path = str(value)
        if any(path.startswith(prefix) for prefix in forbidden_prefixes):
            errors.append(f"core resource replacement forbidden: {path}")

    return errors


def pseudolocalize(text: str) -> str:
    """Expand readable text while preserving common formatting placeholders."""
    placeholders: list[str] = []

    def stash(match: re.Match[str]) -> str:
        placeholders.append(match.group(0))
        return f"\uFFF0{len(placeholders) - 1}\uFFF1"

    protected = re.sub(
        r"%(?:\d+\$)?[-+#0 ]*(?:\d+|\*)?(?:\.\d+)?[diouxXeEfFgGcrs%]"
        r"|\{[A-Za-z0-9_.:-]+\}",
        stash,
        text,
    )
    mapping = str.maketrans({
        "a": "á", "A": "Á", "e": "ë", "E": "Ë",
        "i": "ï", "I": "Ï", "o": "ô", "O": "Ô",
        "u": "ü", "U": "Ü", "c": "ç", "C": "Ç",
        "n": "ñ", "N": "Ñ",
    })
    transformed = protected.translate(mapping)
    padding = "~" * max(2, len(text) // 3)
    result = f"[!! {transformed} {padding} !!]"
    for index, placeholder in enumerate(placeholders):
        result = result.replace(f"\uFFF0{index}\uFFF1", placeholder)
    return result


def build_pseudolocale(string_ir: dict[str, Any], locale: str = "qps-ploc") -> dict[str, Any]:
    errors = validate_string_ir(string_ir)
    if errors:
        raise ValueError("; ".join(errors))
    rows = []
    for row in string_ir["strings"]:
        rows.append({
            "id": row["id"],
            "text": pseudolocalize(str(row["english_fallback"])),
        })
    return {
        "schema": "remaster.localization.pseudolocale",
        "version": 1,
        "locale": locale,
        "strings": rows,
    }


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate localization String IR and external pack manifests."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    string_ir = sub.add_parser("validate-string-ir")
    string_ir.add_argument("path", type=Path)

    pack = sub.add_parser("validate-pack")
    pack.add_argument("path", type=Path)

    pseudo = sub.add_parser("pseudolocalize")
    pseudo.add_argument("string_ir", type=Path)
    pseudo.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()

    if args.command == "validate-string-ir":
        errors = validate_string_ir(_load(args.path))
    elif args.command == "validate-pack":
        errors = validate_pack_manifest(_load(args.path))
    else:
        output = build_pseudolocale(_load(args.string_ir))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(output, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("pseudolocale OK")
        return 0

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("localization validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
