# OpenAzrael Localization Toolchain v139

## Goals

The localization layer is reusable for the demo, retail reconstruction and future
remaster projects. Languages are data, not gameplay code.

Pipeline:

`scan -> normalize -> review -> glossary -> translate -> validate -> pack -> runtime switch`

## Canonical data model

Stable semantic IDs are the runtime key. English source text is metadata and the
fallback value, never the key.

Each source row may retain:
- original source text;
- source file, SHA-256 and offset/line/JSON path;
- domain and speaker;
- room/event/trigger/animation context;
- voice/subtitle/timing metadata when recovered;
- confidence and review status;
- notes and reconstruction status.

Fragments remain research-only (`VERIFIED_FRAGMENT` or `NEEDS_RECONSTRUCTION`) and are excluded from runtime packs.\nTechnical IDs are retained as context but are not translated.

## Current evidence snapshot

See `data/localization/dialog_animation_extraction_v139.json`.

Current complete human-facing dialogue retained in the source-safe corpus:
- `dialog.demo.niamh.0001` — “Good Lord. What are you?”

Current verified fragment, excluded from runtime:
- `dialog.demo.niamh.0002.fragment` — “What do you mean? I'm”

Known dialogue/animation linkage tokens include Niamh/`Conv`,
`R6Speech`, `R6EdgarConv`, `R11TobiasConv`, `R62TobiasConv`,
`7NiamhCall`, `R7OisinCallDone`, `R7NiamhAZ`,
`ICharacterAnim`, `RANIM%d.ANM` and `con%d.dat`.

The user-provided “Oisin…” wording is a search hint only. It is not canonical
until the exact source record is recovered.

## Generic extractor

```bash
python tools/localization_tool_v139.py extract \
  --config data/localization/extraction_config_v139.json \
  --root /path/to/original/corpus \
  --out .tmp/localization/source_registry.json
```

Adapters are config-driven:
- `text_lines`
- `binary_ascii`
- `json_strings`

This keeps the Python tool reusable. Game-specific file patterns live only in
the extraction config.

## Translation workflow

Create/update a locale template:

```bash
python tools/localization_tool_v139.py template \
  --registry data/localization/source_strings_v139.json \
  --locale sk \
  --out localization/sk.json
```

Validate all built-in packs:

```bash
python tools/localization_tool_v139.py validate \
  --registry data/localization/source_strings_v139.json \
  --manifest localization/languages.json \
  --base .
```

Validation checks:
- locale-code uniqueness and BCP-47-style syntax;
- mandatory fallback locale;
- duplicate/orphan/missing source keys;
- printf and named-placeholder preservation;
- LTR/RTL declaration;
- pack schema/locale identity.

## Runtime language switching

`LocalizationManager` reads `localization/languages.json`, remembers the
selected locale in `user://localization.cfg`, and falls back per-string to
English.

`Esc` opens the options/language menu. The `OptionButton` is built directly
from the locale manifest, so adding a built-in language does not require menu
code changes. The menu applies RTL layout when a locale declares
`"direction": "rtl"`.

## External language packs

An optional external manifest may be installed at:

`user://localization/languages.json`

It uses the v139 localization-manifest schema. Relative pack paths resolve below\n`user://localization/`; traversal and absolute/resource-scheme paths are rejected.\n\nExternal packs may add languages but may not silently replace a built-in locale.\nAn incompatible external manifest is ignored fail-closed. This lets community\ntranslations ship independently from the game code.

## Translation quality workflow

For future human translations, use the same discipline as the Slovak Thief
localization workflow:

1. inventory and exact extraction;
2. deduplicate into a master source registry;
3. maintain one master glossary as the terminology authority;
4. translate complete strings systematically;
5. keep lore/wordplay/uncertain fragments as explicit candidates until reviewed;
6. preserve placeholders and technical tokens;
7. validate coverage and runtime layout;
8. test in engine before promoting a locale from experimental to verified.

English voice audio is not modified merely by selecting another text locale.
Localized subtitle/audio policy is a separate metadata layer and can be added
without changing semantic string IDs.
