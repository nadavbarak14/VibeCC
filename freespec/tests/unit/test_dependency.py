"""Unit tests for dependency resolver."""

from pathlib import Path

import pytest

from freespec.parser.dependency import (
    CycleError,
    DependencyResolver,
)
from freespec.parser.models import DependencyGraph, Section, SpecFile


def make_spec(name: str, category: str, mentions: list[str] | None = None) -> SpecFile:
    """Helper to create a SpecFile for testing."""
    return SpecFile(
        path=Path(f"/project/{category}/{name}.spec"),
        name=name,
        category=category,
        description=Section("description", f"A {name}"),
        exports=Section("exports", "- Export"),
        tests=Section("tests", "- Test"),
        mentions=mentions or [],
    )


@pytest.fixture
def resolver() -> DependencyResolver:
    """Create a resolver instance."""
    return DependencyResolver()


class TestDependencyGraph:
    """Tests for DependencyGraph."""

    def test_add_spec(self) -> None:
        graph = DependencyGraph()
        spec = make_spec("student", "entities")

        graph.add_spec(spec)

        assert "entities/student" in graph.specs
        assert graph.get_spec("entities/student") == spec

    def test_add_spec_with_mentions(self) -> None:
        graph = DependencyGraph()
        student = make_spec("student", "entities")
        enrollment = make_spec("enrollment", "services", mentions=["entities/student"])

        graph.add_spec(student)
        graph.add_spec(enrollment)

        assert graph.get_dependencies("services/enrollment") == ["entities/student"]
        assert "services/enrollment" in graph.get_dependents("entities/student")

    def test_all_spec_ids(self) -> None:
        graph = DependencyGraph()
        graph.add_spec(make_spec("student", "entities"))
        graph.add_spec(make_spec("course", "entities"))

        ids = graph.all_spec_ids()

        assert set(ids) == {"entities/student", "entities/course"}


class TestDependencyResolver:
    """Tests for DependencyResolver."""

    def test_build_graph(self, resolver: DependencyResolver) -> None:
        specs = [
            make_spec("student", "entities"),
            make_spec("course", "entities"),
        ]

        graph = resolver.build_graph(specs)

        assert len(graph.all_spec_ids()) == 2

    def test_validate_missing_dependency(self, resolver: DependencyResolver) -> None:
        specs = [
            make_spec("enrollment", "services", mentions=["entities/student"]),
        ]

        graph = resolver.build_graph(specs)
        errors = resolver.validate_dependencies(graph)

        assert len(errors) == 1
        assert errors[0].spec_id == "services/enrollment"
        assert errors[0].missing == "entities/student"

    def test_validate_no_errors_when_deps_present(self, resolver: DependencyResolver) -> None:
        specs = [
            make_spec("student", "entities"),
            make_spec("enrollment", "services", mentions=["entities/student"]),
        ]

        graph = resolver.build_graph(specs)
        errors = resolver.validate_dependencies(graph)

        assert len(errors) == 0

    def test_topological_sort_no_deps(self, resolver: DependencyResolver) -> None:
        specs = [
            make_spec("student", "entities"),
            make_spec("course", "entities"),
        ]

        graph = resolver.build_graph(specs)
        order = resolver.topological_sort(graph)

        # Both should appear, order is alphabetical when no deps
        assert set(order) == {"entities/course", "entities/student"}

    def test_topological_sort_with_deps(self, resolver: DependencyResolver) -> None:
        specs = [
            make_spec("student", "entities"),
            make_spec("enrollment", "services", mentions=["entities/student"]),
        ]

        graph = resolver.build_graph(specs)
        order = resolver.topological_sort(graph)

        # Student must come before enrollment
        student_idx = order.index("entities/student")
        enrollment_idx = order.index("services/enrollment")
        assert student_idx < enrollment_idx

    def test_topological_sort_chain(self, resolver: DependencyResolver) -> None:
        specs = [
            make_spec("student", "entities"),
            make_spec("auth", "services", mentions=["entities/student"]),
            make_spec("api_auth", "api", mentions=["services/auth"]),
        ]

        graph = resolver.build_graph(specs)
        order = resolver.topological_sort(graph)

        # Order must be: student -> auth -> api_auth
        assert order.index("entities/student") < order.index("services/auth")
        assert order.index("services/auth") < order.index("api/api_auth")

    def test_topological_sort_multiple_deps(self, resolver: DependencyResolver) -> None:
        specs = [
            make_spec("student", "entities"),
            make_spec("course", "entities"),
            make_spec("enrollment", "services", mentions=["entities/student", "entities/course"]),
        ]

        graph = resolver.build_graph(specs)
        order = resolver.topological_sort(graph)

        # Both student and course must come before enrollment
        enrollment_idx = order.index("services/enrollment")
        assert order.index("entities/student") < enrollment_idx
        assert order.index("entities/course") < enrollment_idx

    def test_topological_sort_cycle_detection(self, resolver: DependencyResolver) -> None:
        specs = [
            make_spec("a", "entities", mentions=["entities/b"]),
            make_spec("b", "entities", mentions=["entities/a"]),
        ]

        graph = resolver.build_graph(specs)

        with pytest.raises(CycleError) as exc_info:
            resolver.topological_sort(graph)

        cycle = exc_info.value.cycle
        assert "entities/a" in cycle
        assert "entities/b" in cycle

    def test_topological_sort_self_cycle(self, resolver: DependencyResolver) -> None:
        specs = [
            make_spec("a", "entities", mentions=["entities/a"]),
        ]

        graph = resolver.build_graph(specs)

        with pytest.raises(CycleError):
            resolver.topological_sort(graph)

    def test_topological_sort_complex_cycle(self, resolver: DependencyResolver) -> None:
        # A -> B -> C -> A
        specs = [
            make_spec("a", "entities", mentions=["entities/b"]),
            make_spec("b", "entities", mentions=["entities/c"]),
            make_spec("c", "entities", mentions=["entities/a"]),
        ]

        graph = resolver.build_graph(specs)

        with pytest.raises(CycleError):
            resolver.topological_sort(graph)

    def test_get_build_order(self, resolver: DependencyResolver) -> None:
        specs = [
            make_spec("enrollment", "services", mentions=["entities/student"]),
            make_spec("student", "entities"),
        ]

        ordered_specs, errors = resolver.get_build_order(specs)

        # Should reorder: student first, then enrollment
        assert ordered_specs[0].name == "student"
        assert ordered_specs[1].name == "enrollment"
        assert len(errors) == 0

    def test_get_build_order_with_missing_deps(self, resolver: DependencyResolver) -> None:
        specs = [
            make_spec("enrollment", "services", mentions=["entities/nonexistent"]),
        ]

        ordered_specs, errors = resolver.get_build_order(specs)

        assert len(errors) == 1
        assert errors[0].missing == "entities/nonexistent"

    def test_handles_unresolved_deps_in_sort(self, resolver: DependencyResolver) -> None:
        # Spec depends on something not in the graph
        specs = [
            make_spec("enrollment", "services", mentions=["entities/student"]),
        ]

        graph = resolver.build_graph(specs)
        # Should not raise, just returns the one spec
        order = resolver.topological_sort(graph)

        assert order == ["services/enrollment"]


