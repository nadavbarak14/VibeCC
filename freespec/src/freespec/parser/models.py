"""Data models for parsed spec files."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Section:
    """A section within a spec file."""

    name: str
    content: str

    @property
    def lines(self) -> list[str]:
        """Get content split into lines, excluding empty lines."""
        return [line.strip() for line in self.content.strip().split("\n") if line.strip()]

    @property
    def items(self) -> list[str]:
        """Get list items (lines starting with -)."""
        result = []
        for line in self.lines:
            if line.startswith("- "):
                result.append(line[2:])
            elif line.startswith("-"):
                result.append(line[1:].strip())
        return result


@dataclass
class SpecFile:
    """A parsed .spec file."""

    path: Path
    name: str
    category: str  # 'entities', 'services', 'api'
    description: Section
    exports: Section
    tests: Section
    mentions: list[str] = field(default_factory=list)

    @property
    def spec_id(self) -> str:
        """Get the spec identifier (category/name without extension).

        Example: 'entities/student' for entities/student.spec
        """
        return f"{self.category}/{self.name}"

    @property
    def full_content(self) -> str:
        """Get the full spec file content reconstructed."""
        parts = [
            f"# {self.name}.spec",
            "",
            "description:",
            self.description.content,
            "",
            "exports:",
            self.exports.content,
            "",
            "tests:",
            self.tests.content,
        ]
        return "\n".join(parts)


@dataclass
class DependencyGraph:
    """A graph of spec file dependencies based on @mentions."""

    specs: dict[str, SpecFile] = field(default_factory=dict)
    # Maps spec_id -> list of spec_ids it depends on
    dependencies: dict[str, list[str]] = field(default_factory=dict)
    # Maps spec_id -> list of spec_ids that depend on it
    dependents: dict[str, list[str]] = field(default_factory=dict)

    def add_spec(self, spec: SpecFile) -> None:
        """Add a spec file to the graph.

        Args:
            spec: The spec file to add.
        """
        spec_id = spec.spec_id
        self.specs[spec_id] = spec
        self.dependencies[spec_id] = []
        self.dependents.setdefault(spec_id, [])

        # Process @mentions as dependencies
        for mention in spec.mentions:
            self.dependencies[spec_id].append(mention)
            self.dependents.setdefault(mention, []).append(spec_id)

    def get_spec(self, spec_id: str) -> SpecFile | None:
        """Get a spec by its ID.

        Args:
            spec_id: The spec identifier (e.g., 'entities/student').

        Returns:
            The spec file or None if not found.
        """
        return self.specs.get(spec_id)

    def get_dependencies(self, spec_id: str) -> list[str]:
        """Get direct dependencies of a spec.

        Args:
            spec_id: The spec identifier.

        Returns:
            List of spec IDs this spec depends on.
        """
        return self.dependencies.get(spec_id, [])

    def get_dependents(self, spec_id: str) -> list[str]:
        """Get specs that depend on this spec.

        Args:
            spec_id: The spec identifier.

        Returns:
            List of spec IDs that depend on this spec.
        """
        return self.dependents.get(spec_id, [])

    def all_spec_ids(self) -> list[str]:
        """Get all spec IDs in the graph.

        Returns:
            List of all spec identifiers.
        """
        return list(self.specs.keys())
