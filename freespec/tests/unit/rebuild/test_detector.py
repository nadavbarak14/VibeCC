"""Unit tests for the rebuild detector."""

from pathlib import Path

import pytest

from freespec.config import FreeSpecConfig, OutputConfig, SettingsConfig
from freespec.parser.models import DependencyGraph, Section, SpecFile
from freespec.rebuild.detector import (
    DetectionResult,
    RebuildDetector,
    RebuildInfo,
    RebuildReason,
)
from freespec.rebuild.manifest import SpecBuildState, compute_file_hash


@pytest.fixture
def temp_config(tmp_path: Path) -> FreeSpecConfig:
    """Create a temporary config for testing."""
    return FreeSpecConfig(
        name="test-project",
        version="1.0",
        specs=["specs/**/*.spec"],
        output=OutputConfig(out="out/", src="src/", tests="tests/"),
        settings=SettingsConfig(interactive=False),
        root_path=tmp_path,
    )


@pytest.fixture
def sample_spec(tmp_path: Path) -> SpecFile:
    """Create a sample spec file."""
    spec_path = tmp_path / "specs" / "entities" / "student.spec"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text("# student spec\ndescription: A student entity")

    return SpecFile(
        path=spec_path,
        name="student",
        category="entities",
        description=Section("description", "A student entity"),
        exports=Section("exports", "- Student class"),
        tests=Section("tests", "- test student"),
        mentions=[],
    )


@pytest.fixture
def sample_spec_with_mentions(tmp_path: Path) -> SpecFile:
    """Create a spec file with @mentions."""
    spec_path = tmp_path / "specs" / "services" / "enrollment.spec"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text("# enrollment spec\n@entities/student")

    return SpecFile(
        path=spec_path,
        name="enrollment",
        category="services",
        description=Section("description", "Enrollment service"),
        exports=Section("exports", "- EnrollmentService class"),
        tests=Section("tests", "- test enrollment"),
        mentions=["entities/student"],
    )


class TestRebuildInfo:
    """Tests for RebuildInfo."""

    def test_needs_rebuild_when_header_needed(self) -> None:
        info = RebuildInfo(spec_id="test", needs_header=True, needs_impl=False)

        assert info.needs_rebuild is True

    def test_needs_rebuild_when_impl_needed(self) -> None:
        info = RebuildInfo(spec_id="test", needs_header=False, needs_impl=True)

        assert info.needs_rebuild is True

    def test_needs_rebuild_false_when_nothing_needed(self) -> None:
        info = RebuildInfo(spec_id="test", needs_header=False, needs_impl=False)

        assert info.needs_rebuild is False


class TestDetectionResult:
    """Tests for DetectionResult."""

    def test_nothing_to_rebuild_when_empty(self) -> None:
        result = DetectionResult(
            rebuild_info={},
            header_specs=[],
            impl_specs=[],
            total_specs=5,
        )

        assert result.nothing_to_rebuild is True

    def test_nothing_to_rebuild_false_when_has_headers(self) -> None:
        result = DetectionResult(
            rebuild_info={},
            header_specs=["entities/student"],
            impl_specs=[],
            total_specs=5,
        )

        assert result.nothing_to_rebuild is False

    def test_nothing_to_rebuild_false_when_has_impls(self) -> None:
        result = DetectionResult(
            rebuild_info={},
            header_specs=[],
            impl_specs=["entities/student"],
            total_specs=5,
        )

        assert result.nothing_to_rebuild is False


class TestRebuildDetector:
    """Tests for RebuildDetector."""

    def test_get_manifest_path(self, temp_config: FreeSpecConfig) -> None:
        detector = RebuildDetector(temp_config, "python")

        path = detector.get_manifest_path()

        assert path == temp_config.root_path / "out" / "python" / ".freespec_build.json"

    def test_load_manifest_creates_new_if_missing(
        self, temp_config: FreeSpecConfig
    ) -> None:
        detector = RebuildDetector(temp_config, "python")

        manifest = detector.load_manifest()

        assert manifest is not None
        assert manifest.language == "python"

    def test_load_manifest_caches_result(self, temp_config: FreeSpecConfig) -> None:
        detector = RebuildDetector(temp_config, "python")

        manifest1 = detector.load_manifest()
        manifest2 = detector.load_manifest()

        assert manifest1 is manifest2


