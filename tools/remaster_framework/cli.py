from __future__ import annotations

import argparse
import json
from pathlib import Path

from .artifacts import verify_artifact_manifest, write_artifact_manifest
from .contracts import ToolFamily
from .corpus import discover_corpus
from .inventory import write_inventory
from .registry import ToolRegistry


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def command_list(args: argparse.Namespace) -> int:
    registry = ToolRegistry.load()
    tools = registry.all()
    if args.family:
        tools = registry.by_family(ToolFamily(args.family))

    for item in tools:
        print(
            f"{item.tool_id:34} "
            f"{item.family.value:18} "
            f"{item.maturity.value:12} "
            f"{item.entrypoint}"
        )
    return 0


def command_validate(_: argparse.Namespace) -> int:
    registry = ToolRegistry.load()
    errors = registry.validate(repo_root())
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"registry OK: {len(registry.all())} tools")
    return 0


def command_show(args: argparse.Namespace) -> int:
    item = ToolRegistry.load().get(args.tool_id)
    print(json.dumps(item.to_dict(), indent=2, sort_keys=True))
    return 0


def command_inventory(args: argparse.Namespace) -> int:
    payload = write_inventory(args.root, args.output)
    print(
        f"inventory OK: {payload['file_count']} files; "
        f"corpus={payload['corpus_sha256']}"
    )
    return 0


def command_catalog(args: argparse.Namespace) -> int:
    payload = write_artifact_manifest(
        args.root,
        args.output,
        project=args.project,
    )
    print(
        f"catalog OK: {payload['artifact_count']} artifacts; "
        f"schema={payload['schema']} v{payload['version']}"
    )
    return 0


def command_verify_catalog(args: argparse.Namespace) -> int:
    errors = verify_artifact_manifest(args.root, args.manifest)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("artifact catalog OK")
    return 0


def command_discover_corpus(args: argparse.Namespace) -> int:
    payload = discover_corpus(args.root, args.profiles)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")

    matched = [item for item in payload["profiles"] if item["status"] == "match"]
    partial = [item for item in payload["profiles"] if item["status"] == "partial"]
    if matched:
        print(
            "corpus match: "
            + ", ".join(str(item["profile_id"]) for item in matched)
        )
        return 0
    if partial:
        print(
            "corpus partial: "
            + ", ".join(str(item["profile_id"]) for item in partial)
        )
        return 2
    print("corpus profile: no match")
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openazrael-tools",
        description="Shared OpenAzrael/remaster tooling registry and safe utilities.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="List registered tools")
    list_parser.add_argument(
        "--family",
        choices=[family.value for family in ToolFamily],
    )
    list_parser.set_defaults(func=command_list)

    validate_parser = sub.add_parser(
        "validate",
        help="Validate registered tool contracts and entrypoints",
    )
    validate_parser.set_defaults(func=command_validate)

    show_parser = sub.add_parser("show", help="Show one tool contract as JSON")
    show_parser.add_argument("tool_id")
    show_parser.set_defaults(func=command_show)

    inventory_parser = sub.add_parser(
        "inventory",
        help="Create a deterministic source-safe SHA-256 inventory",
    )
    inventory_parser.add_argument("root", type=Path)
    inventory_parser.add_argument("--output", type=Path, required=True)
    inventory_parser.set_defaults(func=command_inventory)

    catalog_parser = sub.add_parser(
        "catalog",
        help="Create a deterministic artifact/IR catalog without rewriting artifacts",
    )
    catalog_parser.add_argument("root", type=Path)
    catalog_parser.add_argument("--output", type=Path, required=True)
    catalog_parser.add_argument("--project", default="OpenAzrael")
    catalog_parser.set_defaults(func=command_catalog)

    verify_parser = sub.add_parser(
        "verify-catalog",
        help="Verify catalog paths, sizes, and SHA-256 hashes against a root",
    )
    verify_parser.add_argument("root", type=Path)
    verify_parser.add_argument("--manifest", type=Path, required=True)
    verify_parser.set_defaults(func=command_verify_catalog)

    corpus_parser = sub.add_parser(
        "discover-corpus",
        help="Evaluate an immutable legacy corpus against evidence-backed profiles",
    )
    corpus_parser.add_argument("root", type=Path)
    corpus_parser.add_argument("--profiles", type=Path)
    corpus_parser.add_argument("--output", type=Path)
    corpus_parser.set_defaults(func=command_discover_corpus)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
