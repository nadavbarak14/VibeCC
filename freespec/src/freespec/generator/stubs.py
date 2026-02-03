"""Stub generation from spec files."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from freespec.config import FreeSpecConfig
from freespec.generator.prompts import PromptBuilder
from freespec.llm.claude_code import ClaudeCodeClient
from freespec.parser.models import SpecFile

logger = logging.getLogger("freespec.generator")


class GenerationError(Exception):
    """Raised when code generation fails."""


@dataclass
class GeneratedFile:
    """A generated code file."""

    spec_id: str
    path: Path
    content: str
    is_test: bool = False


@dataclass
class GenerationContext:
    """Context for tracking generation state."""

    config: FreeSpecConfig
    generated_code: dict[str, str] = field(default_factory=dict)
    generated_files: list[GeneratedFile] = field(default_factory=list)


class StubGenerator:
    """Generates code stubs from spec files using LLM.

    Processes specs in dependency order and accumulates generated code
    for use as context in subsequent generations.
    """

    def __init__(
        self,
        client: ClaudeCodeClient | None = None,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        """Initialize the stub generator.

        Args:
            client: Claude Code client for LLM calls.
            prompt_builder: Builder for generation prompts.
        """
        self.client = client or ClaudeCodeClient()
        self.prompt_builder = prompt_builder or PromptBuilder()

    def generate_stub(
        self,
        spec: SpecFile,
        context: GenerationContext,
    ) -> GeneratedFile:
        """Generate a stub for a single spec file.

        Args:
            spec: The spec to generate code for.
            context: Generation context with config and prior code.

        Returns:
            The generated file info.

        Raises:
            GenerationError: If generation fails.
        """
        output_path = self._get_output_path(spec, context.config)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Gather dependency code
        dependency_code = {}
        for dep_id in spec.mentions:
            if dep_id in context.generated_code:
                dependency_code[dep_id] = context.generated_code[dep_id]

        prompt = self.prompt_builder.build_stub_prompt(
            spec=spec,
            language=context.config.language,
            output_path=output_path,
            dependency_code=dependency_code,
        )

        logger.info("Generating stub for %s -> %s", spec.spec_id, output_path)
        result = self.client.generate(prompt)

        if not result.success:
            raise GenerationError(
                f"Failed to generate stub for {spec.spec_id}: {result.error}"
            )

        # Read the generated file content
        if output_path.exists():
            content = output_path.read_text()
        else:
            # LLM might have written content differently, extract from output
            content = self._extract_code_from_output(result.output)
            if content:
                output_path.write_text(content)
            else:
                raise GenerationError(
                    f"Generated file not found at {output_path} and couldn't extract from output"
                )

        generated = GeneratedFile(
            spec_id=spec.spec_id,
            path=output_path,
            content=content,
        )

        # Update context
        context.generated_code[spec.spec_id] = content
        context.generated_files.append(generated)

        return generated

    def generate_test(
        self,
        spec: SpecFile,
        context: GenerationContext,
    ) -> GeneratedFile | None:
        """Generate test skeleton for a spec file.

        Args:
            spec: The spec to generate tests for.
            context: Generation context with config and generated code.

        Returns:
            The generated test file info, or None if no tests in spec.

        Raises:
            GenerationError: If generation fails.
        """
        if not spec.tests.items:
            logger.debug("No tests defined for %s, skipping test generation", spec.spec_id)
            return None

        output_path = self._get_test_path(spec, context.config)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        impl_code = context.generated_code.get(spec.spec_id, "")

        prompt = self.prompt_builder.build_test_prompt(
            spec=spec,
            language=context.config.language,
            output_path=output_path,
            impl_code=impl_code,
        )

        logger.info("Generating tests for %s -> %s", spec.spec_id, output_path)
        result = self.client.generate(prompt)

        if not result.success:
            raise GenerationError(
                f"Failed to generate tests for {spec.spec_id}: {result.error}"
            )

        if output_path.exists():
            content = output_path.read_text()
        else:
            content = self._extract_code_from_output(result.output)
            if content:
                output_path.write_text(content)
            else:
                raise GenerationError(
                    f"Generated test file not found at {output_path}"
                )

        generated = GeneratedFile(
            spec_id=spec.spec_id,
            path=output_path,
            content=content,
            is_test=True,
        )
        context.generated_files.append(generated)

        return generated

    def generate_all(
        self,
        specs: list[SpecFile],
        config: FreeSpecConfig,
        generate_tests: bool = True,
    ) -> GenerationContext:
        """Generate stubs for all specs in order.

        Args:
            specs: Specs in dependency order (dependencies first).
            config: Project configuration.
            generate_tests: Whether to also generate test skeletons.

        Returns:
            Context with all generated files.

        Raises:
            GenerationError: If any generation fails.
        """
        context = GenerationContext(config=config)

        for spec in specs:
            self.generate_stub(spec, context)

            if generate_tests:
                self.generate_test(spec, context)

        return context

    def _get_output_path(self, spec: SpecFile, config: FreeSpecConfig) -> Path:
        """Determine output path for a spec's generated code.

        Args:
            spec: The spec file.
            config: Project configuration.

        Returns:
            Path where generated code should be written.
        """
        if spec.category == "api":
            base = config.get_output_path("api")
        else:
            base = config.get_output_path("impl")
            base = base / spec.category

        return base / f"{spec.name}.py"

    def _get_test_path(self, spec: SpecFile, config: FreeSpecConfig) -> Path:
        """Determine output path for a spec's test file.

        Args:
            spec: The spec file.
            config: Project configuration.

        Returns:
            Path where test file should be written.
        """
        base = config.get_output_path("tests")
        return base / spec.category / f"test_{spec.name}.py"

    def _extract_code_from_output(self, output: str) -> str | None:
        """Try to extract code from LLM output if file wasn't written.

        Args:
            output: The LLM output text.

        Returns:
            Extracted code or None if not found.
        """
        # Look for Python code blocks
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
