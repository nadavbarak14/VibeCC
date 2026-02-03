"""Implementation generation from spec files (Pass 2).

Implementations are generated using all headers as context, allowing
circular @mentions to be resolved since all interfaces are available.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from freespec.config import FreeSpecConfig
from freespec.generator.prompts import PromptBuilder
from freespec.llm.claude_code import ClaudeCodeClient
from freespec.parser.models import SpecFile

logger = logging.getLogger("freespec.generator.impl")


class ImplementationError(Exception):
    """Raised when implementation generation fails."""


@dataclass
class GeneratedImpl:
    """A generated implementation file."""

    spec_id: str
    path: Path
    content: str


@dataclass
class ImplContext:
    """Context for tracking implementation generation state."""

    config: FreeSpecConfig
    all_headers: dict[str, str]
    generated_code: dict[str, str] = field(default_factory=dict)
    generated_files: list[GeneratedImpl] = field(default_factory=list)


class ImplementationGenerator:
    """Generates implementation files from spec files using headers as context.

    Pass 2 of the two-pass compilation: generates full implementations using
    ALL headers as context. This allows circular @mentions since all interfaces
    are already defined.
    """

    def __init__(
        self,
        client: ClaudeCodeClient | None = None,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        """Initialize the implementation generator.

        Args:
            client: Claude Code client for LLM calls.
            prompt_builder: Builder for generation prompts.
        """
        self.client = client or ClaudeCodeClient()
        self.prompt_builder = prompt_builder or PromptBuilder()

    def generate_impl(
        self,
        spec: SpecFile,
        context: ImplContext,
    ) -> GeneratedImpl:
        """Generate an implementation file for a single spec.

        Args:
            spec: The spec to generate implementation for.
            context: Context with config and all headers.

        Returns:
            The generated implementation file info.

        Raises:
            ImplementationError: If generation fails.
        """
        output_path = self._get_impl_path(spec, context.config)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        prompt = self.prompt_builder.build_impl_prompt(
            spec=spec,
            language=context.config.language,
            output_path=output_path,
            all_headers=context.all_headers,
        )

        logger.info("Generating implementation for %s -> %s", spec.spec_id, output_path)
        result = self.client.generate(prompt)

        if not result.success:
            raise ImplementationError(
                f"Failed to generate implementation for {spec.spec_id}: {result.error}"
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
                raise ImplementationError(
                    f"Generated file not found at {output_path} and couldn't extract from output"
                )

        generated = GeneratedImpl(
            spec_id=spec.spec_id,
            path=output_path,
            content=content,
        )

        # Update context
        context.generated_code[spec.spec_id] = content
        context.generated_files.append(generated)

        return generated

    def generate_all_impls(
        self,
        specs: list[SpecFile],
        config: FreeSpecConfig,
        all_headers: dict[str, str],
    ) -> ImplContext:
        """Generate implementations for all specs.

        Args:
            specs: Specs to generate implementations for (any order).
            config: Project configuration.
            all_headers: Map of all spec_id to their header content.

        Returns:
            Context with all generated implementations.

        Raises:
            ImplementationError: If any generation fails.
        """
        context = ImplContext(config=config, all_headers=all_headers)

        for spec in specs:
            self.generate_impl(spec, context)

        return context

    def _get_impl_path(self, spec: SpecFile, config: FreeSpecConfig) -> Path:
        """Determine output path for a spec's implementation file.

        Args:
            spec: The spec file.
            config: Project configuration.

        Returns:
            Path where implementation file should be written.
        """
        if spec.category == "api":
            base = config.get_output_path("api")
            return base / f"{spec.name}.py"
        else:
            base = config.get_output_path("impl")
            return base / spec.category / f"{spec.name}.py"

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
