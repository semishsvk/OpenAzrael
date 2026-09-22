#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, sys

ROOT=Path(__file__).resolve().parents[1]

def load(rel):
    return json.loads((ROOT/rel).read_text(encoding="utf-8"))

def main():
    reg=load("data/localization/source_strings_v139.json")
    manifest=load("localization/languages.json")
    en=load("localization/en.json")
    sk=load("localization/sk.json")
    manager=(ROOT/"scripts/localization_manager_v139.gd").read_text(encoding="utf-8")
    menu=(ROOT/"scripts/language_menu_v139.gd").read_text(encoding="utf-8")
    hud=(ROOT/"scripts/hud.gd").read_text(encoding="utf-8")
    player=(ROOT/"scripts/player.gd").read_text(encoding="utf-8")
    main_scene=(ROOT/"main.tscn").read_text(encoding="utf-8")
    project=(ROOT/"project.godot").read_text(encoding="utf-8")
    tool=(ROOT/"tools/localization_tool_v139.py").read_text(encoding="utf-8")

    localizable=[e for e in reg.get("entries",[]) if e.get("localizable") and "FRAGMENT" not in str(e.get("status",""))]
    localizable_ids={e["id"] for e in localizable}
    en_ids=set(en.get("strings",{}))
    sk_ids=set(sk.get("strings",{}))
    exact_legacy={e["text"] for e in reg.get("entries",[]) if e.get("source")=="NIAMH.DAT"}

    checks={
      "registry_schema":reg.get("schema")=="openazrael.localization_source_registry" and reg.get("version")==139,
      "manifest_schema":manifest.get("schema")=="openazrael.localization_manifest" and manifest.get("version")==139,
      "fallback_en":manifest.get("fallback_locale")=="en" and any(x.get("code")=="en" for x in manifest.get("locales",[])),
      "multilingual":len(manifest.get("locales",[]))>=2 and {"en","sk"}.issubset({x.get("code") for x in manifest.get("locales",[])}),
      "english_complete":localizable_ids==en_ids,
      "slovak_no_orphans":sk_ids.issubset(localizable_ids),
      "fragment_not_runtime":all(e["id"] not in en_ids and e["id"] not in sk_ids for e in reg.get("entries",[]) if "FRAGMENT" in str(e.get("status",""))),
      "exact_source_policy":reg.get("policy",{}).get("guessed_dialogue_forbidden") is True,
      "known_niamh_strings": "Good Lord. What are you?" in exact_legacy and "What do you mean? I'm" in exact_legacy,
      "generic_extractors":all(x in tool for x in ["text_lines","binary_ascii","json_strings","stable_id","placeholder_mismatch"]),
      "runtime_manifest_driven":all(x in manager for x in ["MANIFEST_PATH","available_locales()","set_locale(","fallback_locale","USER_CONFIG_PATH","TranslationServer.set_locale"]),
      "external_pack_support":all(x in manager for x in ["EXTERNAL_MANIFEST_PATH","user://localization","_register_locale("]),
      "rtl_support":'Control.LAYOUT_DIRECTION_RTL' in menu,
      "runtime_fallback":'if value.is_empty() and current_locale != fallback_locale:' in manager,
      "menu_runtime_switch":all(x in menu for x in ["OptionButton","available_locales()","set_locale(","KEY_ESCAPE"]),
      "menu_in_scene":'res://scripts/language_menu_v139.gd' in main_scene and '[node name="LanguageMenu"' in main_scene,
      "autoload_registered":'LocalizationManager="*res://scripts/localization_manager_v139.gd"' in project,
      "player_no_legacy_escape_toggle":'event.keycode == KEY_ESCAPE' not in player,
      "hud_uses_localization":all(x in hud for x in ['LocalizationManager.tr_key("ui.hud.demo_complete")','LocalizationManager.tr_key("ui.hud.controls")']),
    }

    proc=subprocess.run([
      sys.executable,str(ROOT/"tools/localization_tool_v139.py"),"validate",
      "--registry",str(ROOT/"data/localization/source_strings_v139.json"),
      "--manifest",str(ROOT/"localization/languages.json"),
      "--base",str(ROOT)
    ],cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    checks["tool_self_validation"]=proc.returncode==0

    failed=[k for k,v in checks.items() if not v]
    out={
      "schema":"openazrael.localization_contract_validation",
      "version":139,
      "status":"PASS" if not failed else "FAIL",
      "localizable_source_count":len(localizable_ids),
      "locale_count":len(manifest.get("locales",[])),
      "checks":checks,
      "failed":failed,
      "tool_output":proc.stdout[-4000:],
      "runtime_status":"NOT_EXECUTED"
    }
    print(json.dumps(out,indent=2,ensure_ascii=False))
    return 0 if not failed else 1

if __name__=="__main__":
    raise SystemExit(main())
