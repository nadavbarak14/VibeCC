"""Unit tests for the build manifest."""

import json
from pathlib import Path

from freespec.rebuild.manifest import (
    BuildManifest,
    SpecBuildState,
    compute_content_hash,
    compute_file_hash,
    get_timestamp,
)


class TestSpecBuildState:
    """Tests for SpecBuildState."""

    def test_from_dict(self) -> None:
        data = {
            "spec_hash": "abc123",
            "header_hash": "def456",
            "impl_hash": "ghi789",
            "test_hash": "jkl012",
            "mentions": ["entities/course"],
            "built_at": "2025-01-15T10:30:00Z",
        }

        state = SpecBuildState.from_dict(data)

        assert state.spec_hash == "abc123"
        assert state.header_hash == "def456"
        assert state.impl_hash == "ghi789"
        assert state.test_hash == "jkl012"
        assert state.mentions == ["entities/course"]
        assert state.built_at == "2025-01-15T10:30:00Z"

    def test_from_dict_with_defaults(self) -> None:
        data = {}

        state = SpecBuildState.from_dict(data)

        assert state.spec_hash == ""
        assert state.header_hash == ""
        assert state.impl_hash == ""
        assert state.test_hash == ""
        assert state.mentions == []
        assert state.built_at == ""

    def test_to_dict(self) -> None:
        state = SpecBuildState(
            spec_hash="abc123",
            header_hash="def456",
            impl_hash="ghi789",
            test_hash="jkl012",
            mentions=["entities/course"],
            built_at="2025-01-15T10:30:00Z",
        )

        data = state.to_dict()

        assert data["spec_hash"] == "abc123"
        assert data["header_hash"] == "def456"
        assert data["impl_hash"] == "ghi789"
        assert data["test_hash"] == "jkl012"
        assert data["mentions"] == ["entities/course"]
        assert data["built_at"] == "2025-01-15T10:30:00Z"


class TestBuildManifest:
    """Tests for BuildManifest."""

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        manifest = BuildManifest.load(tmp_path / "nonexistent.json")

        assert manifest is None

    def test_load_invalid_json(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text("invalid json")

        manifest = BuildManifest.load(manifest_path)

        assert manifest is None

    def test_load_valid_manifest(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "manifest.json"
        data = {
            "version": 1,
            "language": "python",
            "specs": {
                "entities/student": {
                    "spec_hash": "abc123",
                    "header_hash": "def456",
                    "impl_hash": "ghi789",
                    "test_hash": "jkl012",
                    "mentions": ["entities/course"],
                    "built_at": "2025-01-15T10:30:00Z",
                }
            },
        }
        manifest_path.write_text(json.dumps(data))

        manifest = BuildManifest.load(manifest_path)

        assert manifest is not None
        assert manifest.version == 1
        assert manifest.language == "python"
        assert "entities/student" in manifest.specs
        assert manifest.specs["entities/student"].spec_hash == "abc123"

    def test_save_and_load(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "manifest.json"

        manifest = BuildManifest(version=1, language="python")
        manifest.update_spec(
            "entities/student",
            SpecBuildState(
                spec_hash="abc123",
                header_hash="def456",
                impl_hash="ghi789",
                test_hash="jkl012",
                mentions=["entities/course"],
                built_at="2025-01-15T10:30:00Z",
            ),
        )
        manifest.save(manifest_path)

        loaded = BuildManifest.load(manifest_path)

        assert loaded is not None
        assert loaded.version == 1
        assert loaded.language == "python"
        state = loaded.get_state("entities/student")
        assert state is not None
        assert state.spec_hash == "abc123"

    def test_get_state_existing(self) -> None:
        manifest = BuildManifest()
        state = SpecBuildState(
            spec_hash="abc",
            header_hash="def",
            impl_hash="ghi",
            test_hash="jkl",
            mentions=[],
            built_at="",
        )
        manifest.specs["entities/student"] = state

        result = manifest.get_state("entities/student")

        assert result is state

    def test_get_state_missing(self) -> None:
        manifest = BuildManifest()

        result = manifest.get_state("entities/student")

        assert result is None

    def test_update_spec(self) -> None:
        manifest = BuildManifest()
        state = SpecBuildState(
            spec_hash="abc",
            header_hash="def",
            impl_hash="ghi",
            test_hash="jkl",
            mentions=[],
            built_at="",
        )

        manifest.update_spec("entities/student", state)

        assert manifest.specs["entities/student"] is state

    def test_save_creates_parent_directories(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "nested" / "dir" / "manifest.json"
        manifest = BuildManifest(language="python")

        manifest.save(manifest_path)

        assert manifest_path.exists()


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_compute_file_hash(self, tmp_path: Path) -> None:
        file_path = tmp_path / "test.txt"
        file_path.write_text("hello world")

        hash1 = compute_file_hash(file_path)

        assert len(hash1) == 64  # SHA256 hex length
        assert hash1 == compute_file_hash(file_path)  # Deterministic

    def test_compute_file_hash_different_content(self, tmp_path: Path) -> None:
        file1 = tmp_path / "test1.txt"
        file2 = tmp_path / "test2.txt"
        file1.write_text("hello")
        file2.write_text("world")

        hash1 = compute_file_hash(file1)
        hash2 = compute_file_hash(file2)

        assert hash1 != hash2

    def test_compute_file_hash_nonexistent(self, tmp_path: Path) -> None:
        result = compute_file_hash(tmp_path / "nonexistent.txt")

        assert result == ""

    def test_compute_content_hash(self) -> None:
        hash1 = compute_content_hash("hello world")
        hash2 = compute_content_hash("hello world")
        hash3 = compute_content_hash("different")

        assert len(hash1) == 64
        assert hash1 == hash2
        assert hash1 != hash3

    def test_get_timestamp(self) -> None:
        ts = get_timestamp()

        assert "T" in ts  # ISO format
        assert "+" in ts or "Z" in ts  # Has timezone
