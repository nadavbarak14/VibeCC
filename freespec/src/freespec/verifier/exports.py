"""Export validation for generated code.

Ensures that implementations don't add or remove public exports
compared to the original stub/header file.
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("freespec.verifier.exports")


@dataclass
class ValidationResult:
    """Result of export validation."""

    success: bool
    original_exports: set[str]
    current_exports: set[str]
    added: set[str]
    removed: set[str]
    message: str


def extract_public_exports(source: str) -> set[str]:
    """Extract public exports from Python source code.

    Public exports are top-level definitions that don't start with underscore:
    - Classes
    - Functions
    - Constants (UPPER_CASE variables)
    - Type aliases and TypedDicts

    Args:
        source: Python source code as a string.

    Returns:
        Set of public export names.
    """
    exports: set[str] = set()

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        logger.warning("Failed to parse source: %s", e)
        return exports

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            if not node.name.startswith("_"):
                exports.add(node.name)

        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if not node.name.startswith("_"):
                exports.add(node.name)

        elif isinstance(node, ast.Assign):
            # Handle CONSTANTS and type aliases
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name = target.id
                    if not name.startswith("_"):
                        # Include UPPER_CASE constants
                        if name.isupper() or name[0].isupper():
                            exports.add(name)

        elif isinstance(node, ast.AnnAssign):
            # Handle annotated assignments like: MyType: TypeAlias = ...
            if isinstance(node.target, ast.Name):
                name = node.target.id
                if not name.startswith("_"):
                    # Include type aliases and typed constants
                    if name[0].isupper():
                        exports.add(name)

    return exports


def extract_public_exports_from_file(file_path: Path) -> set[str]:
    """Extract public exports from a Python file.

    Args:
        file_path: Path to the Python file.

    Returns:
        Set of public export names.

    Raises:
        FileNotFoundError: If file doesn't exist.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    source = file_path.read_text()
    return extract_public_exports(source)


def validate_exports(original_content: str, current_path: Path) -> ValidationResult:
    """Validate that exports haven't changed after implementation.

    Compares the original stub's exports with the current implementation's exports.
    The implementation must not add or remove any public exports.

    Args:
        original_content: The original stub source code.
        current_path: Path to the current implementation file.

    Returns:
        ValidationResult with comparison details.
    """
    original_exports = extract_public_exports(original_content)

    if not current_path.exists():
        return ValidationResult(
            success=False,
            original_exports=original_exports,
            current_exports=set(),
            added=set(),
            removed=original_exports,
            message=f"Implementation file not found: {current_path}",
        )

    current_content = current_path.read_text()
    current_exports = extract_public_exports(current_content)

    added = current_exports - original_exports
    removed = original_exports - current_exports

    if added or removed:
        parts = []
        if added:
            parts.append(f"Added exports: {sorted(added)}")
        if removed:
            parts.append(f"Removed exports: {sorted(removed)}")
        message = "; ".join(parts)
        success = False
    else:
        message = "Exports unchanged"
        success = True

    return ValidationResult(
        success=success,
        original_exports=original_exports,
        current_exports=current_exports,
        added=added,
        removed=removed,
        message=message,
    )
