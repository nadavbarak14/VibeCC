"""Unit tests for independent compiler."""

from pathlib import Path
from unittest.mock import MagicMock

from freespec.config import FreeSpecConfig, OutputConfig, SettingsConfig
from freespec.generator.compiler import (
    CompileContext,
    CompileResult,
    IndependentCompiler,
)
from freespec.generator.runner import RunResult
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


class TestCompileResult:
    """Tests for CompileResult dataclass."""

    def test_success_result(self, tmp_path: Path) -> None:
        """Should create a successful compile result."""
        result = CompileResult(
            spec_id="entities/student",
            success=True,
            impl_path=tmp_path / "student.py",
            test_path=tmp_path / "test_student.py",
        )

        assert result.success is True
        assert result.spec_id == "entities/student"
        assert result.error is None

    def test_failure_result(self, tmp_path: Path) -> None:
        """Should create a failed compile result."""
        result = CompileResult(
            spec_id="entities/student",
            success=False,
            impl_path=tmp_path / "student.py",
            test_path=tmp_path / "test_student.py",
            error="Tests failed",
        )

        assert result.success is False
        assert result.error == "Tests failed"


class TestCompileContext:
    """Tests for CompileContext dataclass."""

    def test_passed_filter(self, tmp_path: Path) -> None:
        """Should filter to only successful results."""
        config = make_config(tmp_path)
        context = CompileContext(config=config, all_headers={})
        context.results = [
            CompileResult(spec_id="a", success=True),
            CompileResult(spec_id="b", success=False),
            CompileResult(spec_id="c", success=True),
        ]

        passed = context.passed

        assert len(passed) == 2
        assert all(r.success for r in passed)

    def test_failed_filter(self, tmp_path: Path) -> None:
        """Should filter to only failed results."""
        config = make_config(tmp_path)
        context = CompileContext(config=config, all_headers={})
        context.results = [
            CompileResult(spec_id="a", success=True),
            CompileResult(spec_id="b", success=False),
            CompileResult(spec_id="c", success=False),
        ]

        failed = context.failed

        assert len(failed) == 2
        assert all(not r.success for r in failed)


