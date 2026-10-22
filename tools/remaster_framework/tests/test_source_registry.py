from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from tools.remaster_framework.source_registry import (
    register_source,
    registry_status,
    resolve_source,
    verify_registered_source,
)


class SourceRegistryTests(unittest.TestCase):
    def _write_contract(
        self,
        root: Path,
        *,
        demo_zip: Path,
    ) -> Path:
        digest = hashlib.sha256(demo_zip.read_bytes()).hexdigest()
        payload = {
            "schema": "openazrael.source_corpora_contract",
            "version": 1,
            "project_id": "openazrael-test",
            "local_registry": {
                "env": "OPENAZRAEL_TEST_SOURCE_HOME",
                "default": str(root / "default-source-home"),
                "registry_file": "registry.json",
            },
            "corpora": {
                "demo": {
                    "corpus_id": "demo-test",
                    "kind": "demo",
                    "accepted_source_types": ["zip", "directory"],
                    "canonical_archive": {
                        "name": demo_zip.name,
                        "bytes": demo_zip.stat().st_size,
                        "sha256": digest,
                    },
                    "extracted_shape": {
                        "required_exact": ["PUZZLES.DAT", "OBJECTS.DAT"],
                        "expected_counts": [
                            {"pattern": "TEXTURES/*.AZF", "count": 2},
                            {"pattern": "TEXTURES/*.XAF", "count": 1},
                            {"pattern": "*.WAV", "count": 1},
                        ],
                    },
                },
                "retail": {
                    "corpus_id": "retail-test",
                    "kind": "retail",
                    "accepted_source_types": ["directory"],
                    "identity_mode": "FULL_LOCAL_SHA256_INVENTORY_PIN",
                    "extracted_shape": {
                        "required_exact": [
                            "PUZZLES.DAT",
                            "OBJECTS.DAT",
                            "ROOMS.DAT",
                            "CHARACTE.DAT",
                        ]
                    },
                },
            },
        }
        path = root / "contract.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def _demo_zip(self, root: Path) -> Path:
        payload = root / "demo-payload"
        game = payload / "ATDEMO"
        textures = game / "TEXTURES"
        textures.mkdir(parents=True)
        (game / "PUZZLES.DAT").write_bytes(b"puzzles")
        (game / "OBJECTS.DAT").write_bytes(b"objects")
        (game / "S001.WAV").write_bytes(b"RIFF")
        (textures / "A.AZF").write_bytes(b"a")
        (textures / "B.AZF").write_bytes(b"b")
        (textures / "R1.XAF").write_bytes(b"x")

        archive = root / "atdemo-test.zip"
        with zipfile.ZipFile(archive, "w") as handle:
            for path in sorted(game.rglob("*")):
                if path.is_file():
                    handle.write(
                        path,
                        Path("ATDEMO") / path.relative_to(game),
                    )
        return archive

    def _retail(self, root: Path) -> Path:
        retail = root / "retail"
        retail.mkdir()
        for name in (
            "PUZZLES.DAT",
            "OBJECTS.DAT",
            "ROOMS.DAT",
            "CHARACTE.DAT",
        ):
            (retail / name).write_bytes(name.encode("ascii"))
        return retail

    def test_demo_exact_archive_registers_and_materializes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = self._demo_zip(root)
            contract = self._write_contract(root, demo_zip=archive)
            home = root / "source-home"

            row = register_source(
                "demo",
                archive,
                mirror=True,
                contract_path=contract,
                home=home,
            )
            self.assertEqual(row["identity_status"], "EXACT_CANONICAL_ARCHIVE")
            self.assertTrue(row["mirrored"])

            resolved = resolve_source(
                "demo",
                contract_path=contract,
                home=home,
            )
            self.assertTrue((resolved / "PUZZLES.DAT").is_file())
            self.assertTrue((resolved / "TEXTURES/R1.XAF").is_file())

            verification = verify_registered_source(
                "demo",
                contract_path=contract,
                home=home,
            )
            self.assertEqual(verification["status"], "PASS")

    def test_demo_nested_zip_chain_materializes_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = root / "nested-payload"
            game = payload / "ATDEMO"
            textures = game / "TEXTURES"
            textures.mkdir(parents=True)
            (game / "PUZZLES.DAT").write_bytes(b"puzzles")
            (game / "OBJECTS.DAT").write_bytes(b"objects")
            (game / "S001.WAV").write_bytes(b"RIFF")
            (textures / "A.AZF").write_bytes(b"a")
            (textures / "B.AZF").write_bytes(b"b")
            (textures / "R1.XAF").write_bytes(b"x")

            resource = root / "RESOURCE.000"
            with zipfile.ZipFile(resource, "w") as handle:
                for path in sorted(game.rglob("*")):
                    if path.is_file():
                        handle.write(path, Path("ATDEMO") / path.relative_to(game))

            self_extract = root / "atdemo.exe"
            with zipfile.ZipFile(self_extract, "w") as handle:
                handle.write(resource, "RESOURCE.000")
                handle.writestr("INSTALL.BAT", "echo install")

            archive = root / "atdemo-test.zip"
            with zipfile.ZipFile(archive, "w") as handle:
                handle.write(self_extract, "atdemo.exe")

            contract = self._write_contract(root, demo_zip=archive)
            home = root / "source-home"
            register_source("demo", archive, contract_path=contract, home=home)
            resolved = resolve_source("demo", contract_path=contract, home=home)
            self.assertTrue((resolved / "PUZZLES.DAT").is_file())
            self.assertTrue((resolved / "TEXTURES/R1.XAF").is_file())

    def test_wrong_demo_archive_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = self._demo_zip(root)
            contract = self._write_contract(root, demo_zip=archive)
            archive.write_bytes(archive.read_bytes() + b"tamper")

            with self.assertRaises(ValueError):
                register_source(
                    "demo",
                    archive,
                    contract_path=contract,
                    home=root / "source-home",
                )

    def test_retail_registration_pins_full_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = self._demo_zip(root)
            contract = self._write_contract(root, demo_zip=archive)
            retail = self._retail(root)
            home = root / "source-home"

            row = register_source(
                "retail",
                retail,
                contract_path=contract,
                home=home,
            )
            self.assertEqual(row["identity_status"], "LOCAL_FULL_INVENTORY_PIN")
            self.assertEqual(
                verify_registered_source(
                    "retail",
                    contract_path=contract,
                    home=home,
                )["status"],
                "PASS",
            )

            (retail / "ROOMS.DAT").write_bytes(b"changed")
            result = verify_registered_source(
                "retail",
                contract_path=contract,
                home=home,
            )
            self.assertEqual(result["status"], "FAIL")
            self.assertIn("inventory_sha256_changed", result["failures"])

    def test_retail_shape_rejects_unrelated_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = self._demo_zip(root)
            contract = self._write_contract(root, demo_zip=archive)
            unrelated = root / "unrelated"
            unrelated.mkdir()
            (unrelated / "README.txt").write_text("not the game")

            with self.assertRaises(ValueError):
                register_source(
                    "retail",
                    unrelated,
                    contract_path=contract,
                    home=root / "source-home",
                )

    def test_status_does_not_require_expensive_rehash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = self._demo_zip(root)
            contract = self._write_contract(root, demo_zip=archive)
            home = root / "source-home"
            register_source(
                "demo",
                archive,
                contract_path=contract,
                home=home,
            )

            status = registry_status(contract_path=contract, home=home)
            self.assertEqual(status["sources"]["demo"]["status"], "AVAILABLE")
            self.assertEqual(status["sources"]["retail"]["status"], "UNREGISTERED")


if __name__ == "__main__":
    unittest.main()