class TestHeaderChangeDetection:
    """Tests for Phase 1 header change detection."""

    def test_detects_new_spec_needs_header(
        self, temp_config: FreeSpecConfig, sample_spec: SpecFile
    ) -> None:
        detector = RebuildDetector(temp_config, "python")

        changes = detector.detect_header_changes([sample_spec])

        assert sample_spec.spec_id in changes
        info = changes[sample_spec.spec_id]
        assert info.needs_header is True
        assert RebuildReason.NO_MANIFEST in info.reasons

    def test_detects_spec_change(
        self, temp_config: FreeSpecConfig, sample_spec: SpecFile
    ) -> None:
        detector = RebuildDetector(temp_config, "python")
        # Set up manifest with old hash
        manifest = detector.load_manifest()
        manifest.update_spec(
            sample_spec.spec_id,
            SpecBuildState(
                spec_hash="old_hash",
                header_hash="header_hash",
                impl_hash="impl_hash",
                test_hash="test_hash",
                mentions=[],
                built_at="",
            ),
        )

        changes = detector.detect_header_changes([sample_spec])

        assert sample_spec.spec_id in changes
        info = changes[sample_spec.spec_id]
        assert info.needs_header is True
        assert RebuildReason.SPEC_CHANGED in info.reasons

    def test_no_change_when_hash_matches(
        self, temp_config: FreeSpecConfig, sample_spec: SpecFile
    ) -> None:
        detector = RebuildDetector(temp_config, "python")
        # Set up manifest with current hash
        current_hash = compute_file_hash(sample_spec.path)
        manifest = detector.load_manifest()
        manifest.update_spec(
            sample_spec.spec_id,
            SpecBuildState(
                spec_hash=current_hash,
                header_hash="header_hash",
                impl_hash="impl_hash",
                test_hash="test_hash",
                mentions=[],
                built_at="",
            ),
        )

        changes = detector.detect_header_changes([sample_spec])

        assert sample_spec.spec_id not in changes

    def test_force_triggers_all_headers(
        self, temp_config: FreeSpecConfig, sample_spec: SpecFile
    ) -> None:
        detector = RebuildDetector(temp_config, "python")
        # Set up manifest with current hash
        current_hash = compute_file_hash(sample_spec.path)
        manifest = detector.load_manifest()
        manifest.update_spec(
            sample_spec.spec_id,
            SpecBuildState(
                spec_hash=current_hash,
                header_hash="header_hash",
                impl_hash="impl_hash",
                test_hash="test_hash",
                mentions=[],
                built_at="",
            ),
        )

        changes = detector.detect_header_changes([sample_spec], force=True)

        assert sample_spec.spec_id in changes
        info = changes[sample_spec.spec_id]
        assert info.needs_header is True
        assert RebuildReason.FORCED in info.reasons


