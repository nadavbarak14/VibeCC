"""Unit tests for two-pass generators."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from freespec.config import FreeSpecConfig, OutputConfig, SettingsConfig
from freespec.generator.headers import (
    HeaderGenerationError,
    HeaderGenerator,
    load_headers,
)
from freespec.generator.impl import (
    ImplContext,
    ImplementationGenerator,
)
from freespec.generator.tests import (
    SkeletonTestGenerator,
)
from freespec.llm.claude_code import GenerationResult
from freespec.parser.models import Section, SpecFile


def make_spec(name: str, category: str, mentions: list[str] | None = None) -> SpecFile:
    """Helper to create a SpecFile for testing."""
    return SpecFile(
        path=Path(f"/project/{category}/{name}.spec"),
        name=name,
        category=category,
        description=Section("description", f"A {name} description"),
        exports=Section("exports", "- Export item"),
        tests=Section("tests", "- Test case"),
        mentions=mentions or [],
    )


def make_config(tmp_path: Path) -> FreeSpecConfig:
    """Helper to create a FreeSpecConfig for testing."""
    return FreeSpecConfig(
        name="test-project",
        version="1.0",
        language="python",
        specs=["**/*.spec"],
        output=OutputConfig(
            headers="generated/headers/",
            api="generated/api/",
            impl="generated/src/",
            tests="generated/tests/",
        ),
        settings=SettingsConfig(),
        root_path=tmp_path,
    )


class TestHeaderGenerator:
    """Tests for HeaderGenerator."""

    def test_generate_header_success(self, tmp_path: Path) -> None:
        """Should generate a header file for a spec."""
        config = make_config(tmp_path)
        spec = make_spec("student", "entities")

        mock_client = MagicMock()
        mock_client.generate.return_value = GenerationResult(
            success=True,
            output="Generated header",
            error=None,
        )

        generator = HeaderGenerator(client=mock_client)

        # Create the expected output path and write mock content
        output_path = tmp_path / "generated/headers/entities/student.py"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("# Generated header\nclass Student:\n    pass")

        header = generator.generate_header(spec, config)

        assert header.spec_id == "entities/student"
        assert header.path == output_path
        assert "Student" in header.content
        mock_client.generate.assert_called_once()

    def test_generate_header_extracts_from_output(self, tmp_path: Path) -> None:
        """Should extract code from LLM output if file not written."""
        config = make_config(tmp_path)
        spec = make_spec("student", "entities")

        mock_client = MagicMock()
        mock_client.generate.return_value = GenerationResult(
            success=True,
            output="```python\nclass Student:\n    pass\n```",
            error=None,
        )

        generator = HeaderGenerator(client=mock_client)

        # Create the directory but not the file
        output_dir = tmp_path / "generated/headers/entities"
        output_dir.mkdir(parents=True, exist_ok=True)

        header = generator.generate_header(spec, config)

        assert "class Student:" in header.content
        # File should have been created
        assert header.path.exists()

    def test_generate_header_failure(self, tmp_path: Path) -> None:
        """Should raise HeaderGenerationError on failure."""
        config = make_config(tmp_path)
        spec = make_spec("student", "entities")

        mock_client = MagicMock()
        mock_client.generate.return_value = GenerationResult(
            success=False,
            output="",
            error="LLM error",
        )

        generator = HeaderGenerator(client=mock_client)

        with pytest.raises(HeaderGenerationError, match="LLM error"):
            generator.generate_header(spec, config)

    def test_generate_all_headers(self, tmp_path: Path) -> None:
        """Should generate headers for all specs."""
        config = make_config(tmp_path)
        specs = [
            make_spec("student", "entities"),
            make_spec("course", "entities"),
        ]

        mock_client = MagicMock()
        mock_client.generate.return_value = GenerationResult(
            success=True,
            output="```python\nclass Entity:\n    pass\n```",
            error=None,
        )

        generator = HeaderGenerator(client=mock_client)
        context = generator.generate_all_headers(specs, config)

        assert len(context.generated_files) == 2
        assert "entities/student" in context.headers
        assert "entities/course" in context.headers

    def test_get_header_path_entities(self, tmp_path: Path) -> None:
        """Should generate correct path for entity specs."""
        config = make_config(tmp_path)
        spec = make_spec("student", "entities")

        generator = HeaderGenerator()
        path = generator._get_header_path(spec, config)

        assert path == tmp_path / "generated/headers/entities/student.py"

    def test_get_header_path_api(self, tmp_path: Path) -> None:
        """Should generate correct path for api specs."""
        config = make_config(tmp_path)
        spec = make_spec("auth", "api")

        generator = HeaderGenerator()
        path = generator._get_header_path(spec, config)

        assert path == tmp_path / "generated/headers/api/auth.py"


class TestImplementationGenerator:
    """Tests for ImplementationGenerator."""

    def test_generate_impl_success(self, tmp_path: Path) -> None:
        """Should generate an implementation file for a spec."""
        config = make_config(tmp_path)
        spec = make_spec("student", "entities")
        all_headers = {"entities/student": "class Student: pass"}

        mock_client = MagicMock()
        mock_client.generate.return_value = GenerationResult(
            success=True,
            output="Generated impl",
            error=None,
        )

        generator = ImplementationGenerator(client=mock_client)
        context = ImplContext(config=config, all_headers=all_headers)

        # Create the expected output path and write mock content
        output_path = tmp_path / "generated/src/entities/student.py"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("# Implementation\nclass Student:\n    pass")

        impl = generator.generate_impl(spec, context)

        assert impl.spec_id == "entities/student"
        assert impl.path == output_path
        assert spec.spec_id in context.generated_code

    def test_generate_impl_with_headers_context(self, tmp_path: Path) -> None:
        """Should pass all headers to the prompt builder."""
        config = make_config(tmp_path)
        spec = make_spec("enrollment", "services", mentions=["entities/student"])
        all_headers = {
            "entities/student": "class Student: pass",
            "entities/course": "class Course: pass",
        }

        mock_client = MagicMock()
        mock_client.generate.return_value = GenerationResult(
            success=True,
            output="```python\nclass Enrollment:\n    pass\n```",
            error=None,
        )

        mock_builder = MagicMock()
        mock_builder.build_impl_prompt.return_value = "prompt"

        generator = ImplementationGenerator(client=mock_client, prompt_builder=mock_builder)
        context = ImplContext(config=config, all_headers=all_headers)

        output_dir = tmp_path / "generated/src/services"
        output_dir.mkdir(parents=True, exist_ok=True)

        generator.generate_impl(spec, context)

        # Verify all headers were passed
        mock_builder.build_impl_prompt.assert_called_once()
        call_kwargs = mock_builder.build_impl_prompt.call_args
        assert call_kwargs.kwargs["all_headers"] == all_headers

    def test_get_impl_path_entities(self, tmp_path: Path) -> None:
        """Should generate correct path for entity implementations."""
        config = make_config(tmp_path)
        spec = make_spec("student", "entities")

        generator = ImplementationGenerator()
        path = generator._get_impl_path(spec, config)

        assert path == tmp_path / "generated/src/entities/student.py"

    def test_get_impl_path_api(self, tmp_path: Path) -> None:
        """Should generate correct path for api implementations."""
        config = make_config(tmp_path)
        spec = make_spec("auth", "api")

        generator = ImplementationGenerator()
        path = generator._get_impl_path(spec, config)

        assert path == tmp_path / "generated/api/auth.py"


class TestSkeletonTestGenerator:
    """Tests for SkeletonTestGenerator."""

    def test_generate_test_success(self, tmp_path: Path) -> None:
        """Should generate a test file for a spec."""
        config = make_config(tmp_path)
        spec = make_spec("student", "entities")
        source_code = "class Student: pass"

        mock_client = MagicMock()
        mock_client.generate.return_value = GenerationResult(
            success=True,
            output="Generated tests",
            error=None,
        )

        generator = SkeletonTestGenerator(client=mock_client)

        # Create the expected output path and write mock content
        output_path = tmp_path / "generated/tests/entities/test_student.py"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("import pytest\ndef test_student(): pass")

        test = generator.generate_test(spec, config, source_code)

        assert test is not None
        assert test.spec_id == "entities/student"
        assert test.path == output_path

    def test_generate_test_skips_no_tests(self, tmp_path: Path) -> None:
        """Should return None if spec has no test cases."""
        config = make_config(tmp_path)
        spec = SpecFile(
            path=Path("/project/entities/student.spec"),
            name="student",
            category="entities",
            description=Section("description", "A student"),
            exports=Section("exports", "- Export"),
            tests=Section("tests", ""),  # Empty tests
            mentions=[],
        )

        mock_client = MagicMock()
        generator = SkeletonTestGenerator(client=mock_client)

        result = generator.generate_test(spec, config, "code")

        assert result is None
        mock_client.generate.assert_not_called()

    def test_get_test_path(self, tmp_path: Path) -> None:
        """Should generate correct path for test files."""
        config = make_config(tmp_path)
        spec = make_spec("student", "entities")

        generator = SkeletonTestGenerator()
        path = generator._get_test_path(spec, config)

        assert path == tmp_path / "generated/tests/entities/test_student.py"


class TestLoadHeaders:
    """Tests for load_headers function."""

    def test_load_headers_empty(self, tmp_path: Path) -> None:
        """Should return empty dict when no headers exist."""
        config = make_config(tmp_path)

        headers = load_headers(config)

        assert headers == {}

    def test_load_headers_finds_files(self, tmp_path: Path) -> None:
        """Should load all header files."""
        config = make_config(tmp_path)

        # Create header files
        headers_dir = tmp_path / "generated/headers"
        (headers_dir / "entities").mkdir(parents=True)
        (headers_dir / "entities/student.py").write_text("class Student: pass")
        (headers_dir / "entities/course.py").write_text("class Course: pass")

        headers = load_headers(config)

        assert len(headers) == 2
        assert "entities/student" in headers
        assert "entities/course" in headers
        assert "class Student: pass" in headers["entities/student"]

    def test_load_headers_ignores_init(self, tmp_path: Path) -> None:
        """Should ignore __init__.py files."""
        config = make_config(tmp_path)

        # Create header files
        headers_dir = tmp_path / "generated/headers"
        (headers_dir / "entities").mkdir(parents=True)
        (headers_dir / "entities/__init__.py").write_text("")
        (headers_dir / "entities/student.py").write_text("class Student: pass")

        headers = load_headers(config)

        assert len(headers) == 1
        assert "entities/student" in headers
