"""Real integration tests for C++ language prompts.

These tests send prompts to the real Claude CLI and verify that
generated C++ code compiles with g++ and behaves correctly.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from freespec.generator.cpp_runner import CppTestRunner
from freespec.generator.prompts import PromptBuilder
from freespec.llm.claude_code import ClaudeCodeClient
from freespec.parser.models import Section, SpecFile

# ---------------------------------------------------------------------------
# Skip markers
# ---------------------------------------------------------------------------


def claude_available() -> bool:
    """Check if claude CLI is available."""
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def gpp_available() -> bool:
    """Check if g++ is available."""
    try:
        result = subprocess.run(
            ["g++", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


requires_claude = pytest.mark.skipif(
    not claude_available(),
    reason="claude CLI not available",
)

requires_gpp = pytest.mark.skipif(
    not gpp_available(),
    reason="g++ not available",
)


# ---------------------------------------------------------------------------
# Shared fixtures / constants
# ---------------------------------------------------------------------------

COUNTER_SPEC_CONTENT = """\
description: A simple counter that tracks an integer value starting at zero.
exports:
- Create a new counter starting at zero
- Increment the counter by one
- Get the current counter value
tests:
- A new counter starts at zero
- Incrementing increases the value by one
- Multiple increments accumulate"""

KNOWN_GOOD_HEADER = """\
#pragma once
#include <cstdint>

struct Counter {
    int64_t value = 0;
    void increment();
    int64_t get_value() const;
};

Counter create_counter();
"""

SERVICE_HEADER = """\
#pragma once
#include <cstdint>
#include <string>