class TestTwoPassSupport:
    """Tests for two-pass compilation support (circular @mentions)."""

    def test_get_all_specs_preserves_order(self, resolver: DependencyResolver) -> None:
        """get_all_specs should return specs in original order."""
        specs = [
            make_spec("enrollment", "services", mentions=["entities/student"]),
            make_spec("student", "entities"),
        ]

        result_specs, errors = resolver.get_all_specs(specs)

        # Original order preserved
        assert result_specs[0].name == "enrollment"
        assert result_specs[1].name == "student"
        assert len(errors) == 0

    def test_get_all_specs_validates_missing_deps(self, resolver: DependencyResolver) -> None:
        """get_all_specs should report missing dependencies."""
        specs = [
            make_spec("enrollment", "services", mentions=["entities/nonexistent"]),
        ]

        _, errors = resolver.get_all_specs(specs)

        assert len(errors) == 1
        assert errors[0].missing == "entities/nonexistent"

    def test_get_build_order_allow_cycles(self, resolver: DependencyResolver) -> None:
        """get_build_order with allow_cycles=True should not raise on cycles."""
        specs = [
            make_spec("a", "entities", mentions=["entities/b"]),
            make_spec("b", "entities", mentions=["entities/a"]),
        ]

        # Should not raise, returns specs in original order
        ordered_specs, errors = resolver.get_build_order(specs, allow_cycles=True)

        assert len(ordered_specs) == 2
        assert ordered_specs[0].name == "a"
        assert ordered_specs[1].name == "b"

    def test_find_cycles_detects_cycle(self, resolver: DependencyResolver) -> None:
        """find_cycles should detect and return cycles."""
        specs = [
            make_spec("a", "entities", mentions=["entities/b"]),
            make_spec("b", "entities", mentions=["entities/a"]),
        ]

        cycles = resolver.find_cycles(specs)

        assert len(cycles) == 1
        assert "entities/a" in cycles[0]
        assert "entities/b" in cycles[0]

    def test_find_cycles_no_cycle(self, resolver: DependencyResolver) -> None:
        """find_cycles should return empty list when no cycles."""
        specs = [
            make_spec("student", "entities"),
            make_spec("enrollment", "services", mentions=["entities/student"]),
        ]

        cycles = resolver.find_cycles(specs)

        assert len(cycles) == 0

    def test_find_cycles_complex_cycle(self, resolver: DependencyResolver) -> None:
        """find_cycles should handle A -> B -> C -> A cycles."""
        specs = [
            make_spec("a", "entities", mentions=["entities/b"]),
            make_spec("b", "entities", mentions=["entities/c"]),
            make_spec("c", "entities", mentions=["entities/a"]),
        ]

        cycles = resolver.find_cycles(specs)

        assert len(cycles) == 1
