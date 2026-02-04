"""Unit tests for export validation."""

from pathlib import Path

import pytest

from freespec.verifier.exports import (
    extract_public_exports,
    extract_public_exports_from_file,
    validate_exports,
)


class TestExtractPublicExports:
    """Tests for extract_public_exports function."""

    def test_extract_classes(self) -> None:
        """Should extract public class names."""
        source = """
class Student:
    pass

class Course:
    pass

class _PrivateHelper:
    pass
"""
        exports = extract_public_exports(source)

        assert "Student" in exports
        assert "Course" in exports
        assert "_PrivateHelper" not in exports

    def test_extract_functions(self) -> None:
        """Should extract public function names."""
        source = """
def create_student(name: str) -> Student:
    pass

def find_by_id(id: int) -> Student:
    pass

def _internal_helper():
    pass
"""
        exports = extract_public_exports(source)

        assert "create_student" in exports
        assert "find_by_id" in exports
        assert "_internal_helper" not in exports

    def test_extract_async_functions(self) -> None:
        """Should extract public async function names."""
        source = """
async def fetch_student(id: int) -> Student:
    pass

async def _private_fetch():
    pass
"""
        exports = extract_public_exports(source)

        assert "fetch_student" in exports
        assert "_private_fetch" not in exports

    def test_extract_constants(self) -> None:
        """Should extract UPPER_CASE constants."""
        source = """
MAX_STUDENTS = 100
DEFAULT_NAME = "Unknown"
StudentType = str  # Type alias

_PRIVATE_CONSTANT = "secret"
lowercase_var = 42
"""
        exports = extract_public_exports(source)

        assert "MAX_STUDENTS" in exports
        assert "DEFAULT_NAME" in exports
        assert "StudentType" in exports
        assert "_PRIVATE_CONSTANT" not in exports
        assert "lowercase_var" not in exports

    def test_extract_type_aliases(self) -> None:
        """Should extract annotated type aliases."""
        source = """
from typing import TypeAlias

StudentId: TypeAlias = int
StudentList: TypeAlias = list[Student]
_PrivateType: TypeAlias = str
"""
        exports = extract_public_exports(source)

        assert "StudentId" in exports
        assert "StudentList" in exports
        assert "_PrivateType" not in exports

    def test_empty_source(self) -> None:
        """Should return empty set for empty source."""
        exports = extract_public_exports("")
        assert exports == set()

    def test_syntax_error(self) -> None:
        """Should return empty set for invalid Python."""
        exports = extract_public_exports("def broken(")
        assert exports == set()

    def test_complete_module(self) -> None:
        """Should extract all public exports from a realistic module."""
        source = '''
"""Student module."""

from dataclasses import dataclass
from typing import TypeAlias

StudentId: TypeAlias = int
MAX_NAME_LENGTH = 100


@dataclass
class Student:
    """A student entity."""
    id: StudentId
    name: str


def create_student(name: str) -> Student:
    """Create a new student."""
    raise NotImplementedError()


def find_by_id(id: StudentId) -> Student | None:
    """Find student by ID."""
    raise NotImplementedError()


def _validate_name(name: str) -> bool:
    """Private validation helper."""
    return len(name) <= MAX_NAME_LENGTH
'''
        exports = extract_public_exports(source)

        expected = {"StudentId", "MAX_NAME_LENGTH", "Student", "create_student", "find_by_id"}
        assert exports == expected


class TestExtractPublicExportsFromFile:
    """Tests for extract_public_exports_from_file function."""

    def test_extract_from_file(self, tmp_path: Path) -> None:
        """Should extract exports from a file."""
        file_path = tmp_path / "student.py"
        file_path.write_text("class Student: pass\ndef create(): pass")

        exports = extract_public_exports_from_file(file_path)

        assert exports == {"Student", "create"}

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Should raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            extract_public_exports_from_file(tmp_path / "missing.py")


class TestValidateExports:
    """Tests for validate_exports function."""

    def test_exports_unchanged(self, tmp_path: Path) -> None:
        """Should succeed when exports are unchanged."""
        original = "class Student: pass\ndef create(): pass"
        current_path = tmp_path / "student.py"
        current_content = (
            "class Student:\n    def __init__(self): pass\n\ndef create():\n    return Student()"
        )
        current_path.write_text(current_content)

        result = validate_exports(original, current_path)

        assert result.success is True
        assert result.added == set()
        assert result.removed == set()
        assert result.message == "Exports unchanged"

    def test_exports_added(self, tmp_path: Path) -> None:
        """Should fail when new exports are added."""
        original = "class Student: pass"
        current_path = tmp_path / "student.py"
        current_path.write_text("class Student: pass\nclass NewClass: pass")

        result = validate_exports(original, current_path)

        assert result.success is False
        assert "NewClass" in result.added
        assert result.removed == set()
        assert "Added exports" in result.message

    def test_exports_removed(self, tmp_path: Path) -> None:
        """Should fail when exports are removed."""
        original = "class Student: pass\ndef create(): pass"
        current_path = tmp_path / "student.py"
        current_path.write_text("class Student: pass")

        result = validate_exports(original, current_path)

        assert result.success is False
        assert result.added == set()
        assert "create" in result.removed
        assert "Removed exports" in result.message

    def test_exports_changed(self, tmp_path: Path) -> None:
        """Should fail when exports are both added and removed."""
        original = "class Student: pass\ndef create(): pass"
        current_path = tmp_path / "student.py"
        current_path.write_text("class Student: pass\nclass NewEntity: pass")

        result = validate_exports(original, current_path)

        assert result.success is False
        assert "NewEntity" in result.added
        assert "create" in result.removed
        assert "Added exports" in result.message
        assert "Removed exports" in result.message

    def test_private_names_allowed(self, tmp_path: Path) -> None:
        """Should allow adding private helpers."""
        original = "class Student: pass"
        current_path = tmp_path / "student.py"
        current_path.write_text("class Student: pass\ndef _helper(): pass\n_CONSTANT = 1")

        result = validate_exports(original, current_path)

        assert result.success is True
        assert result.added == set()

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Should fail when current file doesn't exist."""
        original = "class Student: pass"
        current_path = tmp_path / "missing.py"

        result = validate_exports(original, current_path)

        assert result.success is False
        assert "not found" in result.message

    def test_result_contains_all_exports(self, tmp_path: Path) -> None:
        """Should include original and current exports in result."""
        original = "class Student: pass\ndef create(): pass"
        current_path = tmp_path / "student.py"
        current_path.write_text("class Student: pass\ndef update(): pass")

        result = validate_exports(original, current_path)

        assert result.original_exports == {"Student", "create"}
        assert result.current_exports == {"Student", "update"}
