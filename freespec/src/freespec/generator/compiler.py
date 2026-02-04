"""Independent compiler for FreeSpec.

Compiles each spec file independently, like gcc compiling .c files.
Each file only sees its @mentioned interfaces and generates both
implementation and tests together. Tests are run to verify the
implementation, with retries on failure.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from freespec.config import FreeSpecConfig
from freespec.generator.cpp_runner import CppTestRunner
from freespec.generator.prompts import PromptBuilder
from freespec.generator.runner import PytestRunner
from freespec.llm.claude_code import ClaudeCodeClient
from freespec.parser.models import SpecFile
from freespec.verifier.exports import extract_public_exports

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

    def _get_test_runner(self, config: FreeSpecConfig) -> PytestRunner | CppTestRunner:
        """Get the appropriate test runner for the language.

        Args:
            config: Project configuration.

        Returns:
            PytestRunner for Python, CppTestRunner for C++.
        """
        if self.test_runner:
            return self.test_runner

        lang = config.language.lower()
        if lang in ("cpp", "c++"):
            return CppTestRunner(
                working_dir=config.root_path,
                log_dir=self.log_dir,
                out_dir=config.get_output_path(),
            )
        else:
            return PytestRunner(working_dir=config.root_path)

    def _get_file_ext(self, config: FreeSpecConfig) -> str:
        """Get file extension for the target language."""
        lang = config.language.lower()
        if lang in ("cpp", "c++"):
            return ".cpp"
        return ".py"

    def _get_impl_path(self, spec: SpecFile, config: FreeSpecConfig) -> Path:
        """Determine output path for a spec's implementation file.

        Headers and implementations go to out/src/:
        specs/entities/student.spec → out/src/entities/student.py
        """
        ext = self._get_file_ext(config)
        base = config.get_src_path()
        return base / spec.category / f"{spec.name}{ext}"

    def _get_test_path(self, spec: SpecFile, config: FreeSpecConfig) -> Path:
        """Determine output path for a spec's test file.

        Tests go to out/tests/:
        specs/entities/student.spec → out/tests/entities/test_student.py
        """
        ext = self._get_file_ext(config)
        base = config.get_tests_path()
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
    ) -> dict[str, Path]:
        """Get file paths for @mentioned dependencies.

        Dependencies are in the out/src/ directory structure.
        """
        dependency_paths: dict[str, Path] = {}
        src_dir = config.get_src_path()
        ext = self._get_file_ext(config)

        for mention in spec.mentions:
            # Parse mention like "entities/student" -> out/src/entities/student.py or .cpp
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

    def compile_file(
        self,
        spec: SpecFile,
        context: CompileContext,
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

        Returns:
            CompileResult indicating success/failure.
        """
        impl_path = self._get_impl_path(spec, context.config)
        test_path = self._get_test_path(spec, context.config)

        # Create output directories
        impl_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.parent.mkdir(parents=True, exist_ok=True)

        # Read original stub content and extract exports for validation
        original_exports: set[str] = set()
        if impl_path.exists():
            original_content = impl_path.read_text()
            original_exports = extract_public_exports(original_content)
            logger.debug("  Original exports: %s", sorted(original_exports))

        # Get file paths for @mentioned dependencies
        dependency_paths = self._get_dependency_paths_for_spec(spec, context.config)

        logger.info(
            "Compiling %s (depends on: %s)",
            spec.spec_id,
            list(dependency_paths.keys()) or "none",
        )

        # Set current spec for logging
        self.client.set_current_spec(spec.spec_id)

        # Generate impl + tests - Claude Code will iterate until tests pass
        prompt = self.prompt_builder.build_compile_prompt(
            spec=spec,
            language=context.config.language,
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
        runner = self._get_test_runner(context.config)
        # Set current spec for logging (if runner supports it)
        if hasattr(runner, "set_current_spec"):
            runner.set_current_spec(spec.spec_id)

        last_failure_reason = "Unknown failure"
        review_attempts = 0
        is_cpp = context.config.language.lower() in ("cpp", "c++")

        for attempt in range(MAX_REVIEW_RETRIES):
            # Verify files exist
            if not impl_path.exists() or not test_path.exists():
                logger.warning("  Files not written, asking to write them...")
                last_failure_reason = "Files not written"
                result = self.client.generate(
                    "The files were not written. Please write them to the specified paths.",
                    session_id,
                )
                total_duration += result.duration_seconds
                last_log_file = result.log_file or last_log_file
                continue

            # Run tests
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

                if is_cpp:
                    fix_prompt = (
                        f"C++ compilation/tests failed.\n\n"
                        f"Output:\n{test_result.output}\n\n"
                        "Fix the code and ensure it compiles and tests pass."
                    )
                else:
                    fix_prompt = (
                        f"Tests failed when running: python -m pytest {test_path} -v --tb=short\n\n"
                        f"Output:\n{test_result.output}\n\n"
                        "Fix the code and run that exact command to verify."
                    )
                result = self.client.generate(fix_prompt, session_id)
                total_duration += result.duration_seconds
                last_log_file = result.log_file or last_log_file
                continue

            # Tests passed - now REVIEW with export validation
            logger.info("  Tests passed, running review...")
            review_attempts += 1
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
        fail_fast: bool = False,
    ) -> CompileContext:
        """Compile all spec files independently.

        Args:
            specs: Specs to compile (any order).
            config: Project configuration.
            all_headers: Map of all spec_id to their header content.
            fail_fast: Stop on first module failure.

        Returns:
            CompileContext with all results.
        """
        context = CompileContext(config=config, all_headers=all_headers)

        for spec in specs:
            result = self.compile_file(spec, context)

            if fail_fast and not result.success:
                logger.warning("Stopping early due to --fail-fast")
                break

        return context
