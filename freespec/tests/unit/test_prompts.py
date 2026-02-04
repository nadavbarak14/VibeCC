"""Unit tests for prompt builders."""

from pathlib import Path

import pytest

from freespec.generator.prompts import PromptBuilder
from freespec.parser.models import Section, SpecFile


def make_spec(name: str, category: str, mentions: list[str] | None = None) -> SpecFile:
    """Helper to create a SpecFile for testing."""
    return SpecFile(
        path=Path(f"/project/{category}/{name}.spec"),
        name=name,
        category=category,
        description=Section("description", f"A {name} with functionality"),
        exports=Section("exports", "- Create a new {name}\n- Find {name} by id"),
        tests=Section("tests", "- Creating a {name} should succeed"),
        mentions=mentions or [],
    )


class TestPromptBuilder:
    """Tests for PromptBuilder."""

    @pytest.fixture
    def builder(self, tmp_path: Path) -> PromptBuilder:
        """Create a PromptBuilder with mock docs."""
        docs_path = tmp_path / "docs"
        docs_path.mkdir()
        (docs_path / "instructions.md").write_text("# Instructions\nFreeSpec instructions")
        (docs_path / "spec-format.md").write_text("# Spec Format\nFormat reference")
        return PromptBuilder(docs_path=docs_path)

    def test_load_docs(self, builder: PromptBuilder) -> None:
        """Should load documentation files."""
        docs = builder.load_docs()

        assert "FreeSpec Instructions" in docs
        assert "instructions" in docs.lower()
        assert "format" in docs.lower()

    def test_build_header_prompt(self, builder: PromptBuilder) -> None:
        """Should build a header generation prompt."""
        spec = make_spec("student", "entities")
        output_path = Path("/output/entities/student.py")

        prompt = builder.build_header_prompt(
            spec=spec,
            language="python",
            output_path=output_path,
        )

        # Should include key elements
        assert "HEADER/INTERFACE" in prompt
        assert "PYTHON" in prompt
        assert str(output_path) in prompt
        assert "NotImplementedError" in prompt
        assert spec.name in prompt
        assert "entities" in prompt
        # Should NOT mention dependencies
        assert "dependencies" not in prompt.lower() or "do not" in prompt.lower()

    def test_build_header_prompt_completeness(self, builder: PromptBuilder) -> None:
        """Should require complete stubs with docstrings and types."""
        spec = make_spec("student", "entities")
        output_path = Path("/output/entities/student.py")

        prompt = builder.build_header_prompt(
            spec=spec,
            language="python",
            output_path=output_path,
        )

        # Should mention completeness requirements
        assert "COMPLETENESS" in prompt or "COMPLETE" in prompt
        # Should require docstrings
        assert "docstring" in prompt.lower()
        # Should require enums
        assert "enum" in prompt.lower()
        # Should require full type hints
        assert "type" in prompt.lower()

    def test_build_impl_prompt_without_headers(self, builder: PromptBuilder) -> None:
        """Should build an implementation prompt without headers."""
        spec = make_spec("student", "entities")
        output_path = Path("/output/src/entities/student.py")

        prompt = builder.build_impl_prompt(
            spec=spec,
            language="python",
            output_path=output_path,
            all_headers=None,
        )

        assert "IMPLEMENTATION" in prompt
        assert str(output_path) in prompt
        assert spec.name in prompt
        # Should not include headers section
        assert "Available Interfaces" not in prompt

    def test_build_impl_prompt_with_headers(self, builder: PromptBuilder) -> None:
        """Should include all headers in implementation prompt."""
        spec = make_spec("enrollment", "services", mentions=["entities/student"])
        output_path = Path("/output/src/services/enrollment.py")
        all_headers = {
            "entities/student": "class Student:\n    pass",
            "entities/course": "class Course:\n    pass",
        }

        prompt = builder.build_impl_prompt(
            spec=spec,
            language="python",
            output_path=output_path,
            all_headers=all_headers,
        )

        # Should include headers section
        assert "Available Interfaces" in prompt
        assert "entities/student" in prompt
        assert "entities/course" in prompt
        assert "class Student:" in prompt
        assert "class Course:" in prompt

    def test_build_test_prompt(self, builder: PromptBuilder) -> None:
        """Should build a test generation prompt."""
        spec = make_spec("student", "entities")
        output_path = Path("/output/tests/entities/test_student.py")
        impl_code = "class Student:\n    def __init__(self): pass"

        prompt = builder.build_test_prompt(
            spec=spec,
            language="python",
            output_path=output_path,
            impl_code=impl_code,
        )

        assert "test" in prompt.lower()
        assert str(output_path) in prompt
        assert spec.name in prompt
        assert impl_code in prompt
        assert "pytest" in prompt.lower() or "skip" in prompt.lower()

    def test_build_stub_prompt_deprecated(self, builder: PromptBuilder) -> None:
        """Should still work for backwards compatibility."""
        spec = make_spec("student", "entities")
        output_path = Path("/output/src/entities/student.py")

        prompt = builder.build_stub_prompt(
            spec=spec,
            language="python",
            output_path=output_path,
        )

        assert str(output_path) in prompt
        assert spec.name in prompt

    def test_format_headers_context(self, builder: PromptBuilder) -> None:
        """Should format headers as markdown code blocks."""
        headers = {
            "entities/student": "class Student: pass",
            "entities/course": "class Course: pass",
        }

        formatted = builder._format_headers_context(headers)

        assert "### entities/course" in formatted
        assert "### entities/student" in formatted
        assert "```python" in formatted
        assert "class Student: pass" in formatted

    def test_format_headers_context_empty(self, builder: PromptBuilder) -> None:
        """Should return empty string for empty/None headers."""
        assert builder._format_headers_context(None) == ""
        assert builder._format_headers_context({}) == ""

    def test_build_compile_prompt_basic(self, builder: PromptBuilder) -> None:
        """Should build a compile prompt with impl and test paths."""
        spec = make_spec("student", "entities")
        impl_path = Path("/output/entities/student.py")
        test_path = Path("/output/entities/test_student.py")

        prompt = builder.build_compile_prompt(
            spec=spec,
            language="python",
            impl_path=impl_path,
            test_path=test_path,
            header_paths={},
        )

        # Should mention in-place compilation
        assert "IN-PLACE COMPILATION" in prompt
        # Should include both file paths
        assert str(impl_path) in prompt
        assert str(test_path) in prompt
        # Should require passing tests (not skipped)
        assert "PASS" in prompt
        assert "skip" in prompt.lower()
        # Should include spec content
        assert spec.name in prompt
        # Should include critical constraints about exports
        assert "DO NOT add new" in prompt or "new public exports" in prompt.lower()
        # Should mention reading existing stub
        assert "existing stub" in prompt.lower() or "read" in prompt.lower()

    def test_build_compile_prompt_with_headers(self, builder: PromptBuilder) -> None:
        """Should include header file paths in compile prompt."""
        spec = make_spec("enrollment", "services", mentions=["entities/student"])
        impl_path = Path("/output/services/enrollment.py")
        test_path = Path("/output/services/test_enrollment.py")
        header_paths = {
            "entities/student": Path("/output/entities/student.py"),
        }

        prompt = builder.build_compile_prompt(
            spec=spec,
            language="python",
            impl_path=impl_path,
            test_path=test_path,
            header_paths=header_paths,
        )

        # Should include the header path
        assert "entities/student" in prompt
        assert "/output/entities/student.py" in prompt
        # Should instruct to READ the header files
        assert "READ" in prompt

    def test_build_compile_prompt_no_dependencies(self, builder: PromptBuilder) -> None:
        """Should not include dependencies section when there are none."""
        spec = make_spec("student", "entities")
        impl_path = Path("/output/entities/student.py")
        test_path = Path("/output/entities/test_student.py")

        prompt = builder.build_compile_prompt(
            spec=spec,
            language="python",
            impl_path=impl_path,
            test_path=test_path,
            header_paths={},
        )

        # Should not have dependencies section when empty
        assert "Dependencies (Header Files)" not in prompt

    def test_build_compile_prompt_mocking_external_only(self, builder: PromptBuilder) -> None:
        """Should instruct to mock only external dependencies."""
        spec = make_spec("enrollment", "services", mentions=["entities/student"])
        impl_path = Path("/output/services/enrollment.py")
        test_path = Path("/output/services/test_enrollment.py")
        header_paths = {"entities/student": Path("/output/entities/student.py")}

        prompt = builder.build_compile_prompt(
            spec=spec,
            language="python",
            impl_path=impl_path,
            test_path=test_path,
            header_paths=header_paths,
        )

        # Should mention mocking external dependencies only
        assert "mock" in prompt.lower()
        assert "external" in prompt.lower() or "DO NOT mock the module under test" in prompt

    def test_build_review_prompt(self, builder: PromptBuilder) -> None:
        """Should build a review prompt with spec content and file paths."""
        spec = make_spec("student", "entities")
        impl_path = Path("/output/src/entities/student.py")
        test_path = Path("/output/tests/entities/test_student.py")

        prompt = builder.build_review_prompt(
            spec=spec,
            impl_path=impl_path,
            test_path=test_path,
        )

        # Should include key elements
        assert "REVIEW" in prompt
        assert str(impl_path) in prompt
        assert str(test_path) in prompt
        assert spec.name in prompt
        # Should include response format
        assert "REVIEW_PASSED" in prompt
        assert "REVIEW_FAILED" in prompt
        # Should include spec content
        assert "exports" in prompt.lower()

    def test_build_review_prompt_includes_spec_content(self, builder: PromptBuilder) -> None:
        """Should include the full spec content in the review prompt."""
        spec = make_spec("student", "entities")
        impl_path = Path("/output/src/entities/student.py")
        test_path = Path("/output/tests/entities/test_student.py")

        prompt = builder.build_review_prompt(
            spec=spec,
            impl_path=impl_path,
            test_path=test_path,
        )

        # Should include spec content in a code block
        assert "```spec" in prompt
        assert spec.full_content in prompt

    def test_build_review_prompt_with_exports(self, builder: PromptBuilder) -> None:
        """Should include export validation when exports are provided."""
        spec = make_spec("student", "entities")
        impl_path = Path("/output/entities/student.py")
        test_path = Path("/output/entities/test_student.py")
        original_exports = {"Student", "create_student", "find_student_by_id"}

        prompt = builder.build_review_prompt(
            spec=spec,
            impl_path=impl_path,
            test_path=test_path,
            original_exports=original_exports,
        )

        # Should include export validation section
        assert "EXPORT VALIDATION" in prompt
        # Should list all exports
        assert "Student" in prompt
        assert "create_student" in prompt
        assert "find_student_by_id" in prompt
        # Should mention exports must match exactly
        assert "EXACTLY" in prompt
        # Should mention private names are allowed
        assert "_" in prompt or "private" in prompt.lower()

    def test_build_review_prompt_without_exports(self, builder: PromptBuilder) -> None:
        """Should not include export validation when no exports provided."""
        spec = make_spec("student", "entities")
        impl_path = Path("/output/entities/student.py")
        test_path = Path("/output/entities/test_student.py")

        prompt = builder.build_review_prompt(
            spec=spec,
            impl_path=impl_path,
            test_path=test_path,
            original_exports=None,
        )

        # Should NOT include export validation section
        assert "EXPORT VALIDATION" not in prompt
