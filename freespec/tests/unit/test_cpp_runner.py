"""Unit tests for C++ test runner."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from freespec.generator.cpp_runner import CppRunnerError, CppRunResult, CppTestRunner


class TestCppRunResult:
    """Tests for CppRunResult dataclass."""

    def test_success_result(self) -> None:
        """Should create a successful test result."""
        result = CppRunResult(
            success=True,
            output="All tests passed",
            compile_returncode=0,
            test_returncode=0,
        )

        assert result.success is True
        assert result.output == "All tests passed"
        assert result.compile_returncode == 0
        assert result.test_returncode == 0

    def test_compile_failure_result(self) -> None:
        """Should create a compile failure result."""
        result = CppRunResult(
            success=False,
            output="error: undefined reference",
            compile_returncode=1,
        )

        assert result.success is False
        assert "undefined reference" in result.output
        assert result.compile_returncode == 1
        assert result.test_returncode is None

    def test_test_failure_result(self) -> None:
        """Should create a test failure result."""
        result = CppRunResult(
            success=False,
            output="FAILED: 1 test",
            compile_returncode=0,
            test_returncode=1,
        )

        assert result.success is False
        assert result.compile_returncode == 0
        assert result.test_returncode == 1


class TestCppTestRunner:
    """Tests for CppTestRunner class."""

    def test_init_defaults(self) -> None:
        """Should initialize with default values."""
        runner = CppTestRunner()

        assert runner.working_dir == Path.cwd()
        assert runner.compiler == "g++"
        assert runner.std == "c++17"
        assert runner.timeout == 120
        assert runner.include_paths == []

    def test_init_custom_values(self, tmp_path: Path) -> None:
        """Should accept custom configuration."""
        include_path = tmp_path / "include"
        runner = CppTestRunner(
            working_dir=tmp_path,
            compiler="clang++",
            std="c++20",
            timeout=60,
            include_paths=[include_path],
        )

        assert runner.working_dir == tmp_path
        assert runner.compiler == "clang++"
        assert runner.std == "c++20"
        assert runner.timeout == 60
        assert runner.include_paths == [include_path]

    def test_run_test_file_not_found(self, tmp_path: Path) -> None:
        """Should return failure when test file doesn't exist."""
        runner = CppTestRunner(working_dir=tmp_path)
        test_path = tmp_path / "nonexistent_test.cpp"

        result = runner.run_test(test_path)

        assert result.success is False
        assert "not found" in result.output
        assert result.compile_returncode == 1

    @patch("freespec.generator.cpp_runner.subprocess.run")
    def test_check_available_success(self, mock_run: MagicMock) -> None:
        """Should return True when compiler is available."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="g++ (GCC) 11.0.0",
            stderr="",
        )

        runner = CppTestRunner()
        result = runner.check_available()

        assert result is True
        mock_run.assert_called_once()

    @patch("freespec.generator.cpp_runner.subprocess.run")
    def test_check_available_not_found(self, mock_run: MagicMock) -> None:
        """Should raise CppRunnerError when compiler not found."""
        mock_run.side_effect = FileNotFoundError("g++ not found")

        runner = CppTestRunner()

        with pytest.raises(CppRunnerError) as exc_info:
            runner.check_available()

        assert "not found" in str(exc_info.value).lower()

    @patch("freespec.generator.cpp_runner.subprocess.run")
    def test_check_available_failure(self, mock_run: MagicMock) -> None:
        """Should raise CppRunnerError when compiler check fails."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error: unrecognized option",
        )

        runner = CppTestRunner()

        with pytest.raises(CppRunnerError) as exc_info:
            runner.check_available()

        assert "failed" in str(exc_info.value).lower()

    @patch("freespec.generator.cpp_runner.tempfile.TemporaryDirectory")
    @patch("freespec.generator.cpp_runner.subprocess.run")
    def test_run_test_compile_success_test_success(
        self, mock_run: MagicMock, mock_tmpdir: MagicMock, tmp_path: Path
    ) -> None:
        """Should return success when compilation and tests pass."""
        test_file = tmp_path / "test_example.cpp"
        test_file.write_text('#include <catch.hpp>\nTEST_CASE("test") { REQUIRE(true); }')

        # Mock temp directory
        mock_tmpdir.return_value.__enter__ = MagicMock(return_value=str(tmp_path / "build"))
        mock_tmpdir.return_value.__exit__ = MagicMock(return_value=False)

        # First call is compile, second is run
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # compile
            MagicMock(returncode=0, stdout="All tests passed", stderr=""),  # test run
        ]

        runner = CppTestRunner(working_dir=tmp_path)
        result = runner.run_test(test_file)

        assert result.success is True
        assert result.compile_returncode == 0
        assert result.test_returncode == 0

    @patch("freespec.generator.cpp_runner.tempfile.TemporaryDirectory")
    @patch("freespec.generator.cpp_runner.subprocess.run")
    def test_run_test_compile_failure(
        self, mock_run: MagicMock, mock_tmpdir: MagicMock, tmp_path: Path
    ) -> None:
        """Should return failure when compilation fails."""
        test_file = tmp_path / "test_example.cpp"
        test_file.write_text("invalid c++ code {{{")

        # Mock temp directory
        mock_tmpdir.return_value.__enter__ = MagicMock(return_value=str(tmp_path / "build"))
        mock_tmpdir.return_value.__exit__ = MagicMock(return_value=False)

        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error: expected declaration",
        )

        runner = CppTestRunner(working_dir=tmp_path)
        result = runner.run_test(test_file)

        assert result.success is False
        assert result.compile_returncode == 1
        assert "COMPILATION FAILED" in result.output

    @patch("freespec.generator.cpp_runner.tempfile.TemporaryDirectory")
    @patch("freespec.generator.cpp_runner.subprocess.run")
    def test_run_test_compile_success_test_failure(
        self, mock_run: MagicMock, mock_tmpdir: MagicMock, tmp_path: Path
    ) -> None:
        """Should return failure when tests fail."""
        test_file = tmp_path / "test_example.cpp"
        test_file.write_text('#include <catch.hpp>\nTEST_CASE("test") { REQUIRE(false); }')

        # Mock temp directory
        mock_tmpdir.return_value.__enter__ = MagicMock(return_value=str(tmp_path / "build"))
        mock_tmpdir.return_value.__exit__ = MagicMock(return_value=False)

        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # compile
            MagicMock(returncode=1, stdout="FAILED: 1 test", stderr=""),  # test run
        ]

        runner = CppTestRunner(working_dir=tmp_path)
        result = runner.run_test(test_file)

        assert result.success is False
        assert result.compile_returncode == 0
        assert result.test_returncode == 1

    @patch("freespec.generator.cpp_runner.tempfile.TemporaryDirectory")
    @patch("freespec.generator.cpp_runner.subprocess.run")
    def test_run_test_compile_timeout(
        self, mock_run: MagicMock, mock_tmpdir: MagicMock, tmp_path: Path
    ) -> None:
        """Should return failure on compilation timeout."""
        import subprocess

        test_file = tmp_path / "test_slow.cpp"
        test_file.write_text("// slow compile")

        mock_tmpdir.return_value.__enter__ = MagicMock(return_value=str(tmp_path / "build"))
        mock_tmpdir.return_value.__exit__ = MagicMock(return_value=False)

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="g++", timeout=60)

        runner = CppTestRunner(working_dir=tmp_path, timeout=120)
        result = runner.run_test(test_file)

        assert result.success is False
        assert "timed out" in result.output.lower()
        assert result.compile_returncode == -1

    @patch("freespec.generator.cpp_runner.tempfile.TemporaryDirectory")
    @patch("freespec.generator.cpp_runner.subprocess.run")
    def test_run_test_compiler_not_found(
        self, mock_run: MagicMock, mock_tmpdir: MagicMock, tmp_path: Path
    ) -> None:
        """Should return failure with helpful error when compiler not found."""
        test_file = tmp_path / "test_example.cpp"
        test_file.write_text("// test")

        mock_tmpdir.return_value.__enter__ = MagicMock(return_value=str(tmp_path / "build"))
        mock_tmpdir.return_value.__exit__ = MagicMock(return_value=False)

        mock_run.side_effect = FileNotFoundError("g++ not found")

        runner = CppTestRunner(working_dir=tmp_path)
        result = runner.run_test(test_file)

        assert result.success is False
        assert "compiler not found" in result.output.lower()
        assert "g++" in result.output

    def test_init_with_log_dir(self, tmp_path: Path) -> None:
        """Should accept log_dir parameter."""
        log_dir = tmp_path / "logs"
        runner = CppTestRunner(working_dir=tmp_path, log_dir=log_dir)

        assert runner.log_dir == log_dir

    def test_init_with_out_dir(self, tmp_path: Path) -> None:
        """Should accept out_dir parameter."""
        out_dir = tmp_path / "out"
        runner = CppTestRunner(working_dir=tmp_path, out_dir=out_dir)

        assert runner.out_dir == out_dir

    def test_set_current_spec(self, tmp_path: Path) -> None:
        """Should set current spec for logging."""
        runner = CppTestRunner(working_dir=tmp_path)

        runner.set_current_spec("entities/student")

        assert runner._current_spec_id == "entities/student"

    def test_run_test_saves_log(self, tmp_path: Path) -> None:
        """Should save log file when log_dir is configured."""
        log_dir = tmp_path / "logs"
        runner = CppTestRunner(working_dir=tmp_path, log_dir=log_dir)
        runner.set_current_spec("entities/student")

        test_path = tmp_path / "test_example.cpp"
        # File doesn't exist - will fail but should still log

        result = runner.run_test(test_path)

        assert result.success is False
        assert result.log_file is not None
        assert result.log_file.exists()
        assert "cpp" in result.log_file.name
        assert "student" in result.log_file.name

        # Check log content
        log_content = result.log_file.read_text()
        assert "FREESPEC C++ COMPILATION LOG" in log_content
        assert "entities/student" in log_content
