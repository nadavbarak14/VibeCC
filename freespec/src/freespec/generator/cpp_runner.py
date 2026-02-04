"""Test runner for C++ using Catch2 or Google Test.

Compiles and executes C++ test files to verify implementations.
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("freespec.generator.cpp_runner")


class CppRunnerError(Exception):
    """Raised when C++ build/test infrastructure is broken."""


@dataclass
class CppRunResult:
    """Result of compiling and running C++ tests."""

    success: bool
    output: str
    compile_returncode: int
    test_returncode: int | None = None
    log_file: Path | None = None


class CppTestRunner:
    """Compiles and executes C++ test files.

    Supports Catch2 (header-only) and Google Test frameworks.
    Uses g++ or clang++ for compilation.
    """

    def __init__(
        self,
        working_dir: Path | None = None,
        compiler: str = "g++",
        std: str = "c++17",
        timeout: int = 120,
        include_paths: list[Path] | None = None,
        log_dir: Path | None = None,
        out_dir: Path | None = None,
    ) -> None:
        """Initialize the C++ test runner.

        Args:
            working_dir: Directory to run tests from.
            compiler: C++ compiler to use (g++ or clang++).
            std: C++ standard to use (c++11, c++14, c++17, c++20).
            timeout: Maximum seconds for compilation + test execution.
            include_paths: Additional include paths for headers.
            log_dir: Directory to save compilation logs. If None, no logs saved.
            out_dir: Output directory for generated files (default: working_dir/out).
        """
        self.working_dir = working_dir or Path.cwd()
        self.compiler = compiler
        self.std = std
        self.timeout = timeout
        self.include_paths = include_paths or []
        self.log_dir = log_dir
        self.out_dir = out_dir or (self.working_dir / "out")
        self._current_spec_id: str | None = None

    def set_current_spec(self, spec_id: str) -> None:
        """Set the current spec being compiled (for log file naming)."""
        self._current_spec_id = spec_id

    def check_available(self) -> bool:
        """Check if C++ compiler is available.

        Returns:
            True if compiler can be executed.

        Raises:
            CppRunnerError: If compiler is not available.
        """
        try:
            result = subprocess.run(
                [self.compiler, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                raise CppRunnerError(
                    f"{self.compiler} check failed: {result.stderr or result.stdout}"
                )
            logger.info("C++ compiler: %s", result.stdout.split("\n")[0])
            return True
        except FileNotFoundError:
            raise CppRunnerError(
                f"C++ compiler '{self.compiler}' not found. "
                "Ensure g++ or clang++ is installed and in PATH."
            )
        except subprocess.TimeoutExpired:
            raise CppRunnerError(f"{self.compiler} --version timed out")

    def run_test(self, test_path: Path, impl_path: Path | None = None) -> CppRunResult:
        """Compile and run a C++ test file.

        Args:
            test_path: Path to the test .cpp file.
            impl_path: Path to the implementation .cpp file (optional).

        Returns:
            CppRunResult with compilation and test results.
        """
        # Check test file exists
        if not test_path.exists():
            error_msg = self._format_missing_file_error("Test file", test_path)
            result = CppRunResult(
                success=False,
                output=error_msg,
                compile_returncode=1,
            )
            return self._save_and_return(result, test_path, None)

        # Check impl file if provided
        if impl_path and not impl_path.exists():
            error_msg = self._format_missing_file_error("Implementation file", impl_path)
            result = CppRunResult(
                success=False,
                output=error_msg,
                compile_returncode=1,
            )
            return self._save_and_return(result, test_path, None)

        logger.info("Compiling and running C++ tests: %s", test_path)

        # Create temporary directory for build artifacts
        with tempfile.TemporaryDirectory() as tmpdir:
            executable = Path(tmpdir) / "test_runner"

            # Build compile command
            sources = [str(test_path)]
            if impl_path and impl_path.exists():
                sources.append(str(impl_path))

            compile_cmd = [
                self.compiler,
                f"-std={self.std}",
                "-o",
                str(executable),
                "-I",
                str(self.working_dir),
            ]

            # Add custom include paths
            for inc_path in self.include_paths:
                compile_cmd.extend(["-I", str(inc_path)])

            # Add output directory for headers (new out/ structure)
            if self.out_dir.exists():
                compile_cmd.extend(["-I", str(self.out_dir)])

            compile_cmd.extend(sources)

            # Log the compile command
            cmd_str = " ".join(compile_cmd)
            logger.debug("Compile command: %s", cmd_str)

            # Compile
            try:
                compile_result = subprocess.run(
                    compile_cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout // 2,
                    cwd=self.working_dir,
                )
            except subprocess.TimeoutExpired:
                result = CppRunResult(
                    success=False,
                    output=self._format_timeout_error("Compilation", self.timeout // 2),
                    compile_returncode=-1,
                )
                return self._save_and_return(result, test_path, cmd_str)
            except FileNotFoundError:
                error_msg = self._format_compiler_not_found_error()
                result = CppRunResult(
                    success=False,
                    output=error_msg,
                    compile_returncode=1,
                )
                return self._save_and_return(result, test_path, cmd_str)

            compile_output = compile_result.stdout + compile_result.stderr

            if compile_result.returncode != 0:
                logger.error("Compilation FAILED: %s", test_path)
                error_msg = self._format_compile_error(
                    compile_cmd, compile_output, compile_result.returncode
                )
                result = CppRunResult(
                    success=False,
                    output=error_msg,
                    compile_returncode=compile_result.returncode,
                )
                return self._save_and_return(result, test_path, cmd_str)

            # Run tests
            try:
                test_result = subprocess.run(
                    [str(executable)],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout // 2,
                    cwd=self.working_dir,
                )
            except subprocess.TimeoutExpired:
                result = CppRunResult(
                    success=False,
                    output=self._format_timeout_error("Test execution", self.timeout // 2),
                    compile_returncode=0,
                    test_returncode=-1,
                )
                return self._save_and_return(result, test_path, cmd_str)

            test_output = test_result.stdout + test_result.stderr
            full_output = self._format_full_output(
                cmd_str, compile_output, test_output, test_result.returncode
            )

            if test_result.returncode == 0:
                logger.info("Tests passed: %s", test_path)
            else:
                logger.warning("Tests failed: %s (exit code %d)", test_path, test_result.returncode)

            result = CppRunResult(
                success=test_result.returncode == 0,
                output=full_output,
                compile_returncode=0,
                test_returncode=test_result.returncode,
            )
            return self._save_and_return(result, test_path, cmd_str)

    def _format_missing_file_error(self, file_type: str, path: Path) -> str:
        """Format a clear error message for missing files."""
        return (
            f"{'=' * 80}\n"
            f"ERROR: {file_type} not found\n"
            f"{'=' * 80}\n\n"
            f"Expected file: {path}\n\n"
            f"Possible causes:\n"
            f"  1. Header generation failed (run 'freespec headers' first)\n"
            f"  2. Implementation generation failed\n"
            f"  3. Wrong file path in spec\n\n"
            f"Check the output directory: {self.out_dir}\n"
        )

    def _format_compiler_not_found_error(self) -> str:
        """Format error when compiler is not found."""
        return (
            f"{'=' * 80}\n"
            f"ERROR: C++ compiler not found\n"
            f"{'=' * 80}\n\n"
            f"Compiler: {self.compiler}\n\n"
            f"Please install a C++ compiler:\n"
            f"  Ubuntu/Debian: sudo apt install g++\n"
            f"  macOS: xcode-select --install\n"
            f"  Or specify a different compiler with --compiler flag\n"
        )

    def _format_timeout_error(self, stage: str, timeout: int) -> str:
        """Format timeout error message."""
        return (
            f"{'=' * 80}\n"
            f"ERROR: {stage} timed out\n"
            f"{'=' * 80}\n\n"
            f"Timeout: {timeout} seconds\n\n"
            f"Possible causes:\n"
            f"  1. Infinite loop in code\n"
            f"  2. Blocking I/O operation\n"
            f"  3. Complex compilation (increase timeout)\n"
        )

    def _format_compile_error(self, cmd: list[str], output: str, returncode: int) -> str:
        """Format compilation error with helpful context."""
        cmd_str = " ".join(cmd)

        # Try to extract key error info
        missing_headers = []
        undefined_refs = []
        syntax_errors = []

        for line in output.split("\n"):
            line_lower = line.lower()
            if "no such file or directory" in line_lower:
                missing_headers.append(line.strip())
            elif "undefined reference" in line_lower:
                undefined_refs.append(line.strip())
            elif "error:" in line_lower:
                syntax_errors.append(line.strip())

        parts = [
            f"{'=' * 80}",
            "COMPILATION FAILED",
            f"{'=' * 80}",
            "",
            f"Exit code: {returncode}",
            f"Compiler: {self.compiler}",
            f"Standard: {self.std}",
            "",
            "Command:",
            f"  {cmd_str}",
            "",
        ]

        if missing_headers:
            parts.extend(
                [
                    "Missing headers/files:",
                    *[f"  - {h}" for h in missing_headers[:5]],
                    "",
                ]
            )

        if undefined_refs:
            parts.extend(
                [
                    "Undefined references (missing implementations):",
                    *[f"  - {r}" for r in undefined_refs[:5]],
                    "",
                ]
            )

        if syntax_errors:
            parts.extend(
                [
                    "Syntax/type errors:",
                    *[f"  - {e}" for e in syntax_errors[:10]],
                    "",
                ]
            )

        parts.extend(
            [
                f"{'=' * 80}",
                "Full compiler output:",
                f"{'=' * 80}",
                "",
                output,
            ]
        )

        return "\n".join(parts)

    def _format_full_output(
        self, cmd: str, compile_out: str, test_out: str, test_returncode: int
    ) -> str:
        """Format the full compilation and test output."""
        status = "PASSED" if test_returncode == 0 else "FAILED"
        return (
            f"{'=' * 80}\n"
            f"C++ BUILD AND TEST: {status}\n"
            f"{'=' * 80}\n\n"
            f"Compile command:\n  {cmd}\n\n"
            f"{'=' * 40}\n"
            f"Compilation output:\n"
            f"{'=' * 40}\n"
            f"{compile_out}\n\n"
            f"{'=' * 40}\n"
            f"Test output (exit code: {test_returncode}):\n"
            f"{'=' * 40}\n"
            f"{test_out}\n"
        )

    def _save_and_return(
        self, result: CppRunResult, test_path: Path, compile_cmd: str | None
    ) -> CppRunResult:
        """Save log file and return result."""
        if self.log_dir:
            result.log_file = self._save_log(result, test_path, compile_cmd)
        return result

    def _save_log(self, result: CppRunResult, test_path: Path, compile_cmd: str | None) -> Path:
        """Save compilation/test log to disk."""
        self.log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        spec_name = (
            self._current_spec_id.replace("/", "_") if self._current_spec_id else test_path.stem
        )
        status = "success" if result.success else "failed"
        log_filename = f"{timestamp}_cpp_{spec_name}_{status}.log"
        log_file = self.log_dir / log_filename

        with open(log_file, "w") as f:
            f.write(f"{'=' * 80}\n")
            f.write("FREESPEC C++ COMPILATION LOG\n")
            f.write(f"{'=' * 80}\n\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Spec: {self._current_spec_id or 'unknown'}\n")
            f.write(f"Test file: {test_path}\n")
            f.write(f"Compiler: {self.compiler}\n")
            f.write(f"Standard: {self.std}\n")
            f.write(f"Success: {result.success}\n")
            f.write(f"Compile return code: {result.compile_returncode}\n")
            if result.test_returncode is not None:
                f.write(f"Test return code: {result.test_returncode}\n")
            if compile_cmd:
                f.write(f"\nCompile command:\n  {compile_cmd}\n")
            f.write(f"\n{'=' * 80}\n")
            f.write("OUTPUT\n")
            f.write(f"{'=' * 80}\n\n")
            f.write(result.output)
            f.write("\n")

        logger.info("C++ log saved to: %s", log_file)
        return log_file
