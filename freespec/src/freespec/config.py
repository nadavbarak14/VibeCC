"""Configuration loading for FreeSpec projects."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""


@dataclass
class OutputConfig:
    """Output directory configuration.

    All generated files go to a single output directory that mirrors the spec structure:
    - specs/entities/student.spec → out/entities/student.py
    - specs/entities/student.spec → out/entities/test_student.py
    """

    out: str = "out/"


@dataclass
class SettingsConfig:
    """Project settings."""

    interactive: bool = True
    test_coverage: str = "high"


@dataclass
class FreeSpecConfig:
    """FreeSpec project configuration."""

    name: str
    version: str
    language: str
    specs: list[str]
    output: OutputConfig = field(default_factory=OutputConfig)
    settings: SettingsConfig = field(default_factory=SettingsConfig)
    root_path: Path = field(default_factory=Path)

    @classmethod
    def from_dict(cls, data: dict[str, Any], root_path: Path) -> FreeSpecConfig:
        """Create config from dictionary.

        Args:
            data: Configuration dictionary from YAML.
            root_path: Root directory containing the config file.

        Returns:
            Parsed configuration object.

        Raises:
            ConfigError: If required fields are missing.
        """
        required_fields = ["name", "version", "language", "specs"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise ConfigError(f"Missing required fields: {', '.join(missing)}")

        output_data = data.get("output", {})
        output = OutputConfig(
            out=output_data.get("out", "out/"),
        )

        settings_data = data.get("settings", {})
        settings = SettingsConfig(
            interactive=settings_data.get("interactive", True),
            test_coverage=settings_data.get("test_coverage", "high"),
        )

        return cls(
            name=data["name"],
            version=data["version"],
            language=data["language"],
            specs=data["specs"],
            output=output,
            settings=settings,
            root_path=root_path,
        )

    def get_output_path(self) -> Path:
        """Get absolute output path.

        Returns:
            Absolute path to the output directory.
        """
        return self.root_path / self.output.out


def load_config(config_path: Path | str) -> FreeSpecConfig:
    """Load FreeSpec configuration from a YAML file.

    Args:
        config_path: Path to freespec.yaml file.

    Returns:
        Parsed configuration object.

    Raises:
        ConfigError: If file doesn't exist or is invalid.
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise ConfigError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in {config_path}: {e}") from e

    if not isinstance(data, dict):
        raise ConfigError(f"Configuration must be a YAML mapping, got {type(data).__name__}")

    return FreeSpecConfig.from_dict(data, config_path.parent)


def find_config(start_path: Path | str | None = None) -> Path:
    """Find freespec.yaml by walking up directory tree.

    Args:
        start_path: Starting directory. Defaults to current directory.

    Returns:
        Path to freespec.yaml file.

    Raises:
        ConfigError: If no config file is found.
    """
    if start_path is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start_path)

    current = start_path.resolve()

    while current != current.parent:
        config_path = current / "freespec.yaml"
        if config_path.exists():
            return config_path
        current = current.parent

    # Check root
    config_path = current / "freespec.yaml"
    if config_path.exists():
        return config_path

    raise ConfigError(f"No freespec.yaml found in {start_path} or any parent directory")
