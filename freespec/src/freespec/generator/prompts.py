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
            prompt_parts.extend(
                [
                    "Requirements:",
                    "- Generate a .hpp header file with proper include guards",
                    "- Each export becomes a function or method declaration",
                    "- For entities: Create a class with fields and method declarations",
                    "- For services: Create a class with pure virtual methods",
                    "- NO implementation in the header (declarations only)",
                    "- Use modern C++ (C++17), std::string, std::optional, std::vector",
                    "- Use smart pointers (std::unique_ptr, std::shared_ptr) where appropriate",
                    "- Include necessary standard headers (#include <string>, etc.)",
                    "- Use a namespace matching the category (e.g., namespace entities { })",
                ]
            )
        else:  # Python
            prompt_parts.extend(
                [
                    "## CRITICAL RULES - FOLLOW EXACTLY",
                    "",
                    "1. **NO ABSTRACT CLASSES**: Never use ABC, abstractmethod, Protocol",
                    "2. **ONLY EXPORTS**: Include ONLY what's in `exports:` - nothing else",
                    "3. **CONCRETE CLASSES**: All classes concrete with NotImplementedError()",
                    "4. **NO EXTRA CODE**: No helper classes, utility functions, extra types",
                    "",
                    "## Requirements:",
                    "- Each export becomes a function or method that can be imported and called",
                    "- For entities: Create a dataclass with fields and methods from exports",
                    "- For services: Create a class with method signatures matching exports ONLY",
                    "- All methods must raise NotImplementedError() - NO real implementation",
                    "- Include complete type hints for all parameters and return types",
                    "- Do NOT import from other generated modules (standalone interface)",
                    "- Use standard library types only (datetime, uuid, typing, etc.)",
                    "",
                    "## What TO Include:",
                    "- Classes/functions explicitly named in exports",
                    "- Parameters and return types for exported functions",
                    "- Fields for dataclasses if entity type",
                    "- Enums if explicitly needed by exports",
                    "- Docstrings for exported items",
                    "",
                    "## What NOT TO Include:",
                    "- ABC, abstractmethod, Protocol - NEVER",
                    "- Helper classes not in exports",
                    "- Utility functions not in exports",
                    "- TypedDicts unless explicitly needed",
                    "- Extra type aliases",
                ]
            )

        prompt_parts.extend(
            [
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
            ]
        )

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
        dependency_paths: dict[str, Path] | None = None,
    ) -> str:
        """Build a prompt for compiling a spec (fill in stub + create tests).

        The stub file already exists at impl_path with NotImplementedError().
        This prompt instructs the LLM to fill in the bodies and write tests.

        Args:
            spec: The spec file to compile.
            language: Target programming language.
            impl_path: Path to the existing stub file (modify in-place).
            test_path: Where to write the test file.
            dependency_paths: Map of @mentioned spec_id to their file paths.

        Returns:
            Complete prompt for the LLM.
        """
        # Get language-specific instructions
        lang_info = self._get_language_info(language)

        # Build import example based on impl_path
        # e.g., out/src/entities/student.py -> from src.entities.student import ...
        rel_parts = impl_path.parts
        if "src" in rel_parts:
            src_idx = rel_parts.index("src")
            module_parts = rel_parts[src_idx:-1] + (impl_path.stem,)
            import_example = ".".join(module_parts)
        else:
            import_example = f"src.{spec.category}.{spec.name}"

        prompt_parts = [
            "COMPILE a FreeSpec specification into working code.",
            "",
            "## Task",
            "",
            "You are implementing an EXISTING stub file. The stub already defines:",
            "- All public classes and functions with signatures",
            "- All fields for dataclasses",
            "- All type hints",
            "- Methods that raise NotImplementedError()",
            "",
            "Your job is to:",
            f"1. READ the stub file at `{impl_path}`",
            "2. READ any dependency files this module uses",
            "3. Replace NotImplementedError() with working implementations",
            "4. Write tests that verify the implementation",
            f"5. Run tests with {lang_info['test_runner']} and iterate until they pass",
            "",
            "## CRITICAL CONSTRAINTS - PRESERVE THE STUB EXACTLY",
            "",
            "The stub file defines the PUBLIC API. You MUST NOT change it:",
            "",
            "- DO NOT add new classes, functions, or constants (except private _helpers)",
            "- DO NOT remove any existing classes, functions, or constants",
            "- DO NOT modify function signatures, parameters, or return types",
            "- DO NOT change type hints or field definitions",
            "- DO NOT rename anything",
            "- ONLY replace NotImplementedError() bodies with working code",
            "",
            "If you add `class Foo` that wasn't in the stub -> VIOLATION",
            "If you remove `def bar()` that was in the stub -> VIOLATION",
            "If you change `def foo(x: int)` to `def foo(x: str)` -> VIOLATION",
            "If you add a field that wasn't in the stub -> VIOLATION",
            "",
            "Private helpers (names starting with _) ARE allowed.",
            "",
        ]

        if dependency_paths:
            prompt_parts.extend(
                [
                    "## CRITICAL: Read Dependency Headers First",
                    "",
                    "This module @mentions dependencies. **YOU MUST READ EACH DEPENDENCY FILE**",
                    "before using it. Do NOT guess what fields or methods they have.",
                    "",
                    "**NEVER GUESS:**",
                    "- What fields a dependency's class has",
                    "- What parameters a dependency's function takes",
                    "- What methods are available on a dependency's class",
                    "",
                    "**ALWAYS READ** the dependency file to see the exact API.",
                    "",
                    "Dependencies to READ:",
                    "",
                ]
            )
            for spec_id, path in sorted(dependency_paths.items()):
                # Convert path to import: out/src/entities/student.py -> src.entities.student
                dep_parts = path.parts
                if "src" in dep_parts:
                    src_idx = dep_parts.index("src")
                    dep_module = ".".join(dep_parts[src_idx:-1] + (path.stem,))
                else:
                    dep_module = f"src.{spec_id.replace('/', '.')}"
                prompt_parts.append(
                    f"- **{spec_id}**: READ `{path}` → `from {dep_module} import ...`"
                )
            prompt_parts.append("")
            prompt_parts.append("If you use a field that doesn't exist in dependency → FAILS")
            prompt_parts.append("")

        prompt_parts.extend(
            [
                "## Existing Stub File",
                "",
                f"Read and modify: `{impl_path}`",
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
                "## Output Files",
                "",
                f"1. Implementation (modify in-place): `{impl_path}`",
                f"2. Tests (create new): `{test_path}`",
                "",
                "## Requirements",
                "",
                "### Implementation",
                "- Read the existing stub file first",
                "- Keep all existing signatures, types, and docstrings",
                "- Only fill in method/function bodies",
                "- Use normal Python imports for dependencies",
                "  (e.g., `from src.entities.student import Student`)",
                f"- {lang_info['impl_requirements']}",
                "",
                "### Tests",
                f"- Import from: `from {import_example} import ...`",
                "- Write COMPLETE tests that verify the implementation",
                "- DO NOT mock the module under test",
                "- DO NOT mock @mentioned dependencies - use real imports",
                "- ONLY mock external services (DB, network, filesystem)",
                f"- Tests must PASS - {lang_info['no_skip_instruction']}",
                "- Test the behavior described in the spec's tests section",
                "",
                "**Why no mocking dependencies?** If you use a field that doesn't exist",
                "on a dependency, the test will fail with AttributeError. This catches bugs.",
                "",
                "## Instructions",
                "",
                "1. **READ the header file first** - this is REQUIRED, never skip it",
                "2. Note the exact class fields, function signatures, and types",
                "3. If there are dependencies, READ them and use normal imports",
                "4. Fill in implementation bodies (replace NotImplementedError)",
                "5. Write tests that import from the module",
                f"6. Run tests with {lang_info['test_command']} and iterate until they pass",
                "",
                "**REMINDER: Never guess fields or signatures. Always read the header first.**",
            ]
        )

        return "\n".join(prompt_parts)

    def build_review_prompt(
        self,
        spec: SpecFile,
        impl_path: Path,
        test_path: Path | None,
        original_exports: set[str] | None = None,
    ) -> str:
        """Build a prompt to review if implementation fulfills the spec.

        This is used after tests pass to verify that all spec requirements
        are actually implemented correctly, not just that the tests pass.

        Args:
            spec: The original spec file.
            impl_path: Path to the generated implementation file.
            test_path: Path to the generated test file, or None if no tests.
            original_exports: Set of public exports from the original stub.

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
        ]

        # Add export validation section if exports are provided
        if original_exports:
            prompt_parts.extend(
                [
                    "## CRITICAL: EXPORT VALIDATION",
                    "",
                    "The ORIGINAL HEADER had these public exports:",
                    "",
                ]
            )
            for export in sorted(original_exports):
                prompt_parts.append(f"- `{export}`")
            prompt_parts.extend(
                [
                    "",
                    "**The implementation MUST have EXACTLY these same exports.**",
                    "",
                    "Check for violations:",
                    "1. ADDED exports (classes/functions in impl but NOT in list above) -> FAIL",
                    "2. REMOVED exports (items in list above but NOT in impl) -> FAIL",
                    "3. CHANGED signatures (different parameters or return types) -> FAIL",
                    "",
                    "Private names (starting with `_`) are allowed and don't count as exports.",
                    "",
                    "If exports don't match, report REVIEW_FAILED and FIX it",
                    "to match original exports. Do NOT add new public classes/functions.",
                    "",
                ]
            )

        if test_path:
            prompt_parts.extend(
                [
                    "## Your Task",
                    "",
                    f"1. Read the implementation at `{impl_path}`",
                    f"2. Read the tests at `{test_path}`",
                    "3. Check if ALL exports from the spec are properly implemented",
                    "4. Check if ALL test cases from the spec are covered",
                    "5. Check if the implementation matches the description",
                ]
            )
            next_step = 6
        else:
            prompt_parts.extend(
                [
                    "## Your Task",
                    "",
                    f"1. Read the implementation at `{impl_path}`",
                    "2. Check if ALL exports from the spec are properly implemented",
                    "3. Check if the implementation matches the description",
                ]
            )
            next_step = 4

        if original_exports:
            prompt_parts.append(
                f"{next_step}. Verify that public exports match the original stub exactly"
            )

        prompt_parts.extend(
            [
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
        )

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
                "mock_instruction": (
                    "mock ONLY external dependencies (DB, network) using unittest.mock"
                ),
                "example_function": "`create_student()` or `Student.create()`",
                "impl_requirements": "Use proper type hints throughout",
                "test_requirements": (
                    "Import directly from the implementation file "
                    "(e.g., from src.entities.student import Student)"
                ),
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

    def build_compile_instructions_prompt(self, language: str) -> str:
        """Build the instructions prompt for compilation.

        This is sent once at the start of a compilation session.
        It contains FreeSpec documentation and language-specific instructions,
        but NOT the specs or headers (Claude will read files as needed).

        Args:
            language: Target programming language.

        Returns:
            Instructions prompt to send once at session start.
        """
        docs = self.load_docs()
        lang_info = self._get_language_info(language)

        prompt_parts = [
            "# FreeSpec Compilation Instructions",
            "",
            "You are compiling FreeSpec specifications into working code.",
            "I will give you specs to compile one at a time. Read files as needed.",
            "",
            "## FreeSpec Documentation",
            "",
            docs,
            "",
            "## Target Language",
            "",
            f"Language: {language.upper()}",
            f"Test runner: {lang_info['test_runner']}",
            f"Test command: {lang_info['test_command']}",
            f"Implementation requirements: {lang_info['impl_requirements']}",
            "",
            "## CRITICAL: Never Guess - Always Read Files First",
            "",
            "**NEVER GUESS** what fields a class has or what methods are available.",
            "**ALWAYS READ** the actual files to see the exact structure.",
            "",
            "Before using ANY class or function, READ its source file to know:",
            "- What fields/attributes it has",
            "- What methods are available",
            "- What parameters each method takes",
            "- What types are expected",
            "",
            "If you use a field that doesn't exist → AttributeError → FAILURE",
            "If you call a method with wrong parameters → TypeError → FAILURE",
            "",
            "## Compilation Workflow",
            "",
            "For each spec I give you:",
            "",
            "1. READ the stub file to see the API you're implementing",
            "2. READ the spec file to understand the behavior",
            "3. **READ any @mentioned dependencies** - know their exact API",
            "4. Replace NotImplementedError() with working implementations",
            "5. Write tests that verify the spec's test cases",
            f"6. Run tests with {lang_info['test_command']} and iterate until all pass",
            "",
            "## Constraints",
            "",
            "- Do NOT add new public exports (classes, functions, constants)",
            "- Do NOT modify function signatures or type hints",
            "- Do NOT guess what fields/methods exist - READ the files",
            "- ONLY replace NotImplementedError() with working code",
            "- Private helpers (_prefix) ARE allowed",
            "",
            "Ready for compilation tasks.",
        ]

        return "\n".join(prompt_parts)

    def build_header_review_prompt(
        self,
        spec: SpecFile,
        header_path: Path,
    ) -> str:
        """Build a prompt to review if header correctly represents the spec.

        This is used after header generation to verify that:
        - Only exports from the spec are included
        - No abstract classes or unnecessary code
        - Everything is useful and minimal

        Args:
            spec: The original spec file.
            header_path: Path to the generated header file.

        Returns:
            Complete review prompt for the LLM.
        """
        # Extract expected exports from spec
        exports_list = spec.exports.items if spec.exports.items else []

        prompt_parts = [
            "REVIEW the generated header against the spec.",
            "",
            "## Original Spec",
            "",
            "```spec",
            spec.full_content,
            "```",
            "",
            "## Expected Exports",
            "",
            "The header should contain ONLY these exports:",
            "",
        ]

        for export in exports_list:
            prompt_parts.append(f"- {export}")

        prompt_parts.extend(
            [
                "",
                "## Review Criteria",
                "",
                "Check the header file for these FAILURES:",
                "",
                "1. **ABSTRACT CLASSES**: ABC, abstractmethod, Protocol - FAIL",
                "2. **EXTRA EXPORTS**: Classes/functions NOT in the exports list - FAIL",
                "3. **MISSING EXPORTS**: Exports from spec not in header - FAIL",
                "4. **NON-STUB METHODS**: Methods with real impl (not NotImplementedError) - FAIL",
                "5. **EXTRA TYPES**: TypedDicts, Protocols, helper classes not needed - FAIL",
                "",
                "## Your Task",
                "",
                f"1. Read the header at `{header_path}`",
                "2. Compare against the exports list above",
                "3. Check for abstract classes or unnecessary code",
                "",
                "## Response Format",
                "",
                "If the header is correct, respond with exactly:",
                "REVIEW_PASSED",
                "",
                "If there are issues, respond with:",
                "REVIEW_FAILED",
                "- Issue 1: ...",
                "- Issue 2: ...",
                "",
                "Then FIX the issues by rewriting the header file.",
            ]
        )

        return "\n".join(prompt_parts)

    def build_header_instructions_prompt(self, language: str) -> str:
        """Build the instructions prompt for header generation.

        This is sent once at the start of a header generation session.
        It contains FreeSpec documentation and language-specific instructions.

        Args:
            language: Target programming language.

        Returns:
            Instructions prompt to send once at session start.
        """
        docs = self.load_docs()
        lang = language.lower()

        if lang in ("cpp", "c++"):
            lang_instructions = """