struct CounterService {
    std::string name;
    void reset_counter(int64_t& counter_value);
    std::string status(int64_t counter_value) const;
};
"""


def make_counter_spec() -> SpecFile:
    """Create the counter SpecFile used across tests."""
    return SpecFile(
        path=Path("/project/entities/counter.spec"),
        name="counter",
        category="entities",
        description=Section(
            "description",
            "A simple counter that tracks an integer value starting at zero.",
        ),
        exports=Section(
            "exports",
            (
                "- Create a new counter starting at zero\n"
                "- Increment the counter by one\n"
                "- Get the current counter value"
            ),
        ),
        tests=Section(
            "tests",
            (
                "- A new counter starts at zero\n"
                "- Incrementing increases the value by one\n"
                "- Multiple increments accumulate"
            ),
        ),
    )


def make_service_spec() -> SpecFile:
    """Create a counter_service SpecFile that depends on counter."""
    return SpecFile(
        path=Path("/project/services/counter_service.spec"),
        name="counter_service",
        category="services",
        description=Section(
            "description",
            "A service that manages counter resets and status reporting.",
        ),
        exports=Section(
            "exports",
            (
                "- Reset a counter value to zero\n"
                "- Get a human-readable status string for a counter value"
            ),
        ),
        tests=Section(
            "tests",
            ("- Resetting sets value to zero\n- Status reports the current value"),
        ),
        mentions=["entities/counter"],
    )


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


@requires_claude
@requires_gpp
class TestCppPromptsRealClaude:
    """Integration tests that send C++ prompts to real Claude and compile results."""

    @pytest.fixture
    def builder(self, tmp_path: Path) -> PromptBuilder:
        """Create a PromptBuilder with mock docs."""
        docs_path = tmp_path / "docs"
        docs_path.mkdir()
        (docs_path / "instructions.md").write_text("# Instructions\nFreeSpec instructions")
        (docs_path / "spec-format.md").write_text("# Spec Format\nFormat reference")
        return PromptBuilder(docs_path=docs_path)

    @pytest.fixture
    def client(self, tmp_path: Path) -> ClaudeCodeClient:
        """Create a ClaudeCodeClient pointed at tmp_path."""
        return ClaudeCodeClient(working_dir=tmp_path, timeout=120)

    # ----- Test 1: header prompt generates valid .hpp -----

    def test_header_prompt_generates_valid_hpp(
        self,
        tmp_path: Path,
        builder: PromptBuilder,
        client: ClaudeCodeClient,
    ) -> None:
        """build_header_prompt → Claude → .hpp that compiles."""
        spec = make_counter_spec()
        output_path = tmp_path / "counter.hpp"

        prompt = builder.build_header_prompt(spec, language="cpp", output_path=output_path)
        result = client.generate(prompt)

        assert result.success, f"Claude failed: {result.error}\n{result.output}"
        assert output_path.exists(), "Header file was not written"

        content = output_path.read_text()

        # Should contain C++ header artefacts
        assert "#include" in content or "struct" in content or "class" in content, (
            f"Generated header lacks C++ constructs:\n{content}"
        )

        # Should NOT contain Python-isms
        # Use "\ndef " to avoid matching C++ "#define"
        for python_marker in ("NotImplementedError", "\ndef ", "ABC"):
            assert python_marker not in content, (
                f"Header contains Python marker '{python_marker.strip()}':\n{content}"
            )

        # Must compile with g++
        compile_result = subprocess.run(
            ["g++", "-std=c++17", "-fsyntax-only", str(output_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert compile_result.returncode == 0, f"Header failed to compile:\n{compile_result.stderr}"

    # ----- Test 2: header instructions then fork generates .hpp -----

    def test_header_instructions_then_fork_generates_hpp(
        self,
        tmp_path: Path,
        builder: PromptBuilder,
        client: ClaudeCodeClient,
    ) -> None:
        """Send header instructions, fork with spec → .hpp that compiles."""
        spec = make_counter_spec()
        output_path = tmp_path / "counter.hpp"

        # Step 1: send base instructions
        instructions = builder.build_header_instructions_prompt(language="cpp")
        base_result = client.generate(instructions)
        assert base_result.success, (
            f"Base instructions failed: {base_result.error}\n{base_result.output}"
        )
        assert base_result.session_id is not None

        # Step 2: fork with a minimal prompt referencing the spec
        fork_prompt = (
            f"Generate a C++ header for this spec and write it to `{output_path}`.\n\n"
            f"Category: {spec.category}\n"
            f"Name: {spec.name}\n\n"
            f"```\n{spec.full_content}\n```"
        )
        fork_result = client.fork_session(base_result.session_id, fork_prompt)
        assert fork_result.success, f"Fork failed: {fork_result.error}\n{fork_result.output}"
        assert output_path.exists(), "Header file was not written by fork"

        content = output_path.read_text()
        assert "#include" in content or "struct" in content or "class" in content

        for python_marker in ("NotImplementedError", "\ndef ", "ABC"):
            assert python_marker not in content, (
                f"Header contains Python marker '{python_marker.strip()}'"
            )

        compile_result = subprocess.run(
            ["g++", "-std=c++17", "-fsyntax-only", str(output_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert compile_result.returncode == 0, f"Header failed to compile:\n{compile_result.stderr}"

    # ----- Test 3: compile prompt generates working .cpp -----

    def test_compile_prompt_generates_working_cpp(
        self,
        tmp_path: Path,
        builder: PromptBuilder,
        client: ClaudeCodeClient,
    ) -> None:
        """build_compile_prompt with known-good header → impl + tests that compile and run."""
        spec = make_counter_spec()

        # Write known-good header
        src_dir = tmp_path / "src" / "entities"
        src_dir.mkdir(parents=True)
        header_path = src_dir / "counter.hpp"
        header_path.write_text(KNOWN_GOOD_HEADER)

        impl_path = src_dir / "counter.cpp"
        test_path = tmp_path / "tests" / "entities" / "test_counter.cpp"
        test_path.parent.mkdir(parents=True)

        prompt = builder.build_compile_prompt(
            spec,
            language="cpp",
            impl_path=impl_path,
            test_path=test_path,
        )
        result = client.generate(prompt)
        assert result.success, f"Claude failed: {result.error}\n{result.output}"

        # Both files should be written
        assert impl_path.exists(), "Implementation file was not written"
        assert test_path.exists(), "Test file was not written"

        impl_content = impl_path.read_text()
        test_content = test_path.read_text()

        # No Python-isms (use line-start patterns to avoid matching C++ #define etc.)
        # Note: "pytest" is excluded because pytest tmp paths appear in #include directives.
        for python_marker in ("\nfrom ", "\nimport ", "NotImplementedError"):
            assert python_marker not in impl_content, (
                f"Impl contains Python marker '{python_marker.strip()}'"
            )
            assert python_marker not in test_content, (
                f"Test contains Python marker '{python_marker.strip()}'"
            )

        # Compile + run via CppTestRunner
        runner = CppTestRunner(
            working_dir=tmp_path,
            include_paths=[src_dir],
        )
        run_result = runner.run_test(test_path, impl_path)
        if not run_result.success and "multiple definition" in run_result.output:
            # Test file likely #includes the .cpp directly — compile without
            # separate impl to avoid duplicate symbols.
            run_result = runner.run_test(test_path)
        assert run_result.success, (
            f"Compile/run failed (compile rc={run_result.compile_returncode}, "
            f"test rc={run_result.test_returncode}):\n{run_result.output}"
        )

    # ----- Test 4: compile prompt with dependency uses #include -----

    def test_compile_prompt_with_dependency_uses_include(
        self,
        tmp_path: Path,
        builder: PromptBuilder,
        client: ClaudeCodeClient,
    ) -> None:
        """Compile prompt with dependency_paths produces #include, not 'from ... import'."""
        spec = make_service_spec()

        # Set up directory structure with both headers
        src_dir = tmp_path / "src"
        entities_dir = src_dir / "entities"
        entities_dir.mkdir(parents=True)
        services_dir = src_dir / "services"
        services_dir.mkdir(parents=True)

        counter_header = entities_dir / "counter.hpp"
        counter_header.write_text(KNOWN_GOOD_HEADER)

        service_header = services_dir / "counter_service.hpp"
        service_header.write_text(SERVICE_HEADER)

        impl_path = services_dir / "counter_service.cpp"
        test_path = tmp_path / "tests" / "services" / "test_counter_service.cpp"
        test_path.parent.mkdir(parents=True)

        prompt = builder.build_compile_prompt(
            spec,
            language="cpp",
            impl_path=impl_path,
            test_path=test_path,
            dependency_paths={"entities/counter": counter_header},
        )
        result = client.generate(prompt)
        assert result.success, f"Claude failed: {result.error}\n{result.output}"

        assert impl_path.exists(), "Service impl was not written"

        impl_content = impl_path.read_text()

        # Must use #include, not Python imports
        assert "#include" in impl_content, f"Impl missing #include directive:\n{impl_content}"
        assert "from " not in impl_content, f"Impl contains Python 'from' import:\n{impl_content}"
        assert "import " not in impl_content, (
            f"Impl contains Python 'import' statement:\n{impl_content}"
        )

        # At minimum syntax-check the impl
        compile_result = subprocess.run(
            [
                "g++",
                "-std=c++17",
                "-fsyntax-only",
                f"-I{src_dir}",
                str(impl_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert compile_result.returncode == 0, (
            f"Service impl failed syntax check:\n{compile_result.stderr}"
        )

    # ----- Test 5: review prompt catches C++ export violations -----

    def test_review_prompt_catches_cpp_violations(
        self,
        tmp_path: Path,
        builder: PromptBuilder,
        client: ClaudeCodeClient,
    ) -> None:
        """build_review_prompt detects extra public functions in C++ impl."""
        spec = make_counter_spec()

        # Write an impl that adds an extra public function
        impl_path = tmp_path / "counter.cpp"
        impl_path.write_text(
            '#include "counter.hpp"\n'
            "\n"
            "Counter create_counter() {\n"
            "    return Counter{0};\n"
            "}\n"
            "\n"
            "void Counter::increment() {\n"
            "    value++;\n"
            "}\n"
            "\n"
            "int64_t Counter::get_value() const {\n"
            "    return value;\n"
            "}\n"
            "\n"
            "// EXTRA: not in the spec\n"
            "void Counter::reset() {\n"
            "    value = 0;\n"
            "}\n"
            "\n"
            "// EXTRA free function not in spec\n"
            "Counter create_counter_with_value(int64_t v) {\n"
            "    Counter c;\n"
            "    c.value = v;\n"
            "    return c;\n"
            "}\n"
        )

        # Write a matching header that also has the extra methods
        header_path = tmp_path / "counter.hpp"
        header_path.write_text(
            "#pragma once\n"
            "#include <cstdint>\n"
            "\n"
            "struct Counter {\n"
            "    int64_t value = 0;\n"
            "    void increment();\n"
            "    int64_t get_value() const;\n"
            "    void reset();  // EXTRA\n"
            "};\n"
            "\n"
            "Counter create_counter();\n"
            "Counter create_counter_with_value(int64_t v);  // EXTRA\n"
        )

        prompt = builder.build_review_prompt(
            spec,
            impl_path=impl_path,
            test_path=None,
            original_exports={"Counter", "create_counter"},
            language="cpp",
        )
        result = client.generate(prompt)
        assert result.success, f"Claude failed: {result.error}\n{result.output}"

        # Claude should detect the extra exports — either by reporting REVIEW_FAILED,
        # mentioning them by name, or acknowledging extra exports were found/fixed.
        output_lower = result.output.lower()
        assert (
            "REVIEW_FAILED" in result.output
            or "reset" in result.output
            or "create_counter_with_value" in result.output
            or "extra" in output_lower
            or "removed" in output_lower
            or "violation" in output_lower
        ), f"Expected Claude to detect extra exports but got:\n{result.output}"
