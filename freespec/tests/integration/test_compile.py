"""Integration tests for the compilation pipeline."""

from pathlib import Path
from textwrap import dedent
from unittest.mock import MagicMock

import pytest

from freespec.config import load_config
from freespec.generator.stubs import StubGenerator
from freespec.llm.claude_code import ClaudeCodeClient, GenerationResult
from freespec.parser.dependency import DependencyResolver
from freespec.parser.spec_parser import SpecParser
from freespec.verifier.imports import ImportVerifier


@pytest.fixture
def course_registration_path() -> Path:
    """Path to the course-registration example."""
    return Path(__file__).parent.parent.parent / "examples" / "course-registration"


@pytest.fixture
def example_config_path(course_registration_path: Path) -> Path:
    """Path to the example config file."""
    return course_registration_path.parent.parent / "freespec.yaml"


class TestParseAndResolveCourseRegistration:
    """Integration tests for parsing the course-registration example."""

    def test_parse_all_specs(self, course_registration_path: Path) -> None:
        """Test that all course-registration specs can be parsed."""
        parser = SpecParser()
        specs = parser.parse_glob("**/*.spec", course_registration_path)

        # Should find all spec files
        assert len(specs) >= 10

        # Verify categories
        categories = {s.category for s in specs}
        assert categories == {"entities", "services", "api"}

    def test_resolve_dependencies(self, course_registration_path: Path) -> None:
        """Test that dependencies are correctly resolved."""
        parser = SpecParser()
        specs = parser.parse_glob("**/*.spec", course_registration_path)

        resolver = DependencyResolver()
        ordered_specs, errors = resolver.get_build_order(specs)

        # No missing dependencies
        assert len(errors) == 0

        # Should return all specs in order
        assert len(ordered_specs) == len(specs)

        # Verify entities come before services that depend on them
        spec_order = [s.spec_id for s in ordered_specs]

        # enrollment depends on student, course, registration
        enrollment_idx = spec_order.index("services/enrollment")
        assert spec_order.index("entities/student") < enrollment_idx
        assert spec_order.index("entities/course") < enrollment_idx
        assert spec_order.index("entities/registration") < enrollment_idx

    def test_spec_mentions_are_extracted(self, course_registration_path: Path) -> None:
        """Test that @mentions are correctly extracted."""
        parser = SpecParser()
        specs = parser.parse_glob("**/*.spec", course_registration_path)

        # Find enrollment service
        enrollment = next((s for s in specs if s.name == "enrollment"), None)
        assert enrollment is not None

        # Should have mentions
        assert "entities/student" in enrollment.mentions
        assert "entities/course" in enrollment.mentions
        assert "entities/registration" in enrollment.mentions


