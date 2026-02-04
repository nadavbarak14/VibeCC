"""Unit tests for configuration loading."""

from pathlib import Path
from textwrap import dedent

import pytest

from freespec.config import (
    ConfigError,
    find_config,
    load_config,
)


@pytest.fixture
def temp_config(tmp_path: Path) -> Path:
    """Create a temporary config file."""
    config_content = dedent("""
        name: test-project
        version: "1.0"
        language: python

        specs:
          - "**/*.spec"

        output:
          out: out/

        settings:
          interactive: false
          test_coverage: medium
    """).strip()

    config_path = tmp_path / "freespec.yaml"
    config_path.write_text(config_content)
    return config_path


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_valid_config(self, temp_config: Path) -> None:
        config = load_config(temp_config)

        assert config.name == "test-project"
        assert config.version == "1.0"
        assert config.language == "python"
        assert config.specs == ["**/*.spec"]

    def test_load_output_config(self, temp_config: Path) -> None:
        config = load_config(temp_config)

        assert config.output.out == "out/"

    def test_load_settings_config(self, temp_config: Path) -> None:
        config = load_config(temp_config)

        assert config.settings.interactive is False
        assert config.settings.test_coverage == "medium"

    def test_load_sets_root_path(self, temp_config: Path) -> None:
        config = load_config(temp_config)

        assert config.root_path == temp_config.parent

    def test_load_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigError, match="not found"):
            load_config(tmp_path / "nonexistent.yaml")

    def test_load_missing_required_fields(self, tmp_path: Path) -> None:
        config_path = tmp_path / "freespec.yaml"
        config_path.write_text("name: test\n")

        with pytest.raises(ConfigError, match="Missing required fields"):
            load_config(config_path)

    def test_load_invalid_yaml(self, tmp_path: Path) -> None:
        config_path = tmp_path / "freespec.yaml"
        config_path.write_text("invalid: yaml: content:")

        with pytest.raises(ConfigError, match="Invalid YAML"):
            load_config(config_path)

    def test_load_defaults_for_optional_fields(self, tmp_path: Path) -> None:
        config_path = tmp_path / "freespec.yaml"
        config_path.write_text(
            dedent("""
            name: minimal
            version: "1.0"
            language: python
            specs:
              - "*.spec"
        """).strip()
        )

        config = load_config(config_path)

        # Should use defaults
        assert config.output.out == "out/"
        assert config.settings.interactive is True


class TestFreeSpecConfig:
    """Tests for FreeSpecConfig."""

    def test_get_output_path(self, temp_config: Path) -> None:
        config = load_config(temp_config)

        out_path = config.get_output_path()

        assert out_path == config.root_path / "out/"


class TestFindConfig:
    """Tests for find_config function."""

    def test_find_in_current_directory(self, tmp_path: Path) -> None:
        config_path = tmp_path / "freespec.yaml"
        config_path.write_text("name: test\nversion: '1.0'\nlanguage: python\nspecs: []")

        found = find_config(tmp_path)

        assert found == config_path

    def test_find_in_parent_directory(self, tmp_path: Path) -> None:
        config_path = tmp_path / "freespec.yaml"
        config_path.write_text("name: test\nversion: '1.0'\nlanguage: python\nspecs: []")

        subdir = tmp_path / "sub" / "dir"
        subdir.mkdir(parents=True)

        found = find_config(subdir)

        assert found == config_path

    def test_find_not_found(self, tmp_path: Path) -> None:
        subdir = tmp_path / "empty"
        subdir.mkdir()

        with pytest.raises(ConfigError, match="No freespec.yaml found"):
            find_config(subdir)
