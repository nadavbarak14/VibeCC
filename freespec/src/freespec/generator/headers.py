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

        # Set current spec for logging
        self.client.set_current_spec(f"header_{spec.spec_id}")

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
        """Generate headers for all specs, forking from a shared instructions session.

        Sends instructions once at the start, then forks for each header
        so each generation starts fresh from the instructions state.

        Args:
            specs: Specs to generate headers for (any order is fine).
            config: Project configuration.

        Returns:
            Context with all generated headers.

        Raises:
            HeaderGenerationError: If any generation fails.
        """
        context = HeaderContext(config=config)

        if not specs:
            return context

        # Send instructions once at the start
        logger.info("Creating header generation session with instructions...")
        self.client.set_current_spec("_header_instructions")

        instructions = self.prompt_builder.build_header_instructions_prompt(
            language=config.language,
        )
        result = self.client.generate(instructions)

        if not result.success:
            logger.error("Failed to create header session: %s", result.error)
            # Fall back to independent generation
            logger.warning("Falling back to independent header generation")
            for spec in specs:
                header = self.generate_header(spec, config)
                context.headers[spec.spec_id] = header.content
                context.generated_files.append(header)
            return context

        base_session_id = result.session_id
        logger.info("Header session created: %s", base_session_id[:8] + "...")

        # Fork for each header (each starts fresh from instructions)
        for spec in specs:
            header = self._generate_header_forked(spec, config, base_session_id)
            context.headers[spec.spec_id] = header.content
            context.generated_files.append(header)

        return context

    def _generate_header_forked(
        self,
        spec: SpecFile,
        config: FreeSpecConfig,
        base_session_id: str,
    ) -> GeneratedHeader:
        """Generate a header file by forking from the instructions session.

        Each header starts fresh from the instructions state.

        Args:
            spec: The spec to generate a header for.
            config: Project configuration.
            base_session_id: Session ID to fork from.

        Returns:
            The generated header file info.

        Raises:
            HeaderGenerationError: If generation fails.
        """
        output_path = self._get_header_path(spec, config)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Set current spec for logging
        self.client.set_current_spec(f"header_{spec.spec_id}")

        # Build minimal prompt - just references the spec file
        prompt = f"Generate header for: {spec.spec_id}\n\nSpec file: {spec.path}\nOutput: {output_path}"

        logger.info("Generating header for %s -> %s", spec.spec_id, output_path)
        result = self.client.fork_session(base_session_id, prompt)

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

    def _get_header_ext(self, config: FreeSpecConfig) -> str:
        """Get header file extension for the target language."""
        lang = config.language.lower()
        if lang in ("cpp", "c++"):
            return ".hpp"
        return ".py"

    def _get_header_path(self, spec: SpecFile, config: FreeSpecConfig) -> Path:
        """Determine output path for a spec's header file.

        Headers go to out/src/ directory mirroring spec structure:
        specs/entities/student.spec → out/src/entities/student.py

        Args:
            spec: The spec file.
            config: Project configuration.

        Returns:
            Path where header file should be written.
        """
        base = config.get_src_path()
        ext = self._get_header_ext(config)
        return base / spec.category / f"{spec.name}{ext}"

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
    """Load all existing header files from the src directory.

    Args:
        config: Project configuration.

    Returns:
        Map of spec_id to header content.
    """
    src_dir = config.get_src_path()
    headers: dict[str, str] = {}

    if not src_dir.exists():
        return headers

    for py_file in src_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        # Skip test files
        if py_file.name.startswith("test_"):
            continue

        # Reconstruct spec_id from path
        relative = py_file.relative_to(src_dir)
        category = relative.parent.name if relative.parent.name else ""
        name = py_file.stem

        if category:
            spec_id = f"{category}/{name}"
        else:
            spec_id = name

        headers[spec_id] = py_file.read_text()

    return headers
