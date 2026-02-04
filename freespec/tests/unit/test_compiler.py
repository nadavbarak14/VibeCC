"""Unit tests for independent compiler."""

from pathlib import Path
from unittest.mock import MagicMock, call

from freespec.config import FreeSpecConfig, OutputConfig, SettingsConfig
from freespec.generator.compiler import (
    MAX_REVIEW_RETRIES,
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

    def test_review_tracking_fields(self, tmp_path: Path) -> None:
        """Should track review attempts and status."""
        result = CompileResult(
            spec_id="entities/student",
            success=True,
            impl_path=tmp_path / "student.py",
            test_path=tmp_path / "test_student.py",
            review_attempts=2,
            review_passed=True,
        )

        assert result.review_attempts == 2
        assert result.review_passed is True

    def test_review_fields_default_values(self) -> None:
        """Should have default values for review fields."""
        result = CompileResult(spec_id="test", success=True)

        assert result.review_attempts == 0
        assert result.review_passed is False


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

    def test_compile_file_success_with_review(self, tmp_path: Path) -> None:
        """Should succeed when generation, tests, and review pass."""
        config = make_config(tmp_path)
        spec = make_spec("student", "entities")
        all_headers = {"entities/student": "class Student: pass"}

        # Mock LLM client - first call generates, second call reviews
        mock_client = MagicMock()
        mock_client.generate.side_effect = [
            GenerationResult(
                success=True,
                output="Generated code",
                error=None,
                session_id="test-session-123",
            ),
            GenerationResult(
                success=True,
                output="REVIEW_PASSED",
                error=None,
                session_id="test-session-123",
            ),
        ]

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
        assert result.review_passed is True
        assert result.review_attempts == 1
        # First call is compilation, second is review
        assert mock_client.generate.call_count == 2
        mock_runner.run_test.assert_called_once()

    def test_compile_file_review_failure_exhausts_retries(self, tmp_path: Path) -> None:
        """Should fail when review fails after max retries."""
        config = make_config(tmp_path)
        spec = make_spec("student", "entities")
        all_headers = {}

        # Mock LLM client - generation succeeds, review always fails
        mock_client = MagicMock()
        mock_client.generate.side_effect = [
            GenerationResult(
                success=True, output="Generated code", session_id="test-session"
            ),
        ] + [
            GenerationResult(
                success=True, output="REVIEW_FAILED\n- Missing method X", session_id="test-session"
            )
            for _ in range(MAX_REVIEW_RETRIES)
        ]

        mock_runner = MagicMock()
        mock_runner.run_test.return_value = RunResult(
            success=True, output="passed", returncode=0
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
        assert "Review failed" in result.error
        assert result.review_attempts == MAX_REVIEW_RETRIES
        assert result.review_passed is False

    def test_compile_file_test_failure_exhausts_retries(self, tmp_path: Path) -> None:
        """Should fail with test error message when tests keep failing."""
        config = make_config(tmp_path)
        spec = make_spec("student", "entities")
        all_headers = {}

        # Mock LLM client - generation succeeds, but fixes don't help
        mock_client = MagicMock()
        mock_client.generate.side_effect = [
            GenerationResult(
                success=True, output="Generated code", session_id="test-session"
            ),
        ] + [
            GenerationResult(
                success=True, output="Fixed code", session_id="test-session"
            )
            for _ in range(MAX_REVIEW_RETRIES)
        ]

        # Tests always fail
        mock_runner = MagicMock()
        mock_runner.run_test.return_value = RunResult(
            success=False, output="AssertionError: expected X", returncode=1
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
        # Error should mention tests failed, not review
        assert "Tests failed" in result.error
        # Never got to review
        assert result.review_attempts == 0
        assert result.review_passed is False

    def test_compile_file_review_passes_after_retry(self, tmp_path: Path) -> None:
        """Should succeed when review passes after initial failure."""
        config = make_config(tmp_path)
        spec = make_spec("student", "entities")
        all_headers = {}

        # Mock LLM client - generation succeeds, first review fails, second passes
        mock_client = MagicMock()
        mock_client.generate.side_effect = [
            GenerationResult(
                success=True, output="Generated code", session_id="test-session"
            ),
            GenerationResult(
                success=True, output="REVIEW_FAILED\n- Missing method", session_id="test-session"
            ),
            GenerationResult(
                success=True, output="REVIEW_PASSED", session_id="test-session"
            ),
        ]

        mock_runner = MagicMock()
        mock_runner.run_test.return_value = RunResult(
            success=True, output="passed", returncode=0
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

        assert result.success is True
        assert result.review_passed is True
        assert result.review_attempts == 2  # 2 reviews: first failed, second passed

    def test_compile_file_test_failure_retries(self, tmp_path: Path) -> None:
        """Should retry when tests fail, then succeed on review."""
        config = make_config(tmp_path)
        spec = make_spec("student", "entities")
        all_headers = {}

        # Mock LLM client - generation succeeds, then fix prompt, then review passes
        mock_client = MagicMock()
        mock_client.generate.side_effect = [
            GenerationResult(
                success=True, output="Generated code", session_id="test-session"
            ),
            GenerationResult(
                success=True, output="Fixed the issue", session_id="test-session"
            ),
            GenerationResult(
                success=True, output="REVIEW_PASSED", session_id="test-session"
            ),
        ]

        mock_runner = MagicMock()
        mock_runner.run_test.side_effect = [
            RunResult(success=False, output="tests failed", returncode=1),
            RunResult(success=True, output="passed", returncode=0),
        ]

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

        assert result.success is True
        assert result.review_passed is True
        # Only 1 review attempt (test failure doesn't count as review attempt)
        assert result.review_attempts == 1
        # 3 calls: initial, fix, review
        assert mock_client.generate.call_count == 3
        # 2 test runs: fail, then pass
        assert mock_runner.run_test.call_count == 2

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
            session_id="test-session",
        )

        compiler = IndependentCompiler(client=mock_client)
        context = CompileContext(config=config, all_headers=all_headers)

        result = compiler.compile_file(spec, context)

        assert result.success is False
        assert "Generation failed" in result.error

    def test_compile_file_uses_session_continuity(self, tmp_path: Path) -> None:
        """Should pass session_id for continuity when fixing issues."""
        config = make_config(tmp_path)
        spec = make_spec("student", "entities")
        all_headers = {}

        # Track session_id usage
        mock_client = MagicMock()
        mock_client.generate.side_effect = [
            GenerationResult(
                success=True, output="Generated code", session_id="session-abc"
            ),
            GenerationResult(
                success=True, output="REVIEW_PASSED", session_id="session-abc"
            ),
        ]

        mock_runner = MagicMock()
        mock_runner.run_test.return_value = RunResult(
            success=True, output="passed", returncode=0
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

        compiler.compile_file(spec, context)

        # First call is without session_id (new session)
        first_call = mock_client.generate.call_args_list[0]
        assert first_call[1].get("session_id") is None or "session_id" not in first_call[1]

        # Second call (review) should use the session_id from first call
        second_call = mock_client.generate.call_args_list[1]
        assert second_call[0][1] == "session-abc" or second_call[1].get("session_id") == "session-abc"

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
        mock_client.generate.side_effect = [
            GenerationResult(success=True, output="code", session_id="test-session"),
            GenerationResult(success=True, output="REVIEW_PASSED", session_id="test-session"),
        ]

        mock_builder = MagicMock()
        mock_builder.build_compile_prompt.return_value = "prompt"
        mock_builder.build_review_prompt.return_value = "review prompt"

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
        # Each spec needs generation + review
        mock_client.generate.side_effect = [
            GenerationResult(success=True, output="code", session_id="session-1"),
            GenerationResult(success=True, output="REVIEW_PASSED", session_id="session-1"),
            GenerationResult(success=True, output="code", session_id="session-2"),
            GenerationResult(success=True, output="REVIEW_PASSED", session_id="session-2"),
        ]

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

        # Generation succeeds, but tests always fail during retry loop
        mock_client = MagicMock()
        mock_client.generate.side_effect = [
            GenerationResult(success=True, output="code", session_id="session-1"),
        ] + [
            GenerationResult(success=True, output="fixed", session_id="session-1")
            for _ in range(MAX_REVIEW_RETRIES)
        ]

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
        # Should have test failure error, not review error
        assert "Tests failed" in context.results[0].error
