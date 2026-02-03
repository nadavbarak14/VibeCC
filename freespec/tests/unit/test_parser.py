"""Unit tests for spec parser."""

from pathlib import Path
from textwrap import dedent

import pytest

from freespec.parser.models import Section, SpecFile
from freespec.parser.spec_parser import ParseError, SpecParser


@pytest.fixture
def parser() -> SpecParser:
    """Create a parser instance."""
    return SpecParser()


@pytest.fixture
def temp_spec(tmp_path: Path) -> Path:
    """Create a temporary spec file."""
    spec_content = dedent("""
        # student.spec

        description:
        A student is a user who can register for courses.
        Students have an email and password.

        exports:
        - Create a new student
        - Find a student by email

        tests:
        - Creating a student succeeds
        - Duplicate email fails
    """).strip()

    spec_path = tmp_path / "entities" / "student.spec"
    spec_path.parent.mkdir(parents=True)
    spec_path.write_text(spec_content)
    return spec_path


class TestSection:
    """Tests for Section dataclass."""

    def test_lines_splits_content(self) -> None:
        section = Section(name="description", content="Line 1\nLine 2\n\nLine 3")
        assert section.lines == ["Line 1", "Line 2", "Line 3"]

    def test_lines_strips_whitespace(self) -> None:
        section = Section(name="description", content="  Line 1  \n  Line 2  ")
        assert section.lines == ["Line 1", "Line 2"]

    def test_items_extracts_dash_prefixed_lines(self) -> None:
        section = Section(name="exports", content="- Item 1\n- Item 2\n- Item 3")
        assert section.items == ["Item 1", "Item 2", "Item 3"]

    def test_items_handles_no_space_after_dash(self) -> None:
        section = Section(name="exports", content="-Item 1\n-Item 2")
        assert section.items == ["Item 1", "Item 2"]

    def test_items_ignores_non_item_lines(self) -> None:
        section = Section(name="exports", content="Header\n- Item 1\nNote\n- Item 2")
        assert section.items == ["Item 1", "Item 2"]


class TestSpecFile:
    """Tests for SpecFile dataclass."""

    def test_spec_id(self) -> None:
        spec = SpecFile(
            path=Path("/project/entities/student.spec"),
            name="student",
            category="entities",
            description=Section("description", "A student"),
            exports=Section("exports", "- Create"),
            tests=Section("tests", "- Test"),
        )
        assert spec.spec_id == "entities/student"

    def test_full_content_reconstructs_spec(self) -> None:
        spec = SpecFile(
            path=Path("/project/entities/student.spec"),
            name="student",
            category="entities",
            description=Section("description", "A student"),
            exports=Section("exports", "- Create"),
            tests=Section("tests", "- Test"),
        )
        content = spec.full_content
        assert "# student.spec" in content
        assert "description:" in content
        assert "A student" in content
        assert "exports:" in content
        assert "- Create" in content
        assert "tests:" in content


class TestSpecParser:
    """Tests for SpecParser."""

    def test_parse_file_success(self, parser: SpecParser, temp_spec: Path) -> None:
        spec = parser.parse_file(temp_spec)

        assert spec.name == "student"
        assert spec.category == "entities"
        assert "register for courses" in spec.description.content
        assert len(spec.exports.items) == 2
        assert len(spec.tests.items) == 2

    def test_parse_file_not_found(self, parser: SpecParser, tmp_path: Path) -> None:
        with pytest.raises(ParseError, match="not found"):
            parser.parse_file(tmp_path / "nonexistent.spec")

    def test_parse_file_wrong_extension(self, parser: SpecParser, tmp_path: Path) -> None:
        wrong_file = tmp_path / "test.txt"
        wrong_file.write_text("content")

        with pytest.raises(ParseError, match="must have .spec extension"):
            parser.parse_file(wrong_file)

    def test_parse_file_missing_section(self, parser: SpecParser, tmp_path: Path) -> None:
        spec_path = tmp_path / "incomplete.spec"
        spec_path.write_text(dedent("""
            description:
            A thing.

            exports:
            - Do something
        """).strip())

        with pytest.raises(ParseError, match="Missing required sections.*tests"):
            parser.parse_file(spec_path)

    def test_parse_extracts_mentions(self, parser: SpecParser, tmp_path: Path) -> None:
        spec_path = tmp_path / "services" / "enrollment.spec"
        spec_path.parent.mkdir(parents=True)
        spec_path.write_text(dedent("""
            description:
            Uses @entities/student and @entities/course.
            Also depends on @services/auth.

            exports:
            - Enroll student

            tests:
            - Test enrollment
        """).strip())

        spec = parser.parse_file(spec_path)

        assert spec.mentions == ["entities/student", "entities/course", "services/auth"]

    def test_parse_mentions_deduplicates(self, parser: SpecParser, tmp_path: Path) -> None:
        spec_path = tmp_path / "test.spec"
        spec_path.write_text(dedent("""
            description:
            Uses @entities/student. Also uses @entities/student again.

            exports:
            - Export

            tests:
            - Test
        """).strip())

        spec = parser.parse_file(spec_path)

        assert spec.mentions == ["entities/student"]

    def test_parse_glob_finds_all_specs(self, parser: SpecParser, tmp_path: Path) -> None:
        # Create multiple spec files
        for name in ["student", "course"]:
            spec_path = tmp_path / "entities" / f"{name}.spec"
            spec_path.parent.mkdir(parents=True, exist_ok=True)
            spec_path.write_text(dedent(f"""
                description:
                A {name}.

                exports:
                - Create {name}

                tests:
                - Test {name}
            """).strip())

        specs = parser.parse_glob("entities/*.spec", tmp_path)

        assert len(specs) == 2
        names = {s.name for s in specs}
        assert names == {"student", "course"}

    def test_parse_glob_recursive(self, parser: SpecParser, tmp_path: Path) -> None:
        # Create specs in different directories
        for category in ["entities", "services"]:
            spec_path = tmp_path / category / "test.spec"
            spec_path.parent.mkdir(parents=True, exist_ok=True)
            spec_path.write_text(dedent("""
                description:
                A test.

                exports:
                - Export

                tests:
                - Test
            """).strip())

        specs = parser.parse_glob("**/*.spec", tmp_path)

        assert len(specs) == 2
        categories = {s.category for s in specs}
        assert categories == {"entities", "services"}