class TestMockedGeneration:
    """Integration tests with mocked LLM."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock Claude Code client."""
        client = MagicMock(spec=ClaudeCodeClient)
        client.check_available.return_value = True

        # Return success with placeholder code
        def generate_stub(prompt: str) -> GenerationResult:
            # Extract output path from prompt
            import re
            match = re.search(r"Write.*to: (.+\.py)", prompt)
            if match:
                path = Path(match.group(1))
                # Create stub Python code
                code = dedent(f'''
                    """Generated stub for {path.stem}."""

                    class {path.stem.title()}:
                        """Stub class."""
                        pass
                ''').strip()
                # Write the file
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(code)

            return GenerationResult(success=True, output="Generated successfully")

        client.generate.side_effect = generate_stub
        return client

    def test_generate_stubs_for_single_spec(
        self,
        mock_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test stub generation for a single spec."""
        # Create a minimal spec
        spec_path = tmp_path / "entities" / "student.spec"
        spec_path.parent.mkdir(parents=True)
        spec_path.write_text(dedent("""
            description:
            A student entity.

            exports:
            - Create student
            - Find student

            tests:
            - Creating works
        """).strip())

        # Create config
        config_path = tmp_path / "freespec.yaml"
        config_path.write_text(dedent("""
            name: test
            version: "1.0"
            language: python
            specs:
              - "entities/*.spec"
            output:
              impl: generated/src/
              tests: generated/tests/
              api: generated/api/
        """).strip())

        config = load_config(config_path)

        parser = SpecParser()
        specs = parser.parse_glob("entities/*.spec", tmp_path)

        generator = StubGenerator(client=mock_client)
        context = generator.generate_all(specs, config, generate_tests=False)

        # Should have generated one file
        assert len(context.generated_files) == 1
        assert context.generated_files[0].path.exists()

    def test_dependency_order_respected(
        self,
        mock_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that dependencies are generated before dependents."""
        # Create specs with dependencies
        entities_dir = tmp_path / "entities"
        services_dir = tmp_path / "services"
        entities_dir.mkdir(parents=True)
        services_dir.mkdir(parents=True)

        (entities_dir / "student.spec").write_text(dedent("""
            description:
            A student.

            exports:
            - Create

            tests:
            - Test
        """).strip())

        (services_dir / "enrollment.spec").write_text(dedent("""
            description:
            Uses @entities/student.

            exports:
            - Enroll

            tests:
            - Test
        """).strip())

        # Create config
        config_path = tmp_path / "freespec.yaml"
        config_path.write_text(dedent("""
            name: test
            version: "1.0"
            language: python
            specs:
              - "**/*.spec"
            output:
              impl: generated/src/
              tests: generated/tests/
              api: generated/api/
        """).strip())

        config = load_config(config_path)

        parser = SpecParser()
        specs = parser.parse_glob("**/*.spec", tmp_path)

        resolver = DependencyResolver()
        ordered_specs, _ = resolver.get_build_order(specs)

        generator = StubGenerator(client=mock_client)
        generator.generate_all(ordered_specs, config, generate_tests=False)

        # Track order of generation calls
        call_order = []
        for call in mock_client.generate.call_args_list:
            prompt = call[0][0]
            # Check for spec name in the prompt (Category: X, Name: Y format)
            if "Name: student" in prompt:
                call_order.append("student")
            elif "Name: enrollment" in prompt:
                call_order.append("enrollment")

        # Student must be generated before enrollment
        assert "student" in call_order, f"student not found in call_order: {call_order}"
        assert "enrollment" in call_order, f"enrollment not found in call_order: {call_order}"
        assert call_order.index("student") < call_order.index("enrollment")


class TestImportVerification:
    """Integration tests for import verification."""

    def test_verify_valid_python(self, tmp_path: Path) -> None:
        """Test verification of valid Python files."""
        py_file = tmp_path / "valid.py"
        py_file.write_text(dedent("""
            class Student:
                def __init__(self, name: str) -> None:
                    self.name = name
        """).strip())

        verifier = ImportVerifier()
        errors = verifier.verify_import(py_file)

        assert len(errors) == 0

    def test_verify_syntax_error(self, tmp_path: Path) -> None:
        """Test detection of syntax errors."""
        py_file = tmp_path / "invalid.py"
        py_file.write_text("def broken(\n")

        verifier = ImportVerifier()
        errors = verifier.verify_syntax(py_file)

        assert len(errors) == 1
        assert "Syntax error" in errors[0].error

    def test_verify_import_error(self, tmp_path: Path) -> None:
        """Test detection of import errors."""
        py_file = tmp_path / "bad_import.py"
        py_file.write_text("from nonexistent_module import something\n")

        verifier = ImportVerifier()
        errors = verifier.verify_import(py_file)

        assert len(errors) == 1
        assert "Import failed" in errors[0].error

    def test_verify_all(self, tmp_path: Path) -> None:
        """Test verification of multiple files."""
        (tmp_path / "good1.py").write_text("x = 1\n")
        (tmp_path / "good2.py").write_text("y = 2\n")

        verifier = ImportVerifier()
        result = verifier.verify_all([
            tmp_path / "good1.py",
            tmp_path / "good2.py",
        ])

        assert result.success
        assert len(result.errors) == 0
