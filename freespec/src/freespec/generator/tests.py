"""Test skeleton generation from spec files.

Tests can be generated from either headers (for TDD workflow) or
implementations (for standard workflow).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from freespec.config import FreeSpecConfig
from freespec.generator.prompts import PromptBuilder
from freespec.llm.claude_code import ClaudeCodeClient
from freespec.parser.models import SpecFile

logger = logging.getLogger("freespec.generator.tests")


class SkeletonGenError(Exception):
    """Raised when test generation fails."""


@dataclass
class GeneratedTest:
    """A generated test file."""

    spec_id: str
    path: Path
    content: str


@dataclass
class SkeletonTestContext:
    """Context for tracking test generation state."""

    config: FreeSpecConfig
    generated_files: list[GeneratedTest] = field(default_factory=list)


class SkeletonTestGenerator:
    """Generates test skeleton files from spec files.

    Tests can be generated using either header files (for TDD workflow)
    or implementation files as context.
    """

    def __init__(
        self,
        client: ClaudeCodeClient | None = None,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        """Initialize the test generator.

        Args:
            client: Claude Code client for LLM calls.
            prompt_builder: Builder for generation prompts.
        """
        self.client = client or ClaudeCodeClient()
        self.prompt_builder = prompt_builder or PromptBuilder()

    def generate_test(
        self,
        spec: SpecFile,
        config: FreeSpecConfig,
        source_code: str,
    ) -> GeneratedTest | None:
        """Generate a test file for a single spec.

        Args:
            spec: The spec to generate tests for.
            config: Project configuration.
            source_code: The header or implementation code to test against.

        Returns:
            The generated test file info, or None if no tests in spec.

        Raises:
            SkeletonGenError: If generation fails.
        """
        if not spec.tests.items:
            logger.debug("No tests defined for %s, skipping test generation", spec.spec_id)
            return None

        output_path = self._get_test_path(spec, config)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        prompt = self.prompt_builder.build_test_prompt(
            spec=spec,
            language=config.language,
            output_path=output_path,
            impl_code=source_code,
        )

        logger.info("Generating tests for %s -> %s", spec.spec_id, output_path)
        result = self.client.generate(prompt)

        if not result.success:
            raise SkeletonGenError(f"Failed to generate tests for {spec.spec_id}: {result.error}")

        if output_path.exists():
            content = output_path.read_text()
        else:
            content = self._extract_code_from_output(result.output)
            if content:
                output_path.write_text(content)
            else:
                raise SkeletonGenError(f"Generated test file not found at {output_path}")

        return GeneratedTest(
            spec_id=spec.spec_id,
            path=output_path,
            content=content,
        )

    def generate_all_tests(
        self,
        specs: list[SpecFile],
        config: FreeSpecConfig,
        source_code: dict[str, str],
    ) -> SkeletonTestContext:
        """Generate tests for all specs.

        Args:
            specs: Specs to generate tests for.
            config: Project configuration.
            source_code: Map of spec_id to header or implementation code.

        Returns:
            Context with all generated tests.

        Raises:
            SkeletonGenError: If any generation fails.
        """
        context = SkeletonTestContext(config=config)

        for spec in specs:
            code = source_code.get(spec.spec_id, "")
            test = self.generate_test(spec, config, code)
            if test:
                context.generated_files.append(test)

        return context

    def _get_test_path(self, spec: SpecFile, config: FreeSpecConfig) -> Path:
        """Determine output path for a spec's test file.

        Tests go alongside implementation in the out/ directory:
        specs/entities/student.spec → out/entities/test_student.py

        Args:
            spec: The spec file.
            config: Project configuration.

        Returns:
            Path where test file should be written.
        """
        base = config.get_output_path()
        return base / spec.category / f"test_{spec.name}.py"

    def _extract_code_from_output(self, output: str) -> str | None:
        """Try to extract code from LLM output if file wasn't written.

        Args:
            output: The LLM output text.

        Returns:
            Extracted code or None if not found.
        """
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
