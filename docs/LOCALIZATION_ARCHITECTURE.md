# OpenAzrael Localization Architecture

**Status:** APPROVED  
**Context:** `v116-context-v25`  
**Runtime implementation:** DEFERRED until after the first KG-001 Candidate 1 runtime/manual cycle.

## 1. Goal

OpenAzrael localization is a separate data layer. Gameplay, scene logic and recovered forensic evidence must not depend on a specific human-language string.

Canonical flow:

`original string evidence -> OpenAzrael String IR -> stable semantic ID -> TranslationServer -> selected language pack`

The English text is the mandatory runtime fallback. Original Azrael's Tear strings remain preserved as evidence and are not used as unstable lookup keys.

## 2. Stable semantic IDs

Runtime code and UI refer to stable IDs such as:

- `UI_NEW_GAME`
- `ITEM_WELL_KEY`
- `R1_DOOR_LOCKED`
- `R7_WELL_KEY_UNREACHABLE`
- `R8_LENS_UNDER_WATER`
- `DIALOG_R8_NIAMH_0042`

The English sentence itself must never be the canonical identifier. Editing punctuation or wording therefore does not invalidate translations.

IDs are immutable once published unless an explicit migration map is supplied.

## 3. Authoring format

Canonical translator-facing format:

```text
localization/
  template/openazrael.pot
  en/openazrael.po
  sk/openazrael.po
  cs/openazrael.po
  de/openazrael.po
  glossary/glossary.csv
```

- POT is generated from the String IR/runtime IDs.
- PO is the canonical editable translation format.
- CSV is allowed as an interchange/review format, not the runtime authority.
- Translator comments should carry room, speaker, source/evidence context and constraints where useful.

## 4. String IR

The String IR separates forensic source material from runtime localization.

A logical record may contain:

```json
{
  "id": "DIALOG_R8_NIAMH_0042",
  "original_text": "...",
  "english_fallback": "...",
  "speaker": "NIAMH",
  "room": "R8",
  "context": "dialogue",
  "voice_asset": "r8_niamh_0042.wav",
  "notes": []
}
```

Original text/evidence provenance remains immutable evidence. Translation text is replaceable presentation data.

## 5. Distribution format

Preferred release artifact:

`languages/openazrael-<locale>.pck`

Example:

```text
languages/
  openazrael-sk.pck
  openazrael-cs.pck
  openazrael-de.pck
```

Each pack contains a unique, non-core namespace, for example:

```text
localization/packs/sk/
  manifest.json
  openazrael.translation
  fonts/
  audio/
```

The runtime must mount external packs with replacement disabled, equivalent to:

`ProjectSettings.load_resource_pack(pack_path, false)`

A language pack must not replace core scripts, scenes, IR, rooms or gameplay resources.

ZIP may be supported as a development/import container, but the normal distributable runtime pack is PCK.

## 6. Manifest

Each pack has a versioned manifest, initially:

```json
{
  "schema": 1,
  "package": "openazrael.localization",
  "locale": "sk",
  "language_name": "Slovenčina",
  "pack_version": "1.0.0",
  "string_revision": 1,
  "fallback": "en",
  "min_game_version": "0.1.0",
  "max_game_version": null,
  "translation_resource": "res://localization/packs/sk/openazrael.translation"
}
```

Runtime validation rejects:
- unknown schema/package type;
- invalid locale;
- incompatible game/string revision where migration is impossible;
- paths outside the language-pack namespace;
- duplicate/ambiguous semantic IDs;
- attempts to replace core resources.

## 7. LocalizationManager

A future `LocalizationManager` autoload will:

1. discover external packs;
2. validate manifests;
3. mount accepted PCKs with replacement disabled;
4. register translation resources explicitly;
5. expose available languages to Options;
6. select saved locale, OS locale or English fallback;
7. switch locale through `TranslationServer`;
8. report missing IDs and incompatible packs;
9. expose diagnostics for test builds.

It must not own gameplay state.

## 8. Fallback policy

Fallback order:

`selected locale -> English -> explicit missing-string diagnostic`

Missing translated strings must not silently become empty UI.

English ships with the base game so the game remains usable with no external language packs installed.

## 9. Fonts, subtitles and voice

Language packs are designed to extend beyond plain strings without changing the architecture.

Optional pack payloads may later include:
- locale-specific fonts/fallback fonts;
- subtitle timing/line-break metadata;
- localized voice assets;
- localized images only where text is intrinsically baked into an image.

Gameplay events refer to semantic dialogue/subtitle IDs, not localized filenames directly.

## 10. Pseudolocalization and validation

Before adding production translations, the implementation phase should add:
- pseudolocalization;
- missing/duplicate ID validator;
- manifest validator;
- fallback test;
- long-string/overflow UI tests;
- Unicode/font coverage checks;
- deterministic pack-build tool;
- test language pack containing a small set of strings.

## 11. Versioning

Language packs and game binaries are versioned independently.

A `string_revision` changes when the published semantic-ID contract changes. Pure translation wording corrections do not require a new game build.

Removed/renamed IDs require an explicit migration/deprecation window rather than silent reuse.

## 12. KG-001 boundary

This decision does **not** change KG-001 Candidate 1.

No localization runtime code, translated gameplay text or external pack loading is added before the first Candidate 1 runtime/manual cycle unless needed to fix a blocker.

The approved implementation order after Candidate 1 is:

1. String IR + semantic ID conventions;
2. English fallback catalog;
3. POT/PO generation;
4. LocalizationManager + safe external PCK discovery;
5. validators and pseudolocalization;
6. small Slovak smoke-test pack;
7. migrate demo UI/gameplay strings;
8. expand into the full Slovak localization corpus already being prepared separately.

## 13. Repository boundary

Source-safe localization schemas, IDs, PO/POT files created for OpenAzrael, validators and pack builders may be tracked in Git.

Original commercial strings remain subject to the project's existing evidence/copyright boundary; extraction provenance and repository safety rules still apply.
