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
        lang = language.lower()

        prompt_parts = [
            "Generate a HEADER/INTERFACE file from this FreeSpec specification.",
            "",
            "## Spec Format",
            "- `description:` explains what this component is",
            "- `exports:` lists the PUBLIC API - each line becomes a callable function/method",
            "- `tests:` lists test cases (ignore for header generation)",
            "",
            "## Task",
            "",
            f"Generate a {language.upper()} header/interface file.",
            "This is an INTERFACE only - defines the public API, not implementation.",
            "",
        ]

        if lang in ("cpp", "c++"):
            prompt_parts.extend([
                "Requirements:",
                "- Generate a .hpp header file with proper include guards",
                "- Each export becomes a function or method declaration",
                "- For entities: Create a class with fields and method declarations",
                "- For services: Create a class with pure virtual methods or function declarations",
                "- NO implementation in the header (declarations only)",
                "- Use modern C++ (C++17), std::string, std::optional, std::vector",
                "- Use smart pointers (std::unique_ptr, std::shared_ptr) where appropriate",
                "- Include necessary standard headers (#include <string>, etc.)",
                "- Use a namespace matching the category (e.g., namespace entities { })",
            ])
        else:  # Python
            prompt_parts.extend([
                "Requirements:",
                "- Each export becomes a function or method that can be imported and called",
                "- For entities: Create a dataclass with fields and CRUD methods",
                "- For services: Create a class with method signatures matching exports",
                "- All methods must raise NotImplementedError() - no real implementation",
                "- Include complete type hints for all parameters and return types",
                "- Do NOT import from other generated modules (standalone interface)",
                "- Use standard library types only (datetime, uuid, typing, etc.)",
            ])

        prompt_parts.extend([
            "",
            "## Spec File",
            "",
            f"Category: {spec.category}",
            f"Name: {spec.name}",
            "",
            "```",
            spec.full_content,
            "```",
            "",
            f"Write the generated code to: `{output_path}`",
        ])

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

    def build_compile_prompt(
        self,
        spec: SpecFile,
        language: str,
        impl_path: Path,
        test_path: Path,
        header_paths: dict[str, Path] | None = None,
    ) -> str:
        """Build a prompt for independent compilation (impl + tests together).

        This generates both implementation and tests in a single LLM call.
        Claude Code will iterate internally until tests pass.

        Args:
            spec: The spec file to compile.
            language: Target programming language.
            impl_path: Where the implementation will be written.
            test_path: Where the test file will be written.
            header_paths: Map of @mentioned spec_id to their header file paths.

        Returns:
            Complete prompt for the LLM.
        """
        # Get language-specific instructions
        lang_info = self._get_language_info(language)

        prompt_parts = [
            "INDEPENDENT COMPILATION of a FreeSpec specification.",
            "",
            "## Task",
            "",
            f"Generate BOTH the {language.upper()} implementation AND complete, passing tests.",
            f"Run the tests with {lang_info['test_runner']} and iterate until they pass.",
            "",
            "## Dependencies (Header Files)",
            "",
        ]

        if header_paths:
            prompt_parts.extend(
                [
                    "This module depends on the following interfaces.",
                    "READ these header files to understand the API signatures:",
                    "",
                ]
            )
            for spec_id, path in sorted(header_paths.items()):
                prompt_parts.append(f"- **{spec_id}**: `{path}`")
            prompt_parts.extend(
                [
                    "",
                    "IMPORTANT: Read each header file above to understand:",
                    "- Class names and their constructors",
                    "- Method signatures and return types",
                    "- How to properly instantiate and use these classes",
                    "",
                    f"In your tests, {lang_info['mock_instruction']}",
                    "",
                ]
            )
        else:
            prompt_parts.extend(
                [
                    "This module has no external dependencies (@mentions).",
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
                "## Understanding the Spec Format",
                "",
                "### exports: = The Public API",
                "Each line in `exports:` is something that CAN BE CALLED.",
                "These become the public functions/methods of your implementation.",
                f"Example: 'Create a new student' → {lang_info['example_function']}",
                "",
                "### tests: = Test Cases",
                "Each line describes a test that must pass. Implement tests that verify these.",
                "",
                "## Output Files",
                "",
                f"1. Implementation: `{impl_path}`",
                f"2. Tests: `{test_path}`",
                "",
                "## Requirements",
                "",
                "### Implementation",
                "- Each export becomes a callable function or method",
                f"- {lang_info['impl_requirements']}",
                "- Include dependencies from the header files listed above (if any)",
                "",
                "### Tests",
                f"- {lang_info['test_requirements']}",
                "- Write COMPLETE tests that actually verify the implementation",
                f"- {lang_info['mock_instruction']}",
                f"- Tests must PASS - {lang_info['no_skip_instruction']}",
                "- Test the behavior described in the spec's tests section",
                "",
                "## Instructions",
                "",
                "1. If there are dependencies, READ the header files first to understand the APIs",
                "2. Read the spec - understand what exports need to be implemented",
                "3. Write the implementation exposing all exports as callable API",
                "4. Write tests that call the implementation's API",
                f"5. Run tests with {lang_info['test_command']} and iterate until they pass",
                "6. Write BOTH files to the specified paths",
            ]
        )

        return "\n".join(prompt_parts)

    def build_review_prompt(
        self,
        spec: SpecFile,
        impl_path: Path,
        test_path: Path,
    ) -> str:
        """Build a prompt to review if implementation fulfills the spec.

        This is used after tests pass to verify that all spec requirements
        are actually implemented correctly, not just that the tests pass.

        Args:
            spec: The original spec file.
            impl_path: Path to the generated implementation file.
            test_path: Path to the generated test file.

        Returns:
            Complete review prompt for the LLM.
        """
        prompt_parts = [
            "REVIEW the implementation against the spec.",
            "",
            "## Original Spec",
            "",
            "```spec",
            spec.full_content,
            "```",
            "",
            "## Your Task",
            "",
            "1. Read the implementation at `{impl_path}`".format(impl_path=impl_path),
            "2. Read the tests at `{test_path}`".format(test_path=test_path),
            "3. Check if ALL exports from the spec are properly implemented",
            "4. Check if ALL test cases from the spec are covered",
            "5. Check if the implementation matches the description",
            "",
            "## Response Format",
            "",
            "If everything is correct, respond with exactly:",
            "REVIEW_PASSED",
            "",
            "If there are issues, respond with:",
            "REVIEW_FAILED",
            "- Issue 1: ...",
            "- Issue 2: ...",
            "",
            "Then fix the issues and run the tests again.",
        ]

        return "\n".join(prompt_parts)

    def _get_language_info(self, language: str) -> dict[str, str]:
        """Get language-specific prompt information.

        Args:
            language: Target programming language.

        Returns:
            Dictionary with language-specific instructions.
        """
        lang = language.lower()

        if lang in ("cpp", "c++"):
            return {
                "test_runner": "the compiled test executable",
                "test_command": "g++ to compile, then run the executable",
                "mock_instruction": "use dependency injection or test doubles for mocking",
                "example_function": "`create_student()` or `Student::create()`",
                "impl_requirements": (
                    "Use modern C++ (C++17 or later), proper RAII, and smart pointers"
                ),
                "test_requirements": (
                    "Use Catch2 (single-header) for testing. "
                    "Include catch.hpp and use TEST_CASE/REQUIRE macros"
                ),
                "no_skip_instruction": "no SKIP or disabled tests",
                "header_ext": ".hpp",
                "impl_ext": ".cpp",
                "test_ext": "_test.cpp",
            }
        else:  # Default to Python
            return {
                "test_runner": "pytest",
                "test_command": "pytest",
                "mock_instruction": "mock external dependencies using unittest.mock",
                "example_function": "`create_student()` or `Student.create()`",
                "impl_requirements": "Use proper type hints throughout",
                "test_requirements": "Import and USE the implementation's public API (the exports)",
                "no_skip_instruction": "no @pytest.mark.skip or pending markers",
                "header_ext": ".py",
                "impl_ext": ".py",
                "test_ext": ".py",
            }

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
