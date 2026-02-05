"""Build manifest for tracking rebuild state per-language.

The manifest stores hashes and metadata for each compiled spec,
enabling incremental rebuilds by detecting which specs have changed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class SpecBuildState:
    """Build state for a single spec file."""

    spec_hash: str  # SHA256 of .spec file content
    header_hash: str  # SHA256 of generated header
    impl_hash: str  # SHA256 of impl (after header overwritten)
    test_hash: str  # SHA256 of test file
    mentions: list[str]  # @mentioned dependencies
    built_at: str  # ISO timestamp of last build

    @classmethod
    def from_dict(cls, data: dict) -> SpecBuildState:
        """Create from dictionary."""
        return cls(
            spec_hash=data.get("spec_hash", ""),
            header_hash=data.get("header_hash", ""),
            impl_hash=data.get("impl_hash", ""),
            test_hash=data.get("test_hash", ""),
            mentions=data.get("mentions", []),
            built_at=data.get("built_at", ""),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class BuildManifest:
    """Per-language build manifest stored at out/{language}/.freespec_build.json."""

    version: int = 1
    language: str = ""
    specs: dict[str, SpecBuildState] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> BuildManifest | None:
        """Load manifest from file.

        Args:
            path: Path to manifest file.

        Returns:
            Loaded manifest or None if file doesn't exist or is invalid.
        """
        if not path.exists():
            return None

        try:
            with open(path) as f:
                data = json.load(f)

            manifest = cls(
                version=data.get("version", 1),
                language=data.get("language", ""),
            )

            specs_data = data.get("specs", {})
            for spec_id, spec_data in specs_data.items():
                manifest.specs[spec_id] = SpecBuildState.from_dict(spec_data)

            return manifest
        except (json.JSONDecodeError, OSError):
            return None

    def save(self, path: Path) -> None:
        """Save manifest to file.

        Args:
            path: Path to save manifest to.
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": self.version,
            "language": self.language,
            "specs": {spec_id: state.to_dict() for spec_id, state in self.specs.items()},
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def get_state(self, spec_id: str) -> SpecBuildState | None:
        """Get build state for a spec.

        Args:
            spec_id: The spec identifier.

        Returns:
            Build state or None if not found.
        """
        return self.specs.get(spec_id)

    def update_spec(self, spec_id: str, state: SpecBuildState) -> None:
        """Update or add build state for a spec.

        Args:
            spec_id: The spec identifier.
            state: The new build state.
        """
        self.specs[spec_id] = state


def compute_file_hash(path: Path) -> str:
    """Compute SHA256 hash of a file.

    Args:
        path: Path to file.

    Returns:
        Hex-encoded SHA256 hash, or empty string if file doesn't exist.
    """
    if not path.exists():
        return ""

    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of string content.

    Args:
        content: String content to hash.

    Returns:
        Hex-encoded SHA256 hash.
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def get_timestamp() -> str:
    """Get current UTC timestamp in ISO format.

    Returns:
        ISO-formatted timestamp string.
    """
    return datetime.now(timezone.utc).isoformat()
