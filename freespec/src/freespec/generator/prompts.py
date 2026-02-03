"""Prompt templates for LLM-based code generation."""

from __future__ import annotations

from pathlib import Path

from freespec.parser.models import SpecFile


class PromptBuilder:
    """Builds prompts for stub generation from spec files.

    Uses freespec docs as context for the LLM to understand the spec format.
    """

    def __init__(self, docs_path: Path | None = None) -> None:
        """Initialize the prompt builder.

        Args:
            docs_path: Path to freespec docs directory. Defaults to package docs.
        """
        if docs_path is None:
            # Default to docs relative to this file's location
            docs_path = Path(__file__).parent.parent.parent.parent / "docs"
        self.docs_path = docs_path

    def load_docs(self) -> str:
        """Load freespec documentation for context.

        Returns:
            Combined documentation content.
        """
        docs = []

        instructions_path = self.docs_path / "instructions.md"
        if instructions_path.exists():
            docs.append("# FreeSpec Instructions\n")
            docs.append(instructions_path.read_text())
            docs.append("\n")

        format_path = self.docs_path / "spec-format.md"
        if format_path.exists():
            docs.append("# FreeSpec Format Reference\n")
            docs.append(format_path.read_text())

        return "\n".join(docs)

    def build_header_prompt(
        self,
        spec: SpecFile,
        language: str,
        output_path: Path,
    ) -> str:
        """Build a prompt for generating header/interface files from a spec.

        This is Pass 1 of the two-pass compilation. Headers are generated
        independently without any dependency context.

        Args:
            spec: The spec file to generate a header for.
            language: Target programming language.
            output_path: Where the header file will be written.

        Returns:
            Complete prompt for the LLM.
        """
        docs = self.load_docs()

        prompt_parts = [
            "You are generating a HEADER/INTERFACE file from a FreeSpec specification.",
            "",
            "## FreeSpec Documentation",
            "",
            docs,
            "",
            "## Task",
            "",
            f"Generate a {language.upper()} header/interface file for the following spec.",
            "This is an INTERFACE file only - defines the public API, not implementation.",
            "",
            "Requirements:",
            "- For entities: Create a dataclass with all described fields and types.",
            "- For services/repositories: Create a class with method signatures.",
            "- All methods must raise NotImplementedError() - no real implementation.",
            "- Include complete type hints for all parameters and return types.",
            "- Include docstrings describing each class and method.",
            "- Do NOT import from other generated modules (this is a standalone interface).",
            "- Use standard library types only (datetime, uuid, typing, etc.).",
            "",
            "## Output File",
            "",
            f"Write the generated code to: {output_path}",
            "",
            "## Spec File",
            "",
            f"Category: {spec.category}",
            f"Name: {spec.name}",
            "",
            "```spec",
            spec.full_content,
            "```",
            "",
            "## Instructions",
            "",
            "1. Read the spec carefully and understand all exports.",
            "2. Define all classes, dataclasses, and method signatures.",
            "3. Every method body should be: raise NotImplementedError()",
            "4. The file must be syntactically valid and importable.",
            "5. Write the file to the specified output path.",
        ]

        return "\n".join(prompt_parts)

    def build_impl_prompt(
        self,
        spec: SpecFile,
        language: str,
        output_path: Path,
        all_headers: dict[str, str] | None = None,
    ) -> str:
        """Build a prompt for generating full implementations from a spec.

        This is Pass 2 of the two-pass compilation. All headers are provided
        as context so the implementation can reference any dependency.

        Args:
            spec: The spec file to generate implementation for.
            language: Target programming language.
            output_path: Where the implementation will be written.
            all_headers: Map of all spec_id to their header file content.

        Returns:
            Complete prompt for the LLM.
        """
        docs = self.load_docs()
        headers_context = self._format_headers_context(all_headers)

        prompt_parts = [
            "You are generating an IMPLEMENTATION file from a FreeSpec specification.",
            "",
            "## FreeSpec Documentation",
            "",
            docs,
            "",
            "## Task",
            "",
            f"Generate {language.upper()} implementation stubs for the following spec file.",
            "Create stub code with proper structure but placeholder implementations.",
            "",
            "For entities: Create a class/dataclass with described fields and signatures.",
            "For services: Create a class with method signatures that match the exports.",
            "For APIs: Create route handlers with the correct HTTP methods and paths.",
            "",
            "Include type hints and docstrings. Methods should raise NotImplementedError().",
            "",
            "## Output File",
            "",
            f"Write the generated code to: {output_path}",
            "",
        ]

        if headers_context:
            prompt_parts.extend(
                [
                    "## Available Interfaces (Headers)",
                    "",
                    "The following interfaces have been generated and can be imported.",
                    "Use these for type hints and understand what dependencies are available.",
                    "",
                    headers_context,
                    "",
                ]
            )

        prompt_parts.extend(
            [
                "## Spec File",
                "",
                f"Category: {spec.category}",
                f"Name: {spec.name}",
                "",
                "```spec",
                spec.full_content,
                "```",
                "",
                "## Instructions",
                "",
                "1. Read the spec carefully and understand all exports and tests.",
                "2. Generate clean, idiomatic code for the target language.",
                "3. Include proper imports for any dependencies mentioned with @mentions.",
                "4. Write stub code - interfaces and signatures with NotImplementedError().",
                "5. Write the file to the specified output path.",
            ]
        )

        return "\n".join(prompt_parts)

    def build_stub_prompt(
        self,
        spec: SpecFile,
        language: str,
        output_path: Path,
        dependency_code: dict[str, str] | None = None,
    ) -> str:
        """Build a prompt for generating code stubs from a spec.

        DEPRECATED: Use build_header_prompt for Pass 1 or build_impl_prompt for Pass 2.

        Args:
            spec: The spec file to generate stubs for.
            language: Target programming language.
            output_path: Where the generated code will be written.
            dependency_code: Map of dependency spec_id to their generated code.

        Returns:
            Complete prompt for the LLM.
        """
        docs = self.load_docs()
        dependency_context = self._format_dependency_code(dependency_code)

        prompt_parts = [
            "You are generating code stubs from a FreeSpec specification file.",
            "",
            "## FreeSpec Documentation",
            "",
            docs,
            "",
            "## Task",
            "",
            f"Generate {language.upper()} code stubs for the following spec file.",
            "Create only the interface/stub code - not full implementations.",
            "",
            "For entities: Create a class/dataclass with described fields and signatures.",
            "For services: Create a class with method signatures that match the exports.",
            "For APIs: Create route handlers with the correct HTTP methods and paths.",
            "",
            "Include type hints and docstrings. Methods should raise NotImplementedError().",
            "",
            "## Output File",
            "",
            f"Write the generated code to: {output_path}",
            "",
        ]

        if dependency_context:
            prompt_parts.extend(
                [
                    "## Already Generated Dependencies",
                    "",
                    "The following code has been generated for specs this one depends on.",
                    "Use these for import references and type hints.",
                    "",
                    dependency_context,
                    "",
                ]
            )

        prompt_parts.extend(
            [
                "## Spec File",
                "",
                f"Category: {spec.category}",
                f"Name: {spec.name}",
                "",
                "```spec",
                spec.full_content,
                "```",
                "",
                "## Instructions",
                "",
                "1. Read the spec carefully and understand all exports and tests.",
                "2. Generate clean, idiomatic code for the target language.",
                "3. Include proper imports for any dependencies.",
                "4. Write ONLY stub code - interfaces and signatures, not implementations.",
                "5. Write the file to the specified output path.",
            ]
        )

        return "\n".join(prompt_parts)

    def build_test_prompt(
        self,
        spec: SpecFile,
        language: str,
        output_path: Path,
        impl_code: str,
    ) -> str:
        """Build a prompt for generating test skeletons from a spec.

        Args:
            spec: The spec file to generate tests for.
            language: Target programming language.
            output_path: Where the test file will be written.
            impl_code: The generated implementation code to test.

        Returns:
            Complete prompt for the LLM.
        """
        docs = self.load_docs()

        prompt_parts = [
            "You are generating test skeletons from a FreeSpec specification file.",
            "",
            "## FreeSpec Documentation",
            "",
            docs,
            "",
            "## Task",
            "",
            f"Generate {language.upper()} test skeletons for the following spec file.",
            "Create test function signatures for each test case in the 'tests:' section.",
            "Tests should be marked as pending/skipped - they're skeletons, not implementations.",
            "",
            "## Output File",
            "",
            f"Write the test file to: {output_path}",
            "",
            "## Implementation Code",
            "",
            "This is the stub code being tested:",
            "",
            "```python",
            impl_code,
            "```",
            "",
            "## Spec File",
            "",
            f"Category: {spec.category}",
            f"Name: {spec.name}",
            "",
            "```spec",
            spec.full_content,
            "```",
            "",
            "## Instructions",
            "",
            "1. Create a test function for each item in the 'tests:' section.",
            "2. Name test functions descriptively based on the test description.",
            "3. Mark each test as skipped/pending (e.g., @pytest.mark.skip in Python).",
            "4. Include a comment in each test explaining what it should verify.",
            "5. Write the file to the specified output path.",
        ]

        return "\n".join(prompt_parts)

    def _format_dependency_code(self, dependency_code: dict[str, str] | None) -> str:
        """Format dependency code for inclusion in prompt.

        Args:
            dependency_code: Map of spec_id to code content.

        Returns:
            Formatted string with all dependency code.
        """
        if not dependency_code:
            return ""

        parts = []
        for spec_id, code in sorted(dependency_code.items()):
            parts.append(f"### {spec_id}")
            parts.append("")
            parts.append("```python")
            parts.append(code)
            parts.append("```")
            parts.append("")

        return "\n".join(parts)

    def _format_headers_context(self, all_headers: dict[str, str] | None) -> str:
        """Format all headers for inclusion in implementation prompt.

        Args:
            all_headers: Map of spec_id to header file content.

        Returns:
            Formatted string with all header code.
        """
        if not all_headers:
            return ""

        parts = []
        for spec_id, code in sorted(all_headers.items()):
            parts.append(f"### {spec_id} (header)")
            parts.append("")
            parts.append("```python")
            parts.append(code)
            parts.append("```")
            parts.append("")

        return "\n".join(parts)