class TestIndependentCompiler:
    """Tests for IndependentCompiler class."""

    def test_init_defaults(self) -> None:
        """Should initialize with default values."""
        compiler = IndependentCompiler()

        assert compiler.client is not None
        assert compiler.prompt_builder is not None

    def test_get_impl_path_entities(self, tmp_path: Path) -> None:
        """Should generate correct path for entity implementations."""
        config = make_config(tmp_path)
        spec = make_spec("student", "entities")

        compiler = IndependentCompiler()
        path = compiler._get_impl_path(spec, config)

        assert path == tmp_path / "generated/src/entities/student.py"

    def test_get_impl_path_api(self, tmp_path: Path) -> None:
        """Should generate correct path for API implementations."""
        config = make_config(tmp_path)
        spec = make_spec("auth", "api")

        compiler = IndependentCompiler()
        path = compiler._get_impl_path(spec, config)

        assert path == tmp_path / "generated/api/auth.py"

    def test_get_test_path(self, tmp_path: Path) -> None:
        """Should generate correct path for test files."""
        config = make_config(tmp_path)
        spec = make_spec("student", "entities")

        compiler = IndependentCompiler()
        path = compiler._get_test_path(spec, config)

        assert path == tmp_path / "generated/tests/entities/test_student.py"

    def test_filter_headers_for_spec_with_mentions(self) -> None:
        """Should filter headers to only @mentioned ones."""
        spec = make_spec("enrollment", "services", mentions=["entities/student"])
        all_headers = {
            "entities/student": "class Student: pass",
            "entities/course": "class Course: pass",
            "services/auth": "class Auth: pass",
        }

        compiler = IndependentCompiler()
        filtered = compiler._filter_headers_for_spec(spec, all_headers)

        assert filtered == {"entities/student": "class Student: pass"}

    def test_filter_headers_for_spec_no_mentions(self) -> None:
        """Should return empty dict when spec has no mentions."""
        spec = make_spec("student", "entities", mentions=[])
        all_headers = {"entities/course": "class Course: pass"}

        compiler = IndependentCompiler()
        filtered = compiler._filter_headers_for_spec(spec, all_headers)

        assert filtered == {}

    def test_filter_headers_for_spec_missing_mention(self) -> None:
        """Should skip mentions that don't exist in headers."""
        spec = make_spec("enrollment", "services", mentions=["entities/missing"])
        all_headers = {"entities/student": "class Student: pass"}

        compiler = IndependentCompiler()
        filtered = compiler._filter_headers_for_spec(spec, all_headers)

        assert filtered == {}

    def test_compile_file_success(self, tmp_path: Path) -> None:
        """Should succeed when generation and tests pass."""
        config = make_config(tmp_path)
        spec = make_spec("student", "entities")
        all_headers = {"entities/student": "class Student: pass"}

        # Mock LLM client
        mock_client = MagicMock()
        mock_client.generate.return_value = GenerationResult(
            success=True,
            output="Generated code",
            error=None,
        )

        # Mock test runner
        mock_runner = MagicMock()
        mock_runner.run_test.return_value = RunResult(
            success=True,
            output="1 passed",
            returncode=0,
        )

        compiler = IndependentCompiler(
            client=mock_client,
            test_runner=mock_runner,
        )
        context = CompileContext(config=config, all_headers=all_headers)

        # Create the expected output paths
        impl_path = compiler._get_impl_path(spec, config)
        test_path = compiler._get_test_path(spec, config)
        impl_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.parent.mkdir(parents=True, exist_ok=True)
        impl_path.write_text("class Student: pass")
        test_path.write_text("def test_student(): pass")

        result = compiler.compile_file(spec, context)

        assert result.success is True
        assert result.spec_id == "entities/student"
        mock_client.generate.assert_called_once()
        mock_runner.run_test.assert_called_once()

    def test_compile_file_test_failure(self, tmp_path: Path) -> None:
        """Should fail when tests fail."""
        config = make_config(tmp_path)
        spec = make_spec("student", "entities")
        all_headers = {}

        mock_client = MagicMock()
        mock_client.generate.return_value = GenerationResult(
            success=True,
            output="Generated code",
            error=None,
        )

        mock_runner = MagicMock()
        mock_runner.run_test.return_value = RunResult(
            success=False,
            output="tests failed",
            returncode=1,
        )

        compiler = IndependentCompiler(
            client=mock_client,
            test_runner=mock_runner,
        )
        context = CompileContext(config=config, all_headers=all_headers)

        impl_path = compiler._get_impl_path(spec, config)
        test_path = compiler._get_test_path(spec, config)
        impl_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.parent.mkdir(parents=True, exist_ok=True)
        impl_path.write_text("class Student: pass")
        test_path.write_text("def test_student(): pass")

        result = compiler.compile_file(spec, context)

        assert result.success is False
        assert "Tests failed" in result.error

    def test_compile_file_llm_failure(self, tmp_path: Path) -> None:
        """Should fail on LLM error."""
        config = make_config(tmp_path)
        spec = make_spec("student", "entities")
        all_headers = {}

        mock_client = MagicMock()
        mock_client.generate.return_value = GenerationResult(
            success=False,
            output="",
            error="API error",
        )

        compiler = IndependentCompiler(client=mock_client)
        context = CompileContext(config=config, all_headers=all_headers)

        result = compiler.compile_file(spec, context)

        assert result.success is False
        assert "Generation failed" in result.error

    def test_compile_file_passes_header_paths(self, tmp_path: Path) -> None:
        """Should pass header file paths for @mentioned dependencies."""
        config = make_config(tmp_path)
        spec = make_spec("enrollment", "services", mentions=["entities/student"])
        all_headers = {
            "entities/student": "class Student: pass",
            "entities/course": "class Course: pass",
        }

        # Create the header file on disk
        headers_dir = config.get_output_path("headers")
        student_header = headers_dir / "entities" / "student.py"
        student_header.parent.mkdir(parents=True, exist_ok=True)
        student_header.write_text("class Student: pass")

        mock_client = MagicMock()
        mock_client.generate.return_value = GenerationResult(
            success=True, output="code", error=None
        )

        mock_builder = MagicMock()
        mock_builder.build_compile_prompt.return_value = "prompt"

        mock_runner = MagicMock()
        mock_runner.run_test.return_value = RunResult(success=True, output="passed", returncode=0)

        compiler = IndependentCompiler(
            client=mock_client,
            prompt_builder=mock_builder,
            test_runner=mock_runner,
        )
        context = CompileContext(config=config, all_headers=all_headers)

        impl_path = compiler._get_impl_path(spec, config)
        test_path = compiler._get_test_path(spec, config)
        impl_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.parent.mkdir(parents=True, exist_ok=True)
        impl_path.write_text("code")
        test_path.write_text("test")

        compiler.compile_file(spec, context)

        # Verify header paths were passed (not content)
        call_kwargs = mock_builder.build_compile_prompt.call_args.kwargs
        assert "header_paths" in call_kwargs
        assert "entities/student" in call_kwargs["header_paths"]
        assert call_kwargs["header_paths"]["entities/student"] == student_header

    def test_compile_all_processes_all_specs(self, tmp_path: Path) -> None:
        """Should compile all specs."""
        config = make_config(tmp_path)
        specs = [
            make_spec("student", "entities"),
            make_spec("course", "entities"),
        ]
        all_headers = {}

        mock_client = MagicMock()
        mock_client.generate.return_value = GenerationResult(
            success=True, output="code", error=None
        )

        mock_runner = MagicMock()
        mock_runner.run_test.return_value = RunResult(success=True, output="passed", returncode=0)

        compiler = IndependentCompiler(
            client=mock_client,
            test_runner=mock_runner,
        )

        # Create all output directories and files
        for spec in specs:
            impl_path = compiler._get_impl_path(spec, config)
            test_path = compiler._get_test_path(spec, config)
            impl_path.parent.mkdir(parents=True, exist_ok=True)
            test_path.parent.mkdir(parents=True, exist_ok=True)
            impl_path.write_text("code")
            test_path.write_text("test")

        context = compiler.compile_all(specs, config, all_headers)

        assert len(context.results) == 2
        assert len(context.passed) == 2
        assert len(context.failed) == 0

    def test_compile_all_fail_fast(self, tmp_path: Path) -> None:
        """Should stop early with fail_fast on failure."""
        config = make_config(tmp_path)
        specs = [
            make_spec("student", "entities"),
            make_spec("course", "entities"),
        ]
        all_headers = {}

        mock_client = MagicMock()
        mock_client.generate.return_value = GenerationResult(
            success=True, output="code", error=None
        )

        mock_runner = MagicMock()
        mock_runner.run_test.return_value = RunResult(success=False, output="failed", returncode=1)

        compiler = IndependentCompiler(
            client=mock_client,
            test_runner=mock_runner,
        )

        # Create directories for first spec
        impl_path = compiler._get_impl_path(specs[0], config)
        test_path = compiler._get_test_path(specs[0], config)
        impl_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.parent.mkdir(parents=True, exist_ok=True)
        impl_path.write_text("code")
        test_path.write_text("test")

        context = compiler.compile_all(specs, config, all_headers, fail_fast=True)

        # Should only have tried the first spec
        assert len(context.results) == 1
        assert context.results[0].spec_id == "entities/student"
