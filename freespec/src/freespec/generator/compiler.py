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
from freespec.generator.prompts import PromptBuilder
from freespec.generator.runner import PytestRunner
from freespec.llm.claude_code import ClaudeCodeClient
from freespec.parser.models import SpecFile

logger = logging.getLogger("freespec.generator.compiler")


class CompileError(Exception):
    """Raised when compilation fails."""


@dataclass
class CompileResult:
    """Result of compiling a single spec file."""

    spec_id: str
    success: bool
    impl_path: Path | None = None
    test_path: Path | None = None
    attempts: int = 1
    error: str | None = None


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
    3. Run tests with pytest
    4. If tests fail, retry with error feedback
    5. Report success/failure per module
    """

    def __init__(
        self,
        client: ClaudeCodeClient | None = None,
        prompt_builder: PromptBuilder | None = None,
        test_runner: PytestRunner | None = None,
        max_retries: int = 3,
    ) -> None:
        """Initialize the independent compiler.

        Args:
            client: Claude Code client for LLM calls.
            prompt_builder: Builder for generation prompts.
            test_runner: Runner for executing pytest.
            max_retries: Maximum retry attempts per module (default: 3).
        """
        self.client = client or ClaudeCodeClient()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.test_runner = test_runner
        self.max_retries = max_retries

    def _get_impl_path(self, spec: SpecFile, config: FreeSpecConfig) -> Path:
        """Determine output path for a spec's implementation file."""
        if spec.category == "api":
            base = config.get_output_path("api")
            return base / f"{spec.name}.py"
        else:
            base = config.get_output_path("impl")
            return base / spec.category / f"{spec.name}.py"

    def _get_test_path(self, spec: SpecFile, config: FreeSpecConfig) -> Path:
        """Determine output path for a spec's test file."""
        base = config.get_output_path("tests")
        return base / spec.category / f"test_{spec.name}.py"

    def _filter_headers_for_spec(
        self,
        spec: SpecFile,
        all_headers: dict[str, str],
    ) -> dict[str, str]:
        """Filter headers to only those @mentioned by the spec."""
        return {m: all_headers[m] for m in spec.mentions if m in all_headers}

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
        """Compile a single spec file with test verification.

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

        # Filter to only @mentioned headers
        mentioned_headers = self._filter_headers_for_spec(spec, context.all_headers)

        logger.info(
            "Compiling %s (depends on: %s)",
            spec.spec_id,
            list(mentioned_headers.keys()) or "none",
        )

        previous_error: str | None = None

        for attempt in range(self.max_retries + 1):
            attempt_num = attempt + 1
            logger.info("  Attempt %d/%d", attempt_num, self.max_retries + 1)

            # Generate impl + tests together
            prompt = self.prompt_builder.build_compile_prompt(
                spec=spec,
                language=context.config.language,
                impl_path=impl_path,
                test_path=test_path,
                mentioned_headers=mentioned_headers,
                previous_error=previous_error,
            )

            result = self.client.generate(prompt)

            if not result.success:
                logger.error("  LLM generation failed: %s", result.error)
                return CompileResult(
                    spec_id=spec.spec_id,
                    success=False,
                    impl_path=impl_path,
                    test_path=test_path,
                    attempts=attempt_num,
                    error=f"LLM generation failed: {result.error}",
                )

            # Verify files were written
            if not impl_path.exists():
                code = self._extract_code_from_output(result.output)
                if code:
                    impl_path.write_text(code)
                else:
                    logger.warning("  Implementation file not written")

            if not test_path.exists():
                logger.warning("  Test file not written")
                previous_error = (
                    "Test file was not written. Please write both implementation and test files."
                )
                continue

            # Run tests
            runner = self.test_runner or PytestRunner(working_dir=context.config.root_path)
            test_result = runner.run_test(test_path)

            if test_result.success:
                logger.info("  Tests passed!")
                compile_result = CompileResult(
                    spec_id=spec.spec_id,
                    success=True,
                    impl_path=impl_path,
                    test_path=test_path,
                    attempts=attempt_num,
                )
                context.results.append(compile_result)
                return compile_result

            # Tests failed - prepare for retry
            logger.warning("  Tests failed (exit code %d)", test_result.returncode)
            previous_error = test_result.output

        # All retries exhausted
        logger.error("  All attempts failed for %s", spec.spec_id)
        compile_result = CompileResult(
            spec_id=spec.spec_id,
            success=False,
            impl_path=impl_path,
            test_path=test_path,
            attempts=self.max_retries + 1,
            error=f"Tests failed after {self.max_retries + 1} attempts:\n{previous_error}",
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
