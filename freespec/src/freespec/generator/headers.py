"""Header generation from spec files (Pass 1).

Headers are interface files that define the public API without implementation.
They can be generated independently in any order since they don't depend on
each other's code.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from freespec.config import FreeSpecConfig
from freespec.generator.prompts import PromptBuilder
from freespec.llm.claude_code import ClaudeCodeClient
from freespec.parser.models import SpecFile

logger = logging.getLogger("freespec.generator.headers")


class HeaderGenerationError(Exception):
    """Raised when header generation fails."""


@dataclass
class GeneratedHeader:
    """A generated header file."""

    spec_id: str
    path: Path
    content: str


@dataclass
class HeaderContext:
    """Context for tracking header generation state."""

    config: FreeSpecConfig
    headers: dict[str, str] = field(default_factory=dict)
    generated_files: list[GeneratedHeader] = field(default_factory=list)


class HeaderGenerator:
    """Generates header/interface files from spec files.

    Pass 1 of the two-pass compilation: generates interface files for ALL specs
    independently. No ordering is required since headers don't depend on each other.
    """

    def __init__(
        self,
        client: ClaudeCodeClient | None = None,
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        """Initialize the header generator.

        Args:
            client: Claude Code client for LLM calls.
            prompt_builder: Builder for generation prompts.
        """
        self.client = client or ClaudeCodeClient()
        self.prompt_builder = prompt_builder or PromptBuilder()

    def generate_header(
        self,
        spec: SpecFile,
        config: FreeSpecConfig,
    ) -> GeneratedHeader:
        """Generate a header file for a single spec.

        Args:
            spec: The spec to generate a header for.
            config: Project configuration.

        Returns:
            The generated header file info.

        Raises:
            HeaderGenerationError: If generation fails.
        """
        output_path = self._get_header_path(spec, config)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        prompt = self.prompt_builder.build_header_prompt(
            spec=spec,
            language=config.language,
            output_path=output_path,
        )

        logger.info("Generating header for %s -> %s", spec.spec_id, output_path)
        result = self.client.generate(prompt)

        if not result.success:
            raise HeaderGenerationError(
                f"Failed to generate header for {spec.spec_id}: {result.error}"
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
                raise HeaderGenerationError(
                    f"Generated header not found at {output_path} and couldn't extract from output"
                )

        return GeneratedHeader(
            spec_id=spec.spec_id,
            path=output_path,
            content=content,
        )

    def generate_all_headers(
        self,
        specs: list[SpecFile],
        config: FreeSpecConfig,
    ) -> HeaderContext:
        """Generate headers for all specs.

        Args:
            specs: Specs to generate headers for (any order is fine).
            config: Project configuration.

        Returns:
            Context with all generated headers.

        Raises:
            HeaderGenerationError: If any generation fails.
        """
        context = HeaderContext(config=config)

        for spec in specs:
            header = self.generate_header(spec, config)
            context.headers[spec.spec_id] = header.content
            context.generated_files.append(header)

        return context

    def _get_header_path(self, spec: SpecFile, config: FreeSpecConfig) -> Path:
        """Determine output path for a spec's header file.

        Args:
            spec: The spec file.
            config: Project configuration.

        Returns:
            Path where header file should be written.
        """
        base = config.get_output_path("headers")

        if spec.category == "api":
            return base / "api" / f"{spec.name}.py"
        else:
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


def load_headers(config: FreeSpecConfig) -> dict[str, str]:
    """Load all existing header files from the headers directory.

    Args:
        config: Project configuration.

    Returns:
        Map of spec_id to header content.
    """
    headers_dir = config.get_output_path("headers")
    headers: dict[str, str] = {}

    if not headers_dir.exists():
        return headers

    for py_file in headers_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        # Reconstruct spec_id from path
        relative = py_file.relative_to(headers_dir)
        category = relative.parent.name if relative.parent.name else ""
        name = py_file.stem

        if category:
            spec_id = f"{category}/{name}"
        else:
            spec_id = name

        headers[spec_id] = py_file.read_text()

    return headers
