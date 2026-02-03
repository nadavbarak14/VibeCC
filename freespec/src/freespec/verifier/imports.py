"""Import verification for generated code."""

from __future__ import annotations

import ast
import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("freespec.verifier")


@dataclass
class ImportError:
    """An import verification error."""

    file_path: Path
    error: str
    line: int | None = None


@dataclass
class VerificationResult:
    """Result of import verification."""

    success: bool
    errors: list[ImportError]


class ImportVerifier:
    """Verifies that generated modules can import successfully.

    Uses AST analysis for syntax checking and subprocess for actual import testing.
    """

    def verify_syntax(self, file_path: Path) -> list[ImportError]:
        """Verify Python syntax of a file using AST.

        Args:
            file_path: Path to the Python file.

        Returns:
            List of syntax errors found.
        """
        errors = []

        if not file_path.exists():
            errors.append(ImportError(file_path=file_path, error="File not found"))
            return errors

        try:
            content = file_path.read_text()
            ast.parse(content, filename=str(file_path))
        except SyntaxError as e:
            errors.append(
                ImportError(
                    file_path=file_path,
                    error=f"Syntax error: {e.msg}",
                    line=e.lineno,
                )
            )

        return errors

    def verify_import(self, file_path: Path, python_path: Path | None = None) -> list[ImportError]:
        """Verify a Python file can be imported.

        Args:
            file_path: Path to the Python file.
            python_path: Additional path to add to PYTHONPATH.

        Returns:
            List of import errors found.
        """
        errors = []

        # First check syntax
        syntax_errors = self.verify_syntax(file_path)
        if syntax_errors:
            return syntax_errors

        # Construct module name from file path
        module_name = file_path.stem

        # Run import in subprocess to avoid polluting current process
        env = dict(subprocess.os.environ)
        if python_path:
            existing = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f"{python_path}:{existing}" if existing else str(python_path)

        # Create a simple import test script
        test_code = f"""
import sys
sys.path.insert(0, '{file_path.parent}')
try:
    import {module_name}
    print('OK')
except Exception as e:
    print(f'ERROR: {{type(e).__name__}}: {{e}}')
    sys.exit(1)
"""

        try:
            result = subprocess.run(
                [sys.executable, "-c", test_code],
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip()
                errors.append(
                    ImportError(
                        file_path=file_path,
                        error=f"Import failed: {error_msg}",
                    )
                )
        except subprocess.TimeoutExpired:
            errors.append(
                ImportError(
                    file_path=file_path,
                    error="Import timed out",
                )
            )

        return errors

    def verify_all(
        self,
        files: list[Path],
        python_path: Path | None = None,
    ) -> VerificationResult:
        """Verify all generated files can be imported.

        Args:
            files: List of Python files to verify.
            python_path: Additional path for PYTHONPATH.

        Returns:
            Verification result with any errors found.
        """
        all_errors = []

        for file_path in files:
            if file_path.suffix != ".py":
                continue

            logger.debug("Verifying imports for %s", file_path)
            errors = self.verify_import(file_path, python_path)
            all_errors.extend(errors)

        return VerificationResult(
            success=len(all_errors) == 0,
            errors=all_errors,
        )

    def verify_cross_imports(
        self,
        files: list[Path],
        base_path: Path,
    ) -> VerificationResult:
        """Verify files can import each other correctly.

        Ensures that the dependency structure allows proper importing.

        Args:
            files: List of Python files to verify.
            base_path: Base path for import resolution.

        Returns:
            Verification result with any errors found.
        """
        all_errors = []

        # Create __init__.py files if missing to enable package imports
        self._ensure_init_files(files, base_path)

        # Verify each file can be imported
        result = self.verify_all(files, python_path=base_path)
        all_errors.extend(result.errors)

        return VerificationResult(
            success=len(all_errors) == 0,
            errors=all_errors,
        )

    def _ensure_init_files(self, files: list[Path], base_path: Path) -> None:
        """Create __init__.py files in directories that need them.

        Args:
            files: List of Python files.
            base_path: Base path for the package structure.
        """
        directories = set()
        for file_path in files:
            # Get all parent directories up to base_path
            current = file_path.parent
            while current != base_path and base_path in current.parents:
                directories.add(current)
                current = current.parent

        for directory in directories:
            init_file = directory / "__init__.py"
            if not init_file.exists():
                logger.debug("Creating %s", init_file)
                init_file.touch()
