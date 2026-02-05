"""Independent compiler for FreeSpec.

Compiles each spec file independently, like gcc compiling .c files.
Each file only sees its @mentioned interfaces and generates both
implementation and tests together. Tests are run to verify the
implementation, with retries on failure.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from tqdm import tqdm

from freespec.config import FreeSpecConfig
from freespec.generator.cpp_runner import CppTestRunner
from freespec.generator.prompts import PromptBuilder
from freespec.generator.runner import PytestRunner
from freespec.llm.claude_code import ClaudeCodeClient
from freespec.parser.models import SpecFile
from freespec.verifier.exports import extract_public_exports

if TYPE_CHECKING:
    from freespec.rebuild.detector import RebuildDetector

logger = logging.getLogger("freespec.generator.compiler")


class CompileError(Exception):
    """Raised when compilation fails."""


MAX_REVIEW_RETRIES = 3


@dataclass
class CompileResult:
    """Result of compiling a single spec file."""

    spec_id: str
    success: bool
    impl_path: Path | None = None
    test_path: Path | None = None
    error: str | None = None
    duration_seconds: float = 0.0
    log_file: Path | None = None
    review_attempts: int = 0
    review_passed: bool = False


@dataclass
class CompileContext:
    """Context for tracking compilation state."""

    config: FreeSpecConfig
    all_headers: dict[str, str]
    results: list[CompileResult] = field(default_factory=list)

    @property
    def passed(self) -> list[CompileResult]:
        """Get all successful compilations."""
        return [r for r in self.results if r.success]

    @property
    def failed(self) -> list[CompileResult]:
        """Get all failed compilations."""
        return [r for r in self.results if not r.success]


class IndependentCompiler:
    """Compiles spec files independently with test verification.

    Each file is compiled in isolation:
    1. Filter headers to only @mentioned dependencies
    2. Generate implementation + tests together in one LLM call
    3. Run tests with pytest (Python) or compiled executable (C++)
    4. If tests fail, retry with error feedback
    5. Report success/failure per module
    """

    def __init__(
        self,
        client: ClaudeCodeClient | None = None,
        prompt_builder: PromptBuilder | None = None,
        test_runner: PytestRunner | CppTestRunner | None = None,
        log_dir: Path | None = None,
    ) -> None:
        """Initialize the independent compiler.

        Args:
            client: Claude Code client for LLM calls.
            prompt_builder: Builder for generation prompts.
            test_runner: Runner for executing tests (auto-detected if None).
            log_dir: Directory to save compilation logs.
        """
        self.client = client or ClaudeCodeClient()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.test_runner = test_runner
        self.log_dir = log_dir

    def _get_test_runner(
        self, config: FreeSpecConfig, language: str
    ) -> PytestRunner | CppTestRunner:
        """Get the appropriate test runner for the language.

        Args:
            config: Project configuration.
            language: Target language (python, cpp).

        Returns:
            PytestRunner for Python, CppTestRunner for C++.
        """
        if self.test_runner:
            return self.test_runner

        lang = language.lower()
        if lang in ("cpp", "c++"):
            return CppTestRunner(
                working_dir=config.root_path,
                log_dir=self.log_dir,
                out_dir=config.get_output_path(language),
            )
        else:
            return PytestRunner(working_dir=config.root_path)

    def _get_file_ext(self, language: str) -> str:
        """Get file extension for the target language."""
        if language.lower() in ("cpp", "c++"):
            return ".cpp"
        return ".py"

    def _get_impl_path(self, spec: SpecFile, config: FreeSpecConfig, language: str) -> Path:
        """Determine output path for a spec's implementation file.

        Headers and implementations go to out/{language}/src/:
        specs/entities/student.spec → out/python/src/entities/student.py
        """
        ext = self._get_file_ext(language)
        base = config.get_src_path(language)
        return base / spec.category / f"{spec.name}{ext}"

    def _get_test_path(self, spec: SpecFile, config: FreeSpecConfig, language: str) -> Path:
        """Determine output path for a spec's test file.

        Tests go to out/{language}/tests/:
        specs/entities/student.spec → out/python/tests/entities/test_student.py
        """
        ext = self._get_file_ext(language)
        base = config.get_tests_path(language)
        return base / spec.category / f"test_{spec.name}{ext}"

    def _filter_headers_for_spec(
        self,
        spec: SpecFile,
        all_headers: dict[str, str],
    ) -> dict[str, str]:
        """Filter headers to only those @mentioned by the spec."""
        return {m: all_headers[m] for m in spec.mentions if m in all_headers}

    def _get_dependency_paths_for_spec(
        self,
        spec: SpecFile,
        config: FreeSpecConfig,
        language: str,
    ) -> dict[str, Path]:
        """Get file paths for @mentioned dependencies.

        Dependencies are in the out/{language}/src/ directory structure.
        """
        dependency_paths: dict[str, Path] = {}
        src_dir = config.get_src_path(language)
        ext = self._get_file_ext(language)

        for mention in spec.mentions:
            # Parse mention like "entities/student" -> out/python/src/entities/student.py or .cpp
            parts = mention.split("/")
            if len(parts) == 2:
                category, name = parts
                dep_path = src_dir / category / f"{name}{ext}"
                if dep_path.exists():
                    dependency_paths[mention] = dep_path

        return dependency_paths

    def _extract_code_from_output(self, output: str) -> str | None:
        """Try to extract code from LLM output if file wasn't written."""
        import re

        pattern = r"```python\n(.*?)```"
        matches = re.findall(pattern, output, re.DOTALL)
        if matches:
            return matches[-1].strip()

        pattern = r"```\n(.*?)```"
        matches = re.findall(pattern, output, re.DOTALL)
        if matches:
            return matches[-1].strip()

        return None

    def _validate_module_import(
        self,
        impl_path: Path,
        config: FreeSpecConfig,
        language: str,
    ) -> str | None:
        """Validate that a module can be imported without errors.

        This catches issues like accessing non-existent fields on dependencies
        at import time (e.g., module-level code).

        Args:
            impl_path: Path to the implementation file.
            config: Project configuration.
            language: Target language.

        Returns:
            Error message if import failed, None if successful.
        """
        import subprocess
        import sys

        if language.lower() != "python":
            return None  # Only validate Python modules

        # Build the module import path
        # e.g., out/python/src/entities/student.py -> src.entities.student
        rel_parts = impl_path.parts
        if "src" in rel_parts:
            src_idx = rel_parts.index("src")
            module_parts = rel_parts[src_idx:-1] + (impl_path.stem,)
            module_name = ".".join(module_parts)
        else:
            return None  # Can't determine module path

        # Run import in subprocess to avoid polluting our namespace
        src_dir = config.get_src_path(language).parent  # Go to out/python/ level
        cmd = [
            sys.executable,
            "-c",
            f"import sys; sys.path.insert(0, '{src_dir}'); import {module_name}",
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=config.root_path,
            )
            if result.returncode != 0:
                return result.stderr or result.stdout or "Unknown import error"
            return None
        except subprocess.TimeoutExpired:
            return "Import timed out"
        except Exception as e:
            return str(e)

    def compile_file(
        self,
        spec: SpecFile,
        context: CompileContext,
        language: str,
        detector: RebuildDetector | None = None,
    ) -> CompileResult:
        """Compile a single spec file with test verification and review.

        Flow:
        1. Read original stub file and extract exports for validation
        2. Generate implementation (in-place) and tests
        3. Verify files exist
        4. Run tests
        5. If tests pass, run review (with export validation)
        6. If review fails, send feedback and retry (up to MAX_REVIEW_RETRIES)

        Args:
            spec: The spec to compile.
            context: Compilation context with config and all headers.
            language: Target language (python, cpp).
            detector: Optional rebuild detector to update manifest.

        Returns:
            CompileResult indicating success/failure.
        """
        impl_path = self._get_impl_path(spec, context.config, language)
        # Only set test_path if spec has test cases defined
        has_tests = bool(spec.tests.items)
        test_path = self._get_test_path(spec, context.config, language) if has_tests else None

        # Create output directories
        impl_path.parent.mkdir(parents=True, exist_ok=True)
        if test_path:
            test_path.parent.mkdir(parents=True, exist_ok=True)

        # Read original stub content and extract exports for validation
        original_exports: set[str] = set()
        if impl_path.exists():
            original_content = impl_path.read_text()
            original_exports = extract_public_exports(original_content)
            logger.debug("  Original exports: %s", sorted(original_exports))

        # Get file paths for @mentioned dependencies
        dependency_paths = self._get_dependency_paths_for_spec(spec, context.config, language)

        logger.info(
            "Compiling %s (depends on: %s)",
            spec.spec_id,
            list(dependency_paths.keys()) or "none",
        )

        # Set current spec and phase for logging
        self.client.set_current_spec(spec.spec_id)
        self.client.set_current_phase("impl")

        # Generate impl + tests - Claude Code will iterate until tests pass
        prompt = self.prompt_builder.build_compile_prompt(
            spec=spec,
            language=language,
            impl_path=impl_path,
            test_path=test_path,
            dependency_paths=dependency_paths,
        )

        result = self.client.generate(prompt)
        session_id = result.session_id
        total_duration = result.duration_seconds
        last_log_file = result.log_file

        if not result.success:
            logger.error("  Generation failed: %s", result.error)
            compile_result = CompileResult(
                spec_id=spec.spec_id,
                success=False,
                impl_path=impl_path,
                test_path=test_path,
                error=f"Generation failed: {result.error}",
                duration_seconds=total_duration,
                log_file=last_log_file,
            )
            context.results.append(compile_result)
            return compile_result

        # Review loop - verify files, tests, and spec fulfillment
        runner = self._get_test_runner(context.config, language)
        # Set current spec for logging (if runner supports it)
        if hasattr(runner, "set_current_spec"):
            runner.set_current_spec(spec.spec_id)

        last_failure_reason = "Unknown failure"
        review_attempts = 0
        is_cpp = language.lower() in ("cpp", "c++")

        for attempt in range(MAX_REVIEW_RETRIES):
            # Track attempt number for logging
            self.client.set_current_attempt(attempt + 1)

            # Verify impl file exists
            if not impl_path.exists():
                logger.warning("  Impl file not written, asking to write it...")
                last_failure_reason = "Impl file not written"
                self.client.set_current_phase("fix")
                result = self.client.generate(
                    "The implementation file was not written. "
                    "Please write it to the specified path.",
                    session_id,
                )
                total_duration += result.duration_seconds
                last_log_file = result.log_file or last_log_file
                continue

            # Verify test file exists (only if spec has tests)
            if test_path and not test_path.exists():
                logger.warning("  Test file not written, asking to write it...")
                last_failure_reason = "Test file not written"
                self.client.set_current_phase("fix")
                result = self.client.generate(
                    "The test file was not written. Please write it to the specified path.",
                    session_id,
                )
                total_duration += result.duration_seconds
                last_log_file = result.log_file or last_log_file
                continue

            # Run tests (only if spec has tests)
            if test_path:
                if is_cpp:
                    # For C++, pass both test and impl paths
                    test_result = runner.run_test(test_path, impl_path)
                else:
                    test_result = runner.run_test(test_path)

                if not test_result.success:
                    logger.warning(
                        "  Tests failed (attempt %d/%d), asking to fix...",
                        attempt + 1,
                        MAX_REVIEW_RETRIES,
                    )
                    last_failure_reason = f"Tests failed:\n{test_result.output}"
                    self.client.set_current_phase("fix")

                    if is_cpp:
                        fix_prompt = (
                            f"C++ compilation/tests failed.\n\n"
                            f"Output:\n{test_result.output}\n\n"
                            "Fix the code and ensure it compiles and tests pass."
                        )
                    else:
                        cmd = f"python -m pytest {test_path} -v --tb=short"
                        fix_prompt = (
                            f"Tests failed when running: {cmd}\n\nOutput:\n{test_result.output}\n\n"
                        )
                        # Add specific guidance for common errors
                        if "AttributeError" in test_result.output:
                            fix_prompt += (
                                "\n**AttributeError detected!** "
                                "You used a field/method that doesn't exist.\n"
                                "READ the dependency file to see what's available.\n"
                                "Do NOT guess - check the actual source code.\n\n"
                            )
                        if "TypeError" in test_result.output and "argument" in test_result.output:
                            fix_prompt += (
                                "\n**TypeError detected!** "
                                "You called a function with wrong arguments.\n"
                                "READ the dependency file for the correct signature.\n"
                                "Do NOT guess - check the actual source code.\n\n"
                            )
                        fix_prompt += "Fix the code and run that exact command to verify."
                    result = self.client.generate(fix_prompt, session_id)
                    total_duration += result.duration_seconds
                    last_log_file = result.log_file or last_log_file
                    continue

            # Tests passed (or no tests defined) - validate module can be imported
            if not is_cpp and impl_path.exists():
                import_error = self._validate_module_import(impl_path, context.config, language)
                if import_error:
                    logger.warning("  Module import validation failed: %s", import_error[:200])
                    last_failure_reason = f"Import validation failed: {import_error}"
                    self.client.set_current_phase("fix")
                    fix_prompt = (
                        f"Module import validation FAILED.\n\n"
                        f"Error: {import_error}\n\n"
                        "This usually means you're using a field/method/class "
                        "that doesn't exist.\n"
                        "READ the dependency files to see what's available.\n"
                        "Do NOT guess - check the actual source code.\n\n"
                        "Fix the implementation so the module can be imported."
                    )
                    result = self.client.generate(fix_prompt, session_id)
                    total_duration += result.duration_seconds
                    last_log_file = result.log_file or last_log_file
                    continue

            # Validate exports programmatically
            if original_exports and impl_path.exists():
                current_content = impl_path.read_text()
                current_exports = extract_public_exports(current_content)

                added_exports = current_exports - original_exports
                removed_exports = original_exports - current_exports

                if added_exports or removed_exports:
                    logger.warning(
                        "  Export validation failed: added=%s, removed=%s",
                        sorted(added_exports),
                        sorted(removed_exports),
                    )
                    last_failure_reason = (
                        f"Exports changed: added={sorted(added_exports)}, "
                        f"removed={sorted(removed_exports)}"
                    )
                    self.client.set_current_phase("fix")

                    fix_prompt = (
                        "EXPORT VALIDATION FAILED - Fix the implementation.\n\n"
                        f"Original header exports: {sorted(original_exports)}\n"
                        f"Current implementation exports: {sorted(current_exports)}\n\n"
                    )
                    if added_exports:
                        fix_prompt += (
                            f"PROBLEM: You ADDED exports not in header: {sorted(added_exports)}\n"
                        )
                        fix_prompt += "Remove these or make them private (prefix with _).\n\n"
                    if removed_exports:
                        fix_prompt += (
                            f"PROBLEM: You REMOVED exports from header: {sorted(removed_exports)}\n"
                        )
                        fix_prompt += "Add these back - don't remove from the header.\n\n"
                    fix_prompt += "Implementation must have EXACTLY same exports as header."

                    result = self.client.generate(fix_prompt, session_id)
                    total_duration += result.duration_seconds
                    last_log_file = result.log_file or last_log_file
                    continue

            # Exports validated - now REVIEW for spec fulfillment
            logger.info("  Exports validated, running spec review...")
            review_attempts += 1
            self.client.set_current_phase("review")
            review_prompt = self.prompt_builder.build_review_prompt(
                spec,
                impl_path,
                test_path,
                original_exports=original_exports if original_exports else None,
            )
            review_result = self.client.generate(review_prompt, session_id)
            total_duration += review_result.duration_seconds
            last_log_file = review_result.log_file or last_log_file

            if "REVIEW_PASSED" in review_result.output:
                logger.info("  Review passed!")
                # Update manifest if detector provided
                if detector:
                    detector.update_manifest_after_compile(spec, impl_path, test_path)
                compile_result = CompileResult(
                    spec_id=spec.spec_id,
                    success=True,
                    impl_path=impl_path,
                    test_path=test_path,
                    duration_seconds=total_duration,
                    log_file=last_log_file,
                    review_attempts=review_attempts,
                    review_passed=True,
                )
                context.results.append(compile_result)
                return compile_result

            # Review failed - Claude was already told to fix issues in the review prompt
            last_failure_reason = f"Review failed: {review_result.output[:500]}"
            logger.info(f"  Review failed (attempt {review_attempts}/{MAX_REVIEW_RETRIES})")

        # All retries exhausted
        logger.error("  Compilation failed after %d attempts", MAX_REVIEW_RETRIES)
        compile_result = CompileResult(
            spec_id=spec.spec_id,
            success=False,
            impl_path=impl_path,
            test_path=test_path,
            error=last_failure_reason,
            duration_seconds=total_duration,
            log_file=last_log_file,
            review_attempts=review_attempts,
            review_passed=False,
        )
        context.results.append(compile_result)
        return compile_result

    def compile_all(
        self,
        specs: list[SpecFile],
        config: FreeSpecConfig,
        all_headers: dict[str, str],
        language: str,
        fail_fast: bool = True,
        detector: RebuildDetector | None = None,
        num_workers: int = 1,
    ) -> CompileContext:
        """Compile all spec files, forking from a shared instructions session.

        Sends instructions once at the start, then forks for each spec
        so each compilation starts fresh from the instructions state.

        Args:
            specs: Specs to compile (any order).
            config: Project configuration.
            all_headers: Map of all spec_id to their header content.
            language: Target language (python, cpp).
            fail_fast: Stop on first module failure (default: True).
            detector: Optional rebuild detector to update manifest.
            num_workers: Number of parallel workers (1 = sequential).

        Returns:
            CompileContext with all results.
        """
        context = CompileContext(config=config, all_headers=all_headers)

        if not specs:
            return context

        # Send instructions once at the start
        logger.info("Creating compilation session with instructions...")
        self.client.set_current_spec("_compile_instructions")
        self.client.set_current_phase("instructions")

        instructions = self.prompt_builder.build_compile_instructions_prompt(
            language=language,
        )
        result = self.client.generate(instructions)

        if not result.success:
            logger.error("Failed to create compilation session: %s", result.error)
            # Fall back to independent compilation
            logger.warning("Falling back to independent compilation")
            for spec in specs:
                compile_result = self.compile_file(spec, context, language, detector)
                if fail_fast and not compile_result.success:
                    logger.warning("Stopping early due to fail-fast")
                    break
            return context

        base_session_id = result.session_id
        logger.info("Compilation session created: %s", base_session_id[:8] + "...")

        # Use parallel or sequential based on num_workers
        if num_workers > 1 and len(specs) > 1:
            return self._compile_parallel(
                specs, context, language, base_session_id, fail_fast, detector, num_workers
            )

        # Sequential: Fork for each spec (each starts fresh from instructions)
        for spec in tqdm(specs, desc="Compiling", unit="spec", disable=len(specs) <= 1):
            compile_result = self._compile_file_forked(
                spec, context, language, base_session_id, detector
            )

            if fail_fast and not compile_result.success:
                logger.warning("Stopping early due to fail-fast")
                break

        return context

    def _compile_parallel(
        self,
        specs: list[SpecFile],
        context: CompileContext,
        language: str,
        base_session_id: str,
        fail_fast: bool,
        detector: RebuildDetector | None,
        num_workers: int,
    ) -> CompileContext:
        """Compile specs in parallel using ThreadPoolExecutor.

        Args:
            specs: Specs to compile.
            context: Compilation context.
            language: Target language.
            base_session_id: Session ID to fork from.
            fail_fast: Stop on first failure.
            detector: Optional rebuild detector.
            num_workers: Number of parallel workers.

        Returns:
            CompileContext with all results.
        """
        results_lock = threading.Lock()
        stop_event = threading.Event()

        def compile_spec(spec: SpecFile) -> CompileResult:
            if stop_event.is_set():
                return CompileResult(
                    spec_id=spec.spec_id,
                    success=False,
                    error="Stopped due to fail-fast",
                )
            return self._compile_file_forked(spec, context, language, base_session_id, detector)

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            future_to_spec = {executor.submit(compile_spec, spec): spec for spec in specs}

            with tqdm(total=len(specs), desc="Compiling", unit="spec") as pbar:
                for future in as_completed(future_to_spec):
                    spec = future_to_spec[future]
                    try:
                        result = future.result()
                        with results_lock:
                            context.results.append(result)

                        if fail_fast and not result.success:
                            logger.warning("Setting stop flag due to fail-fast")
                            stop_event.set()
                    except Exception as e:
                        logger.error("Compilation failed for %s: %s", spec.spec_id, e)
                        with results_lock:
                            context.results.append(
                                CompileResult(
                                    spec_id=spec.spec_id,
                                    success=False,
                                    error=str(e),
                                )
                            )
                        if fail_fast:
                            stop_event.set()
                    finally:
                        pbar.update(1)
                        pbar.set_postfix(last=spec.spec_id[:20])

        return context

    def _compile_file_forked(
        self,
        spec: SpecFile,
        context: CompileContext,
        language: str,
        base_session_id: str,
        detector: RebuildDetector | None = None,
    ) -> CompileResult:
        """Compile a spec file by forking from the instructions session.

        Each file starts fresh from the instructions state.

        Args:
            spec: The spec to compile.
            context: Compilation context with config and all headers.
            language: Target language (python, cpp).
            base_session_id: Session ID to fork from.
            detector: Optional rebuild detector to update manifest.

        Returns:
            CompileResult indicating success/failure.
        """
        impl_path = self._get_impl_path(spec, context.config, language)
        # Only set test_path if spec has test cases defined
        has_tests = bool(spec.tests.items)
        test_path = self._get_test_path(spec, context.config, language) if has_tests else None

        # Create output directories
        impl_path.parent.mkdir(parents=True, exist_ok=True)
        if test_path:
            test_path.parent.mkdir(parents=True, exist_ok=True)

        # Read original stub content and extract exports for validation
        original_exports: set[str] = set()
        if impl_path.exists():
            original_content = impl_path.read_text()
            original_exports = extract_public_exports(original_content)
            logger.debug("  Original exports: %s", sorted(original_exports))

        # Get file paths for @mentioned dependencies
        dependency_paths = self._get_dependency_paths_for_spec(spec, context.config, language)

        logger.info(
            "Compiling %s (depends on: %s)",
            spec.spec_id,
            list(dependency_paths.keys()) or "none",
        )

        # Set current spec and phase for logging
        self.client.set_current_spec(spec.spec_id)
        self.client.set_current_phase("impl")

        # Build minimal prompt - just the spec path and output paths
        prompt = self._build_minimal_compile_prompt(spec, impl_path, test_path, dependency_paths)

        # Fork from base session (starts fresh from instructions)
        result = self.client.fork_session(base_session_id, prompt)
        forked_session_id = result.session_id  # New session for this file
        total_duration = result.duration_seconds
        last_log_file = result.log_file

        if not result.success:
            logger.error("  Generation failed: %s", result.error)
            compile_result = CompileResult(
                spec_id=spec.spec_id,
                success=False,
                impl_path=impl_path,
                test_path=test_path,
                error=f"Generation failed: {result.error}",
                duration_seconds=total_duration,
                log_file=last_log_file,
            )
            context.results.append(compile_result)
            return compile_result

        # Review loop
        runner = self._get_test_runner(context.config, language)
        if hasattr(runner, "set_current_spec"):
            runner.set_current_spec(spec.spec_id)

        last_failure_reason = "Unknown failure"
        review_attempts = 0
        is_cpp = language.lower() in ("cpp", "c++")

        for attempt in range(MAX_REVIEW_RETRIES):
            # Track attempt number for logging
            self.client.set_current_attempt(attempt + 1)

            # Verify impl file exists
            if not impl_path.exists():
                logger.warning("  Impl file not written, asking to write it...")
                last_failure_reason = "Impl file not written"
                self.client.set_current_phase("fix")
                result = self.client.generate(
                    "The implementation file was not written. "
                    "Please write it to the specified path.",
                    forked_session_id,
                )
                total_duration += result.duration_seconds
                last_log_file = result.log_file or last_log_file
                continue

            # Verify test file exists (only if spec has tests)
            if test_path and not test_path.exists():
                logger.warning("  Test file not written, asking to write it...")
                last_failure_reason = "Test file not written"
                self.client.set_current_phase("fix")
                result = self.client.generate(
                    "The test file was not written. Please write it to the specified path.",
                    forked_session_id,
                )
                total_duration += result.duration_seconds
                last_log_file = result.log_file or last_log_file
                continue

            # Run tests (only if spec has tests)
            if test_path:
                if is_cpp:
                    test_result = runner.run_test(test_path, impl_path)
                else:
                    test_result = runner.run_test(test_path)

                if not test_result.success:
                    logger.warning(
                        "  Tests failed (attempt %d/%d), asking to fix...",
                        attempt + 1,
                        MAX_REVIEW_RETRIES,
                    )
                    last_failure_reason = f"Tests failed:\n{test_result.output}"
                    self.client.set_current_phase("fix")

                    if is_cpp:
                        fix_prompt = (
                            f"C++ compilation/tests failed.\n\n"
                            f"Output:\n{test_result.output}\n\n"
                            "Fix the code and ensure it compiles and tests pass."
                        )
                    else:
                        cmd = f"python -m pytest {test_path} -v --tb=short"
                        fix_prompt = (
                            f"Tests failed when running: {cmd}\n\nOutput:\n{test_result.output}\n\n"
                        )
                        # Add specific guidance for common errors
                        if "AttributeError" in test_result.output:
                            fix_prompt += (
                                "\n**AttributeError detected!** "
                                "You used a field/method that doesn't exist.\n"
                                "READ the dependency file to see what's available.\n"
                                "Do NOT guess - check the actual source code.\n\n"
                            )
                        if "TypeError" in test_result.output and "argument" in test_result.output:
                            fix_prompt += (
                                "\n**TypeError detected!** "
                                "You called a function with wrong arguments.\n"
                                "READ the dependency file for the correct signature.\n"
                                "Do NOT guess - check the actual source code.\n\n"
                            )
                        fix_prompt += "Fix the code and run that exact command to verify."
                    result = self.client.generate(fix_prompt, forked_session_id)
                    total_duration += result.duration_seconds
                    last_log_file = result.log_file or last_log_file
                    continue

            # Tests passed (or no tests defined) - validate module can be imported
            if not is_cpp and impl_path.exists():
                import_error = self._validate_module_import(impl_path, context.config, language)
                if import_error:
                    logger.warning("  Module import validation failed: %s", import_error[:200])
                    last_failure_reason = f"Import validation failed: {import_error}"
                    self.client.set_current_phase("fix")
                    fix_prompt = (
                        f"Module import validation FAILED.\n\n"
                        f"Error: {import_error}\n\n"
                        "This usually means you're using a field/method/class "
                        "that doesn't exist.\n"
                        "READ the dependency files to see what's available.\n"
                        "Do NOT guess - check the actual source code.\n\n"
                        "Fix the implementation so the module can be imported."
                    )
                    result = self.client.generate(fix_prompt, forked_session_id)
                    total_duration += result.duration_seconds
                    last_log_file = result.log_file or last_log_file
                    continue

            # Validate exports programmatically
            if original_exports and impl_path.exists():
                current_content = impl_path.read_text()
                current_exports = extract_public_exports(current_content)

                added_exports = current_exports - original_exports
                removed_exports = original_exports - current_exports

                if added_exports or removed_exports:
                    logger.warning(
                        "  Export validation failed: added=%s, removed=%s",
                        sorted(added_exports),
                        sorted(removed_exports),
                    )
                    last_failure_reason = (
                        f"Exports changed: added={sorted(added_exports)}, "
                        f"removed={sorted(removed_exports)}"
                    )
                    self.client.set_current_phase("fix")

                    fix_prompt = (
                        "EXPORT VALIDATION FAILED - Fix the implementation.\n\n"
                        f"Original header exports: {sorted(original_exports)}\n"
                        f"Current implementation exports: {sorted(current_exports)}\n\n"
                    )
                    if added_exports:
                        fix_prompt += (
                            f"PROBLEM: You ADDED exports not in header: {sorted(added_exports)}\n"
                        )
                        fix_prompt += "Remove these or make them private (prefix with _).\n\n"
                    if removed_exports:
                        fix_prompt += (
                            f"PROBLEM: You REMOVED exports from header: {sorted(removed_exports)}\n"
                        )
                        fix_prompt += "Add these back - don't remove from the header.\n\n"
                    fix_prompt += "Implementation must have EXACTLY same exports as header."

                    result = self.client.generate(fix_prompt, forked_session_id)
                    total_duration += result.duration_seconds
                    last_log_file = result.log_file or last_log_file
                    continue

            # Exports validated - now REVIEW for spec fulfillment
            logger.info("  Exports validated, running spec review...")
            review_attempts += 1
            self.client.set_current_phase("review")
            review_prompt = self.prompt_builder.build_review_prompt(
                spec,
                impl_path,
                test_path,
                original_exports=original_exports if original_exports else None,
            )
            review_result = self.client.generate(review_prompt, forked_session_id)
            total_duration += review_result.duration_seconds
            last_log_file = review_result.log_file or last_log_file

            if "REVIEW_PASSED" in review_result.output:
                logger.info("  Review passed!")
                # Update manifest if detector provided
                if detector:
                    detector.update_manifest_after_compile(spec, impl_path, test_path)
                compile_result = CompileResult(
                    spec_id=spec.spec_id,
                    success=True,
                    impl_path=impl_path,
                    test_path=test_path,
                    duration_seconds=total_duration,
                    log_file=last_log_file,
                    review_attempts=review_attempts,
                    review_passed=True,
                )
                context.results.append(compile_result)
                return compile_result

            # Review failed
            last_failure_reason = f"Review failed: {review_result.output[:500]}"
            logger.info(f"  Review failed (attempt {review_attempts}/{MAX_REVIEW_RETRIES})")

        # All retries exhausted
        logger.error("  Compilation failed after %d attempts", MAX_REVIEW_RETRIES)
        compile_result = CompileResult(
            spec_id=spec.spec_id,
            success=False,
            impl_path=impl_path,
            test_path=test_path,
            error=last_failure_reason,
            duration_seconds=total_duration,
            log_file=last_log_file,
            review_attempts=review_attempts,
            review_passed=False,
        )
        context.results.append(compile_result)
        return compile_result

    def _build_minimal_compile_prompt(
        self,
        spec: SpecFile,
        impl_path: Path,
        test_path: Path | None,
        dependency_paths: dict[str, Path],
    ) -> str:
        """Build a minimal prompt for compiling a spec.

        Just references the files - Claude will read them.
        """
        parts = [
            f"Compile: {spec.spec_id}",
            "",
            f"Spec file: {spec.path}",
            f"Stub file (modify in-place): {impl_path}",
        ]

        if test_path:
            parts.append(f"Test file (create): {test_path}")
        else:
            parts.append("No tests defined for this spec.")

        if dependency_paths:
            parts.append("")
            parts.append("Dependencies to read if needed:")
            for dep_id, dep_path in sorted(dependency_paths.items()):
                parts.append(f"  - {dep_id}: {dep_path}")

        return "\n".join(parts)
