"""Parser for .spec files."""

from __future__ import annotations

import glob
import re
from pathlib import Path

from freespec.parser.models import Section, SpecFile


class ParseError(Exception):
    """Raised when a spec file cannot be parsed."""


class SpecParser:
    """Parser for FreeSpec .spec files.

    Parses spec files with three required sections: description, exports, tests.
    Extracts @mentions for dependency tracking.
    """

    SECTION_PATTERN = re.compile(r"^(description|exports|tests):$", re.MULTILINE)
    # Match @mentions but not email addresses (require @ to not be preceded by word char)
    MENTION_PATTERN = re.compile(r"(?<![a-zA-Z0-9])@([a-zA-Z][a-zA-Z0-9_/-]*)")

    def parse_file(self, path: Path | str) -> SpecFile:
        """Parse a single .spec file.

        Args:
            path: Path to the .spec file.

        Returns:
            Parsed SpecFile object.

        Raises:
            ParseError: If the file is invalid or missing required sections.
        """
        path = Path(path)

        if not path.exists():
            raise ParseError(f"Spec file not found: {path}")

        if not path.suffix == ".spec":
            raise ParseError(f"File must have .spec extension: {path}")

        content = path.read_text()
        sections = self._parse_sections(content, path)

        # Validate all required sections present
        required = {"description", "exports", "tests"}
        found = set(sections.keys())
        missing = required - found
        if missing:
            raise ParseError(f"Missing required sections in {path}: {', '.join(sorted(missing))}")

        # Extract @mentions from description
        mentions = self._extract_mentions(sections["description"].content)

        # Determine category and name from path
        name = path.stem
        category = self._determine_category(path)

        return SpecFile(
            path=path,
            name=name,
            category=category,
            description=sections["description"],
            exports=sections["exports"],
            tests=sections["tests"],
            mentions=mentions,
        )

    def parse_glob(self, pattern: str, base_path: Path | str | None = None) -> list[SpecFile]:
        """Parse all spec files matching a glob pattern.

        Args:
            pattern: Glob pattern (e.g., '**/*.spec').
            base_path: Base directory for the pattern. Defaults to current directory.

        Returns:
            List of parsed SpecFile objects.

        Raises:
            ParseError: If any spec file is invalid.
        """
        if base_path is None:
            base_path = Path.cwd()
        else:
            base_path = Path(base_path)

        # Use glob to find matching files
        full_pattern = str(base_path / pattern)
        paths = glob.glob(full_pattern, recursive=True)

        specs = []
        for path_str in sorted(paths):
            path = Path(path_str)
            specs.append(self.parse_file(path))

        return specs

    def _parse_sections(self, content: str, path: Path) -> dict[str, Section]:
        """Parse content into sections.

        Args:
            content: File content.
            path: File path for error messages.

        Returns:
            Dictionary mapping section names to Section objects.
        """
        # Find all section headers and their positions
        matches = list(self.SECTION_PATTERN.finditer(content))

        if not matches:
            raise ParseError(f"No sections found in {path}")

        sections = {}
        for i, match in enumerate(matches):
            section_name = match.group(1)

            # Get content from after this header to next header or end
            start = match.end()
            if i + 1 < len(matches):
                end = matches[i + 1].start()
            else:
                end = len(content)

            section_content = content[start:end].strip()
            sections[section_name] = Section(name=section_name, content=section_content)

        return sections

    def _extract_mentions(self, text: str) -> list[str]:
        """Extract @mentions from text.

        Args:
            text: Text to search for mentions.

        Returns:
            List of unique mention paths (without @ prefix), in order of appearance.
        """
        mentions = self.MENTION_PATTERN.findall(text)
        # Preserve order while removing duplicates
        seen = set()
        unique = []
        for mention in mentions:
            if mention not in seen:
                seen.add(mention)
                unique.append(mention)
        return unique

    def _determine_category(self, path: Path) -> str:
        """Determine the category from the file path.

        Args:
            path: Path to the spec file.

        Returns:
            Category string (e.g., 'entities', 'services', 'api').
        """
        # Walk up to find a known category directory
        parts = path.parts
        for part in reversed(parts[:-1]):  # Exclude filename
            if part in ("entities", "services", "api"):
                return part

        # Fall back to parent directory name
        return path.parent.name