## Language: C++

Generate .hpp header files with:
- Proper include guards
- Function/method declarations (no implementation)
- Class definitions with fields and method declarations
- Modern C++ (C++17), std::string, std::optional, std::vector
- Smart pointers where appropriate
- Namespaces matching the category
"""
        else:
            lang_instructions = """
## Language: Python

Generate Python stub files with:
- Function/method signatures with complete type hints
- Classes with all fields and method signatures
- All methods raise NotImplementedError()
- Dataclasses for entities with fields and types
- Complete enum definitions
- Docstrings for every function and class
- Standard library types only (datetime, uuid, typing, etc.)

## CRITICAL RULES - READ CAREFULLY

1. **NO ABSTRACT CLASSES**: Never use ABC or abstractmethod. Use concrete classes.
2. **ONLY EXPORTS**: Only include what's explicitly listed in the spec's `exports:` section
3. **NO EXTRA CODE**: Don't add helper classes, utility functions, or extra types
4. **MINIMAL AND USEFUL**: Every line of code must serve a purpose from the spec
5. **CONCRETE IMPLEMENTATIONS**: Methods should raise NotImplementedError(), not be abstract

Example - If spec says:
```
exports:
- create_student(name, email) -> Student
- Student.save() -> None
```

Generate ONLY:
```python
@dataclass
class Student:
    name: str
    email: str

    def save(self) -> None:
        raise NotImplementedError()

def create_student(name: str, email: str) -> Student:
    raise NotImplementedError()
```

Do NOT add abstract base classes, protocols, or extra types not in exports.
"""

        prompt_parts = [
            "# FreeSpec Header Generation Instructions",
            "",
            "You are generating header/interface files from FreeSpec specifications.",
            "I will give you specs to generate headers for one at a time.",
            "",
            "## FreeSpec Documentation",
            "",
            docs,
            "",
            lang_instructions,
            "",
            "## Header Generation Workflow",
            "",
            "For each spec I give you:",
            "",
            "1. Read the spec file to understand description and exports",
            "2. Generate ONLY what is listed in the `exports:` section",
            "3. Write the file to the specified output path",
            "4. Do NOT generate implementation or tests",
            "",
            "## STRICT RULES",
            "",
            "- ONLY include what's explicitly in `exports:` - nothing more",
            "- NO abstract classes or ABC/abstractmethod - use concrete classes",
            "- NO extra helper classes, utilities, or types not in exports",
            "- Every export must be directly callable/importable",
            "- Methods raise NotImplementedError(), they are NOT abstract",
            "",
            "Ready for header generation tasks.",
        ]

        return "\n".join(prompt_parts)
