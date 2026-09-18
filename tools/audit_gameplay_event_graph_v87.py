#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_GRAPHS = {
    "R7_WATER_SWITCHBOARD_SOLVED", "R8_LENS_PLACE", "R8_OPTICAL_START",
    "R8_SECRET_DOOR_OPEN", "R8_TAKE_SHIELD",
}
ALLOWED = {"set_flag", "set_puzzle_node", "add_inventory", "remove_inventory", "play_sound"}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-only", action="store_true",
        help="Validate source-safe IR and call sites without requiring excluded commercial audio assets.")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    checks = []
    def ck(name, condition): checks.append((name, bool(condition)))

    graph = json.loads((ROOT / "data/gameplay_event_graph_v87.json").read_text(encoding="utf-8"))
    graphs = graph.get("graphs", {})
    ck("expected_graph_ids", set(graphs) == EXPECTED_GRAPHS)
    ck("hold_boundary_present", bool(graph.get("hold")))
    for graph_id, event_graph in graphs.items():
        ck(graph_id + ":actions", bool(event_graph.get("actions")))
        for index, action in enumerate(event_graph.get("actions", [])):
            op = action.get("op")
            ck(f"{graph_id}:{index}:op", op in ALLOWED)
            ck(f"{graph_id}:{index}:confidence", bool(action.get("confidence")))
            if op == "play_sound":
                asset = str(action.get("asset", ""))
                ck(f"{graph_id}:{index}:asset_name", asset.upper().endswith(".WAV") and "/" not in asset and "\\" not in asset)
                if not args.source_only:
                    ck(f"{graph_id}:{index}:asset_exists", (ROOT / "assets/audio" / asset).is_file())

    runner = (ROOT / "scripts/legacy_event_runner_v87.gd").read_text(encoding="utf-8")
    ck("runner_loads_graph", "gameplay_event_graph_v87.json" in runner)
    project = (ROOT / "project.godot").read_text(encoding="utf-8")
    ck("autoload_registered", 'LegacyEvents="*res://scripts/legacy_event_runner_v87.gd"' in project)
    call_sites = {
        "scripts/r8_bible_interaction.gd": ["R8_LENS_PLACE", "R8_OPTICAL_START", "R8_SECRET_DOOR_OPEN"],
        "scripts/r8_shield_interaction.gd": ["R8_TAKE_SHIELD"],
        "scripts/demo_state.gd": ["R7_WATER_SWITCHBOARD_SOLVED"],
    }
    for relative_path, graph_ids in call_sites.items():
        source = (ROOT / relative_path).read_text(encoding="utf-8")
        for graph_id in graph_ids:
            ck(f"{relative_path}:{graph_id}", f'LegacyEvents.run("{graph_id}")' in source)

    failed = [name for name, passed in checks if not passed]
    result = {"version": 87, "mode": "source-only" if args.source_only else "full-checkpoint",
              "checks": len(checks), "passed": len(checks)-len(failed), "failed": failed,
              "status": "PASS" if not failed else "FAIL"}
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
