"""Header generation from spec files (Pass 1).

Headers are interface files that define the public API without implementation.
They can be generated independently in any order since they don't depend on
each other's code.
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
from freespec.generator.prompts import PromptBuilder
from freespec.llm.claude_code import ClaudeCodeClient
from freespec.parser.models import SpecFile

if TYPE_CHECKING:
    from freespec.rebuild.detector import RebuildDetector

logger = logging.getLogger("freespec.generator.headers")

MAX_HEADER_REVIEW_RETRIES = 3


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
        language: str,
        detector: RebuildDetector | None = None,
    ) -> GeneratedHeader:
        """Generate a header file for a single spec.

        Args:
            spec: The spec to generate a header for.
            config: Project configuration.
            language: Target language (python, cpp).
            detector: Optional rebuild detector to update manifest.

        Returns:
            The generated header file info.

        Raises:
            HeaderGenerationError: If generation fails.
        """
        output_path = self._get_header_path(spec, config, language)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Set current spec and phase for logging
        self.client.set_current_spec(f"header_{spec.spec_id}")
        self.client.set_current_phase("header")

        prompt = self.prompt_builder.build_header_prompt(
            spec=spec,
            language=language,
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

        # Update manifest if detector provided
        if detector:
            detector.update_manifest_after_header(spec, output_path)

        return GeneratedHeader(
            spec_id=spec.spec_id,
            path=output_path,
            content=content,
        )

    def generate_all_headers(
        self,
        specs: list[SpecFile],
        config: FreeSpecConfig,
        language: str,
        detector: RebuildDetector | None = None,
        num_workers: int = 1,
    ) -> HeaderContext:
        """Generate headers for all specs, forking from a shared instructions session.

        Sends instructions once at the start, then forks for each header
        so each generation starts fresh from the instructions state.

        Args:
            specs: Specs to generate headers for (any order is fine).
            config: Project configuration.
            language: Target language (python, cpp).
            detector: Optional rebuild detector to update manifest.
            num_workers: Number of parallel workers (1 = sequential).

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
        self.client.set_current_phase("instructions")

        instructions = self.prompt_builder.build_header_instructions_prompt(
            language=language,
        )
        result = self.client.generate(instructions)

        if not result.success:
            logger.error("Failed to create header session: %s", result.error)
            # Fall back to independent generation
            logger.warning("Falling back to independent header generation")
            for spec in specs:
                header = self.generate_header(spec, config, language, detector)
                context.headers[spec.spec_id] = header.content
                context.generated_files.append(header)
            return context

        base_session_id = result.session_id
        logger.info("Header session created: %s", base_session_id[:8] + "...")

        # Use parallel or sequential based on num_workers
        if num_workers > 1 and len(specs) > 1:
            return self._generate_headers_parallel(
                specs, config, language, base_session_id, detector, context, num_workers
            )

        # Sequential: Fork for each header (each starts fresh from instructions)
        for spec in tqdm(specs, desc="Headers", unit="spec", disable=len(specs) <= 1):
            header = self._generate_header_forked(spec, config, language, base_session_id, detector)
            context.headers[spec.spec_id] = header.content
            context.generated_files.append(header)

        return context

    def _generate_headers_parallel(
        self,
        specs: list[SpecFile],
        config: FreeSpecConfig,
        language: str,
        base_session_id: str,
        detector: RebuildDetector | None,
        context: HeaderContext,
        num_workers: int,
    ) -> HeaderContext:
        """Generate headers in parallel using ThreadPoolExecutor.

        Args:
            specs: Specs to generate headers for.
            config: Project configuration.
            language: Target language.
            base_session_id: Session ID to fork from.
            detector: Optional rebuild detector.
            context: Header context to populate.
            num_workers: Number of parallel workers.

        Returns:
            Context with all generated headers.

        Raises:
            HeaderGenerationError: If any generation fails.
        """
        results_lock = threading.Lock()
        first_error: HeaderGenerationError | None = None

        def process_spec(spec: SpecFile) -> GeneratedHeader:
            return self._generate_header_forked(
                spec, config, language, base_session_id, detector
            )

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            future_to_spec = {
                executor.submit(process_spec, spec): spec
                for spec in specs
            }

            with tqdm(total=len(specs), desc="Headers", unit="spec") as pbar:
                for future in as_completed(future_to_spec):
                    spec = future_to_spec[future]
                    try:
                        header = future.result()
                        with results_lock:
                            context.headers[spec.spec_id] = header.content
                            context.generated_files.append(header)
                    except HeaderGenerationError as e:
                        if first_error is None:
                            first_error = e
                        logger.error("Failed to generate header for %s: %s", spec.spec_id, e)
                    finally:
                        pbar.update(1)
                        pbar.set_postfix(last=spec.spec_id[:20])

        if first_error is not None:
            raise first_error

        return context

    def _generate_header_forked(
        self,
        spec: SpecFile,
        config: FreeSpecConfig,
        language: str,
        base_session_id: str,
        detector: RebuildDetector | None = None,
    ) -> GeneratedHeader:
        """Generate a header file by forking from the instructions session.

        Each header starts fresh from the instructions state.
        Includes a review step to ensure the header only contains
        what's in the spec's exports section.

        Args:
            spec: The spec to generate a header for.
            config: Project configuration.
            language: Target language (python, cpp).
            base_session_id: Session ID to fork from.
            detector: Optional rebuild detector to update manifest.

        Returns:
            The generated header file info.

        Raises:
            HeaderGenerationError: If generation fails.
        """
        output_path = self._get_header_path(spec, config, language)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Set current spec and phase for logging
        self.client.set_current_spec(f"header_{spec.spec_id}")
        self.client.set_current_phase("header")

        # Build minimal prompt - just references the spec file
        prompt = (
            f"Generate header for: {spec.spec_id}\n\n"
            f"Spec file: {spec.path}\nOutput: {output_path}"
        )

        logger.info("Generating header for %s -> %s", spec.spec_id, output_path)
        result = self.client.fork_session(base_session_id, prompt)
        forked_session_id = result.session_id

        if not result.success:
            raise HeaderGenerationError(
                f"Failed to generate header for {spec.spec_id}: {result.error}"
            )

        # Review loop - verify header contains only what's in exports
        last_failure_reason = "Unknown failure"

        for attempt in range(MAX_HEADER_REVIEW_RETRIES):
            # Verify file exists
            if not output_path.exists():
                logger.warning("  Header file not written, asking to write it...")
                last_failure_reason = "Header file not written"
                self.client.set_current_phase("fix")
                result = self.client.generate(
                    "The header file was not written. "
                    "Please write it to the specified path.",
                    forked_session_id,
                )
                continue

            # Run review
            logger.info(
                "  Reviewing header (attempt %d/%d)...",
                attempt + 1, MAX_HEADER_REVIEW_RETRIES
            )
            self.client.set_current_phase("review")
            review_prompt = self.prompt_builder.build_header_review_prompt(
                spec, output_path
            )
            review_result = self.client.generate(review_prompt, forked_session_id)

            if "REVIEW_PASSED" in review_result.output:
                logger.info("  Header review passed!")
                content = output_path.read_text()

                # Update manifest if detector provided
                if detector:
                    detector.update_manifest_after_header(spec, output_path)

                return GeneratedHeader(
                    spec_id=spec.spec_id,
                    path=output_path,
                    content=content,
                )

            # Review failed - Claude was already told to fix issues in the review prompt
            last_failure_reason = f"Review failed: {review_result.output[:500]}"
            logger.info(
                "  Header review failed (attempt %d/%d)",
                attempt + 1, MAX_HEADER_REVIEW_RETRIES
            )

        # All retries exhausted - return whatever we have but log warning
        logger.warning(
            "  Header review failed after %d attempts for %s: %s",
            MAX_HEADER_REVIEW_RETRIES,
            spec.spec_id,
            last_failure_reason[:200],
        )

        # Still return the header even if review failed - let compilation catch issues
        if output_path.exists():
            content = output_path.read_text()
        else:
            raise HeaderGenerationError(
                f"Header not found at {output_path} after {MAX_HEADER_REVIEW_RETRIES} attempts"
            )

        # Update manifest if detector provided
        if detector:
            detector.update_manifest_after_header(spec, output_path)

        return GeneratedHeader(
            spec_id=spec.spec_id,
            path=output_path,
            content=content,
        )

    def _get_header_ext(self, language: str) -> str:
        """Get header file extension for the target language."""
        if language.lower() in ("cpp", "c++"):
            return ".hpp"
        return ".py"

    def _get_header_path(self, spec: SpecFile, config: FreeSpecConfig, language: str) -> Path:
        """Determine output path for a spec's header file.

        Headers go to out/{language}/src/ directory mirroring spec structure:
        specs/entities/student.spec → out/python/src/entities/student.py

        Args:
            spec: The spec file.
            config: Project configuration.
            language: Target language (python, cpp).

        Returns:
            Path where header file should be written.
        """
        base = config.get_src_path(language)
        ext = self._get_header_ext(language)
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


def load_headers(config: FreeSpecConfig, language: str) -> dict[str, str]:
    """Load all existing header files from the src directory.

    Args:
        config: Project configuration.
        language: Target language (python, cpp).

    Returns:
        Map of spec_id to header content.
    """
    src_dir = config.get_src_path(language)
    headers: dict[str, str] = {}

    if not src_dir.exists():
        return headers

    # Determine extension based on language
    ext = ".py" if language.lower() == "python" else ".hpp"

    for header_file in src_dir.rglob(f"*{ext}"):
        if header_file.name == "__init__.py":
            continue
        # Skip test files
        if header_file.name.startswith("test_"):
            continue

        # Reconstruct spec_id from path
        relative = header_file.relative_to(src_dir)
        category = relative.parent.name if relative.parent.name else ""
        name = header_file.stem

        if category:
            spec_id = f"{category}/{name}"
        else:
            spec_id = name

        headers[spec_id] = header_file.read_text()

    return headers
