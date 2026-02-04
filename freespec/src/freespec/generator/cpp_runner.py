"""Test runner for C++ using Catch2 or Google Test.

Compiles and executes C++ test files to verify implementations.
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
from dataclasses import dataclass
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
    ) -> None:
        """Initialize the C++ test runner.

        Args:
            working_dir: Directory to run tests from.
            compiler: C++ compiler to use (g++ or clang++).
            std: C++ standard to use (c++11, c++14, c++17, c++20).
            timeout: Maximum seconds for compilation + test execution.
            include_paths: Additional include paths for headers.
        """
        self.working_dir = working_dir or Path.cwd()
        self.compiler = compiler
        self.std = std
        self.timeout = timeout
        self.include_paths = include_paths or []

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
            logger.info("C++ compiler: %s", result.stdout.split('\n')[0])
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
        if not test_path.exists():
            return CppRunResult(
                success=False,
                output=f"Test file not found: {test_path}",
                compile_returncode=1,
            )

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
                "-o", str(executable),
                "-I", str(self.working_dir),
            ]

            # Add custom include paths
            for inc_path in self.include_paths:
                compile_cmd.extend(["-I", str(inc_path)])

            # Add header directory
            headers_dir = self.working_dir / "generated" / "headers"
            if headers_dir.exists():
                compile_cmd.extend(["-I", str(headers_dir)])

            compile_cmd.extend(sources)

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
                return CppRunResult(
                    success=False,
                    output=f"Compilation timed out after {self.timeout // 2} seconds",
                    compile_returncode=-1,
                )
            except FileNotFoundError:
                raise CppRunnerError(
                    f"C++ compiler '{self.compiler}' not found. "
                    "Ensure g++ or clang++ is installed and in PATH."
                )

            compile_output = compile_result.stdout + compile_result.stderr

            if compile_result.returncode != 0:
                logger.warning("Compilation failed: %s", test_path)
                return CppRunResult(
                    success=False,
                    output=f"Compilation failed:\n{compile_output}",
                    compile_returncode=compile_result.returncode,
                )

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
                return CppRunResult(
                    success=False,
                    output=f"Tests timed out after {self.timeout // 2} seconds",
                    compile_returncode=0,
                    test_returncode=-1,
                )

            test_output = test_result.stdout + test_result.stderr
            full_output = f"=== Compilation ===\n{compile_output}\n=== Tests ===\n{test_output}"

            if test_result.returncode == 0:
                logger.info("Tests passed: %s", test_path)
            else:
                logger.warning("Tests failed: %s (exit code %d)", test_path, test_result.returncode)

            return CppRunResult(
                success=test_result.returncode == 0,
                output=full_output,
                compile_returncode=0,
                test_returncode=test_result.returncode,
            )