class TestImplChangeDetection:
    """Tests for Phase 2 impl change detection."""

    def test_header_change_triggers_impl(
        self, temp_config: FreeSpecConfig, sample_spec: SpecFile
    ) -> None:
        detector = RebuildDetector(temp_config, "python")
        graph = DependencyGraph()
        graph.add_spec(sample_spec)
        header_changes = {
            sample_spec.spec_id: RebuildInfo(
                spec_id=sample_spec.spec_id,
                needs_header=True,
                reasons=[RebuildReason.SPEC_CHANGED],
            )
        }

        changes = detector.detect_impl_changes([sample_spec], graph, header_changes)

        assert sample_spec.spec_id in changes
        info = changes[sample_spec.spec_id]
        assert info.needs_impl is True

    def test_missing_output_triggers_impl(
        self, temp_config: FreeSpecConfig, sample_spec: SpecFile
    ) -> None:
        detector = RebuildDetector(temp_config, "python")
        graph = DependencyGraph()
        graph.add_spec(sample_spec)
        # Set up manifest with current hash (spec hasn't changed)
        current_hash = compute_file_hash(sample_spec.path)
        manifest = detector.load_manifest()
        manifest.update_spec(
            sample_spec.spec_id,
            SpecBuildState(
                spec_hash=current_hash,
                header_hash="header_hash",
                impl_hash="impl_hash",
                test_hash="test_hash",
                mentions=[],
                built_at="",
            ),
        )

        # No output files exist
        changes = detector.detect_impl_changes([sample_spec], graph, {})

        assert sample_spec.spec_id in changes
        info = changes[sample_spec.spec_id]
        assert info.needs_impl is True
        assert RebuildReason.OUTPUT_MISSING in info.reasons

    def test_dependency_change_propagates(
        self,
        temp_config: FreeSpecConfig,
        sample_spec: SpecFile,
        sample_spec_with_mentions: SpecFile,
    ) -> None:
        detector = RebuildDetector(temp_config, "python")

        # Build graph with dependency relationship
        graph = DependencyGraph()
        graph.add_spec(sample_spec)  # entities/student
        graph.add_spec(sample_spec_with_mentions)  # services/enrollment -> entities/student

        # Create output files for enrollment so OUTPUT_MISSING doesn't trigger
        impl_path = temp_config.get_src_path("python") / "services" / "enrollment.py"
        test_path = temp_config.get_tests_path("python") / "services" / "test_enrollment.py"
        impl_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.parent.mkdir(parents=True, exist_ok=True)
        impl_path.write_text("# impl")
        test_path.write_text("# test")

        # Set up manifest for enrollment (so NO_MANIFEST doesn't trigger)
        manifest = detector.load_manifest()
        current_hash = compute_file_hash(sample_spec_with_mentions.path)
        manifest.update_spec(
            sample_spec_with_mentions.spec_id,
            SpecBuildState(
                spec_hash=current_hash,
                header_hash="old_header",
                impl_hash="impl_hash",
                test_hash="test_hash",
                mentions=["entities/student"],
                built_at="",
            ),
        )

        # Student header changed
        header_changes = {
            sample_spec.spec_id: RebuildInfo(
                spec_id=sample_spec.spec_id,
                needs_header=True,
                reasons=[RebuildReason.SPEC_CHANGED],
            )
        }

        specs = [sample_spec, sample_spec_with_mentions]
        changes = detector.detect_impl_changes(specs, graph, header_changes)

        # Enrollment should need rebuild due to dependency change
        assert sample_spec_with_mentions.spec_id in changes
        info = changes[sample_spec_with_mentions.spec_id]
        assert info.needs_impl is True
        assert RebuildReason.DEPENDENCY_HEADER_CHANGED in info.reasons
        assert sample_spec.spec_id in info.triggering_deps


class TestRebuildOrder:
    """Tests for topological ordering."""

    def test_orders_by_dependencies(
        self,
        temp_config: FreeSpecConfig,
        sample_spec: SpecFile,
        sample_spec_with_mentions: SpecFile,
    ) -> None:
        detector = RebuildDetector(temp_config, "python")

        # Build graph with dependency relationship
        graph = DependencyGraph()
        graph.add_spec(sample_spec)  # entities/student
        graph.add_spec(sample_spec_with_mentions)  # services/enrollment -> entities/student

        rebuild_info = {
            sample_spec.spec_id: RebuildInfo(spec_id=sample_spec.spec_id, needs_impl=True),
            sample_spec_with_mentions.spec_id: RebuildInfo(
                spec_id=sample_spec_with_mentions.spec_id, needs_impl=True
            ),
        }

        order = detector.get_rebuild_order(rebuild_info, graph)

        # Student should come before enrollment
        student_idx = order.index(sample_spec.spec_id)
        enrollment_idx = order.index(sample_spec_with_mentions.spec_id)
        assert student_idx < enrollment_idx

    def test_handles_empty_rebuild_info(self, temp_config: FreeSpecConfig) -> None:
        detector = RebuildDetector(temp_config, "python")
        graph = DependencyGraph()

        order = detector.get_rebuild_order({}, graph)

        assert order == []


