"""Test runner for independent compilation.

Executes pytest on individual test files to verify implementations.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("freespec.generator.runner")


@dataclass
class RunResult:
    """Result of running tests on a single file."""

    success: bool
    output: str
    returncode: int


class PytestRunner:
    """Executes pytest on individual test files.

    Used by the independent compiler to verify that generated
    implementations pass their tests.
    """

    def __init__(
        self,
        working_dir: Path | None = None,
        timeout: int = 60,
    ) -> None:
        """Initialize the test runner.

        Args:
            working_dir: Directory to run tests from. Defaults to current directory.
            timeout: Maximum seconds to wait for tests to complete.
        """
        self.working_dir = working_dir or Path.cwd()
        self.timeout = timeout

    def run_test(self, test_path: Path) -> RunResult:
        """Run pytest on a single test file.

        Args:
            test_path: Path to the test file to run.

        Returns:
            RunResult with success status, output, and return code.
        """
        if not test_path.exists():
            return RunResult(
                success=False,
                output=f"Test file not found: {test_path}",
                returncode=1,
            )

        logger.info("Running tests: %s", test_path)

        try:
            result = subprocess.run(
                ["python", "-m", "pytest", str(test_path), "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.working_dir,
            )

            output = result.stdout + result.stderr
            success = result.returncode == 0

            if success:
                logger.info("Tests passed: %s", test_path)
            else:
                logger.warning("Tests failed: %s (exit code %d)", test_path, result.returncode)

            return RunResult(
                success=success,
                output=output,
                returncode=result.returncode,
            )

        except subprocess.TimeoutExpired:
            logger.error("Tests timed out: %s", test_path)
            return RunResult(
                success=False,
                output=f"Tests timed out after {self.timeout} seconds",
                returncode=-1,
            )
        except FileNotFoundError:
            logger.error("pytest not found")
            return RunResult(
                success=False,
                output="pytest not found. Please install pytest.",
                returncode=-1,
            )
        except Exception as e:
            logger.error("Failed to run tests: %s", e)
            return RunResult(
                success=False,
                output=f"Failed to run tests: {e}",
                returncode=-1,
            )
