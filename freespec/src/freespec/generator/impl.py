"""Implementation generation from spec files (Pass 2).

Implementations are generated using all headers as context, allowing
circular @mentions to be resolved since all interfaces are available.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from tqdm import tqdm

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
        language: str,
    ) -> GeneratedImpl:
        """Generate an implementation file for a single spec.

        Args:
            spec: The spec to generate implementation for.
            context: Context with config and all headers.
            language: Target language (python, cpp).

        Returns:
            The generated implementation file info.

        Raises:
            ImplementationError: If generation fails.
        """
        output_path = self._get_impl_path(spec, context.config, language)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        prompt = self.prompt_builder.build_impl_prompt(
            spec=spec,
            language=language,
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
        language: str,
        num_workers: int = 1,
    ) -> ImplContext:
        """Generate implementations for all specs.

        Args:
            specs: Specs to generate implementations for (any order).
            config: Project configuration.
            all_headers: Map of all spec_id to their header content.
            language: Target language (python, cpp).
            num_workers: Number of parallel workers (1 = sequential).

        Returns:
            Context with all generated implementations.

        Raises:
            ImplementationError: If any generation fails.
        """
        context = ImplContext(config=config, all_headers=all_headers)

        if not specs:
            return context

        if num_workers > 1 and len(specs) > 1:
            return self._generate_impls_parallel(specs, context, language, num_workers)

        for spec in tqdm(specs, desc="Implementations", unit="spec", disable=len(specs) <= 1):
            self.generate_impl(spec, context, language)

        return context

    def _generate_impls_parallel(
        self,
        specs: list[SpecFile],
        context: ImplContext,
        language: str,
        num_workers: int,
    ) -> ImplContext:
        """Generate implementations in parallel using ThreadPoolExecutor.

        Args:
            specs: Specs to generate implementations for.
            context: Implementation context to populate.
            language: Target language.
            num_workers: Number of parallel workers.

        Returns:
            Context with all generated implementations.

        Raises:
            ImplementationError: If any generation fails.
        """
        results_lock = threading.Lock()
        first_error: ImplementationError | None = None

        def process_spec(spec: SpecFile) -> GeneratedImpl:
            return self.generate_impl(spec, context, language)

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            future_to_spec = {executor.submit(process_spec, spec): spec for spec in specs}

            with tqdm(total=len(specs), desc="Implementations", unit="spec") as pbar:
                for future in as_completed(future_to_spec):
                    spec = future_to_spec[future]
                    try:
                        impl = future.result()
                        with results_lock:
                            context.generated_code[spec.spec_id] = impl.content
                            context.generated_files.append(impl)
                    except ImplementationError as e:
                        if first_error is None:
                            first_error = e
                        logger.error("Failed to generate impl for %s: %s", spec.spec_id, e)
                    finally:
                        pbar.update(1)
                        pbar.set_postfix(last=spec.spec_id[:20])

        if first_error is not None:
            raise first_error

        return context

    def _filter_headers_for_spec(
        self,
        spec: SpecFile,
        all_headers: dict[str, str],
    ) -> dict[str, str]:
        """Filter headers to only those @mentioned by the spec.

        For independent compilation, each file only sees the interfaces
        it explicitly depends on via @mentions.

        Args:
            spec: The spec file being compiled.
            all_headers: Map of all spec_id to their header content.

        Returns:
            Map containing only the headers for @mentioned specs.
        """
        return {m: all_headers[m] for m in spec.mentions if m in all_headers}

    def _get_impl_path(self, spec: SpecFile, config: FreeSpecConfig, language: str) -> Path:
        """Determine output path for a spec's implementation file.

        Implementations go to out/{language}/src/ directory:
        specs/entities/student.spec → out/python/src/entities/student.py

        Args:
            spec: The spec file.
            config: Project configuration.
            language: Target language (python, cpp).

        Returns:
            Path where implementation file should be written.
        """
        ext = ".py" if language.lower() == "python" else ".cpp"
        base = config.get_src_path(language)
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