class TestDetectAll:
    """Tests for the full detection pipeline."""

    def test_detect_all_new_project(
        self, temp_config: FreeSpecConfig, sample_spec: SpecFile
    ) -> None:
        detector = RebuildDetector(temp_config, "python")
        graph = DependencyGraph()
        graph.add_spec(sample_spec)

        result = detector.detect_all([sample_spec], graph)

        assert not result.nothing_to_rebuild
        assert sample_spec.spec_id in result.header_specs
        assert sample_spec.spec_id in result.impl_specs
        assert result.total_specs == 1

    def test_detect_all_nothing_changed(
        self, temp_config: FreeSpecConfig, sample_spec: SpecFile
    ) -> None:
        detector = RebuildDetector(temp_config, "python")
        graph = DependencyGraph()
        graph.add_spec(sample_spec)

        # Create output files
        impl_path = temp_config.get_src_path("python") / "entities" / "student.py"
        test_path = temp_config.get_tests_path("python") / "entities" / "test_student.py"
        impl_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.parent.mkdir(parents=True, exist_ok=True)
        impl_path.write_text("# impl")
        test_path.write_text("# test")

        # Set up manifest with current hash
        current_hash = compute_file_hash(sample_spec.path)
        manifest = detector.load_manifest()
        manifest.update_spec(
            sample_spec.spec_id,
            SpecBuildState(
                spec_hash=current_hash,
                header_hash="header_hash",
                impl_hash="impl_hash",
                test_hash="test_hash",
                mentions=[],
                built_at="",
            ),
        )

        result = detector.detect_all([sample_spec], graph)

        assert result.nothing_to_rebuild
        assert len(result.header_specs) == 0
        assert len(result.impl_specs) == 0


class TestManifestUpdates:
    """Tests for manifest update methods."""

    def test_update_manifest_after_header(
        self, temp_config: FreeSpecConfig, sample_spec: SpecFile
    ) -> None:
        detector = RebuildDetector(temp_config, "python")

        # Create header file
        header_path = temp_config.get_src_path("python") / "entities" / "student.py"
        header_path.parent.mkdir(parents=True, exist_ok=True)
        header_path.write_text("# header content")

        detector.update_manifest_after_header(sample_spec, header_path)

        manifest = detector.load_manifest()
        state = manifest.get_state(sample_spec.spec_id)
        assert state is not None
        assert state.spec_hash == compute_file_hash(sample_spec.path)
        assert state.header_hash == compute_file_hash(header_path)

    def test_update_manifest_after_compile(
        self, temp_config: FreeSpecConfig, sample_spec: SpecFile
    ) -> None:
        detector = RebuildDetector(temp_config, "python")

        # Create impl and test files
        impl_path = temp_config.get_src_path("python") / "entities" / "student.py"
        test_path = temp_config.get_tests_path("python") / "entities" / "test_student.py"
        impl_path.parent.mkdir(parents=True, exist_ok=True)
        test_path.parent.mkdir(parents=True, exist_ok=True)
        impl_path.write_text("# impl content")
        test_path.write_text("# test content")

        detector.update_manifest_after_compile(sample_spec, impl_path, test_path)

        manifest = detector.load_manifest()
        state = manifest.get_state(sample_spec.spec_id)
        assert state is not None
        assert state.spec_hash == compute_file_hash(sample_spec.path)
        assert state.impl_hash == compute_file_hash(impl_path)
        assert state.test_hash == compute_file_hash(test_path)
