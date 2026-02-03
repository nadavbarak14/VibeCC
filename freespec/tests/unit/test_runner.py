"""Unit tests for test runner."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from freespec.generator.runner import PytestRunner, RunResult


class TestRunResult:
    """Tests for RunResult dataclass."""

    def test_success_result(self) -> None:
        """Should create a successful test result."""
        result = RunResult(success=True, output="All tests passed", returncode=0)

        assert result.success is True
        assert result.output == "All tests passed"
        assert result.returncode == 0

    def test_failure_result(self) -> None:
        """Should create a failed test result."""
        result = RunResult(success=False, output="1 test failed", returncode=1)

        assert result.success is False
        assert result.output == "1 test failed"
        assert result.returncode == 1


class TestPytestRunner:
    """Tests for PytestRunner class."""

    def test_init_defaults(self) -> None:
        """Should initialize with default values."""
        runner = PytestRunner()

        assert runner.working_dir == Path.cwd()
        assert runner.timeout == 60

    def test_init_custom_values(self, tmp_path: Path) -> None:
        """Should accept custom working directory and timeout."""
        runner = PytestRunner(working_dir=tmp_path, timeout=120)

        assert runner.working_dir == tmp_path
        assert runner.timeout == 120

    def test_run_test_file_not_found(self, tmp_path: Path) -> None:
        """Should return failure when test file doesn't exist."""
        runner = PytestRunner(working_dir=tmp_path)
        test_path = tmp_path / "nonexistent_test.py"

        result = runner.run_test(test_path)

        assert result.success is False
        assert "not found" in result.output
        assert result.returncode == 1

    @patch("freespec.generator.runner.subprocess.run")
    def test_run_test_success(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Should return success when pytest passes."""
        test_file = tmp_path / "test_example.py"
        test_file.write_text("def test_pass(): assert True")

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="1 passed",
            stderr="",
        )

        runner = PytestRunner(working_dir=tmp_path)
        result = runner.run_test(test_file)

        assert result.success is True
        assert "1 passed" in result.output
        assert result.returncode == 0
        mock_run.assert_called_once()

    @patch("freespec.generator.runner.subprocess.run")
    def test_run_test_failure(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Should return failure when pytest fails."""
        test_file = tmp_path / "test_example.py"
        test_file.write_text("def test_fail(): assert False")

        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="1 failed",
            stderr="AssertionError",
        )

        runner = PytestRunner(working_dir=tmp_path)
        result = runner.run_test(test_file)

        assert result.success is False
        assert result.returncode == 1
        assert "failed" in result.output or "AssertionError" in result.output

    @patch("freespec.generator.runner.subprocess.run")
    def test_run_test_timeout(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Should return failure on timeout."""
        import subprocess

        test_file = tmp_path / "test_slow.py"
        test_file.write_text("import time; def test_slow(): time.sleep(100)")

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="pytest", timeout=60)

        runner = PytestRunner(working_dir=tmp_path, timeout=60)
        result = runner.run_test(test_file)

        assert result.success is False
        assert "timed out" in result.output.lower()
        assert result.returncode == -1

    @patch("freespec.generator.runner.subprocess.run")
    def test_run_test_pytest_not_found(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Should return failure when pytest is not installed."""
        test_file = tmp_path / "test_example.py"
        test_file.write_text("def test_pass(): assert True")

        mock_run.side_effect = FileNotFoundError("python not found")

        runner = PytestRunner(working_dir=tmp_path)
        result = runner.run_test(test_file)

        assert result.success is False
        assert "not found" in result.output.lower()
        assert result.returncode == -1

    @patch("freespec.generator.runner.subprocess.run")
    def test_run_test_combines_stdout_stderr(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Should combine stdout and stderr in output."""
        test_file = tmp_path / "test_example.py"
        test_file.write_text("def test_pass(): pass")

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="test output",
            stderr="warnings here",
        )

        runner = PytestRunner(working_dir=tmp_path)
        result = runner.run_test(test_file)

        assert "test output" in result.output
        assert "warnings here" in result.output

    @patch("freespec.generator.runner.subprocess.run")
    def test_run_test_uses_correct_command(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Should call pytest with correct arguments."""
        test_file = tmp_path / "test_example.py"
        test_file.write_text("def test_pass(): pass")

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        runner = PytestRunner(working_dir=tmp_path, timeout=30)
        runner.run_test(test_file)

        call_args = mock_run.call_args
        assert call_args.kwargs["cwd"] == tmp_path
        assert call_args.kwargs["timeout"] == 30
        assert call_args.kwargs["capture_output"] is True
        cmd = call_args[0][0]
        assert "pytest" in cmd
        assert str(test_file) in cmd
        assert "-v" in cmd
