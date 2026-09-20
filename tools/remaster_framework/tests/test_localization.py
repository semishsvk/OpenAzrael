from __future__ import annotations

import unittest

from tools.remaster_framework.localization import (
    build_pseudolocale,
    pseudolocalize,
    validate_pack_manifest,
    validate_string_ir,
)


class LocalizationContractTests(unittest.TestCase):
    def test_valid_string_ir_requires_stable_ids_and_english_fallback(self) -> None:
        payload = {
            "schema": "remaster.localization.string_ir",
            "version": 1,
            "strings": [
                {
                    "id": "R7_WELL_KEY_UNREACHABLE",
                    "english_fallback": "The key is out of reach.",
                    "source": {"artifact": "retail_string_evidence"},
                    "notes": [],
                }
            ],
        }
        self.assertEqual(validate_string_ir(payload), [])

    def test_duplicate_or_sentence_key_is_rejected(self) -> None:
        payload = {
            "schema": "remaster.localization.string_ir",
            "version": 1,
            "strings": [
                {"id": "This is text", "english_fallback": "A"},
                {"id": "This is text", "english_fallback": "B"},
            ],
        }
        errors = validate_string_ir(payload)
        self.assertTrue(any("invalid semantic id" in item for item in errors))
        self.assertTrue(any("duplicate semantic id" in item for item in errors))

    def test_pack_must_stay_inside_locale_namespace(self) -> None:
        valid = {
            "schema": 1,
            "package": "openazrael.localization",
            "locale": "sk",
            "language_name": "Slovenčina",
            "pack_version": "1.0.0",
            "string_revision": 1,
            "fallback": "en",
            "min_game_version": "0.1.0",
            "max_game_version": None,
            "translation_resource": (
                "res://localization/packs/sk/openazrael.translation"
            ),
            "resources": [
                "res://localization/packs/sk/fonts/fallback.tres",
            ],
        }
        self.assertEqual(validate_pack_manifest(valid), [])

        escaped = dict(valid)
        escaped["translation_resource"] = "res://scripts/player.gd"
        errors = validate_pack_manifest(escaped)
        self.assertTrue(any("namespace" in item for item in errors))
        self.assertTrue(any("core resource" in item for item in errors))

    def test_pseudolocalization_preserves_placeholders_and_expands(self) -> None:
        source = "Take {item} - %d remaining"
        pseudo = pseudolocalize(source)
        self.assertIn("{item}", pseudo)
        self.assertIn("%d", pseudo)
        self.assertGreater(len(pseudo), len(source))

    def test_pseudolocale_keeps_semantic_ids(self) -> None:
        ir = {
            "schema": "remaster.localization.string_ir",
            "version": 1,
            "strings": [
                {
                    "id": "ITEM_WELL_KEY",
                    "english_fallback": "Well Key",
                    "notes": [],
                }
            ],
        }
        pseudo = build_pseudolocale(ir)
        self.assertEqual(pseudo["strings"][0]["id"], "ITEM_WELL_KEY")
        self.assertNotEqual(pseudo["strings"][0]["text"], "Well Key")


if __name__ == "__main__":
    unittest.main()
