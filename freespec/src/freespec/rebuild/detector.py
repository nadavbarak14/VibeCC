"""Rebuild detection with two-phase dependency propagation.

Phase 1: Detect spec files that need header regeneration
Phase 2: Detect specs that need implementation rebuild based on:
         - Header was regenerated
         - Output files missing
         - Dependency's header changed (with transitive propagation)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from freespec.config import FreeSpecConfig
from freespec.parser.models import DependencyGraph, SpecFile
from freespec.rebuild.manifest import (
    BuildManifest,
    SpecBuildState,
    compute_file_hash,
    get_timestamp,
)


class RebuildReason(Enum):
    """Reasons why a spec needs to be rebuilt."""

    NO_MANIFEST = "no build history"
    SPEC_CHANGED = "spec changed"
    HEADER_CHANGED = "header changed"
    DEPENDENCY_HEADER_CHANGED = "dependency header changed"
    OUTPUT_MISSING = "output missing"
    FORCED = "forced"


@dataclass
class RebuildInfo:
    """Information about why a spec needs rebuilding."""

    spec_id: str
    needs_header: bool = False
    needs_impl: bool = False
    reasons: list[RebuildReason] = field(default_factory=list)
    triggering_deps: list[str] = field(default_factory=list)

    @property
    def needs_rebuild(self) -> bool:
        """Check if any rebuild is needed."""
        return self.needs_header or self.needs_impl


@dataclass
class DetectionResult:
    """Result of rebuild detection."""

    # All specs that need any kind of rebuild
    rebuild_info: dict[str, RebuildInfo]
    # Specs that need header regeneration (Phase 1)
    header_specs: list[str]
    # Specs that need impl rebuild (Phase 2), in topological order
    impl_specs: list[str]
    # Total spec count
    total_specs: int

    @property
    def nothing_to_rebuild(self) -> bool:
        """Check if nothing needs rebuilding."""
        return len(self.header_specs) == 0 and len(self.impl_specs) == 0


class RebuildDetector:
    """Detects which specs need rebuilding using two-phase detection."""

    def __init__(self, config: FreeSpecConfig, language: str) -> None:
        """Initialize the rebuild detector.

        Args:
            config: Project configuration.
            language: Target language (python, cpp).
        """
        self.config = config
        self.language = language
        self._manifest: BuildManifest | None = None

    def get_manifest_path(self) -> Path:
        """Get the manifest file path for this language."""
        return self.config.get_manifest_path(self.language)

    def load_manifest(self) -> BuildManifest:
        """Load or create manifest for this language."""
        if self._manifest is not None:
            return self._manifest

        manifest = BuildManifest.load(self.get_manifest_path())
        if manifest is None:
            manifest = BuildManifest(language=self.language)
        self._manifest = manifest
        return manifest

    def save_manifest(self) -> None:
        """Save the current manifest."""
        if self._manifest is not None:
            self._manifest.save(self.get_manifest_path())

    def _get_file_ext(self) -> str:
        """Get file extension for the target language."""
        if self.language.lower() in ("cpp", "c++"):
            return ".cpp"
        return ".py"

    def _get_header_ext(self) -> str:
        """Get header file extension for the target language."""
        if self.language.lower() in ("cpp", "c++"):
            return ".hpp"
        return ".py"

    def _get_impl_path(self, spec: SpecFile) -> Path:
        """Get implementation file path for a spec."""
        ext = self._get_file_ext()
        base = self.config.get_src_path(self.language)
        return base / spec.category / f"{spec.name}{ext}"

    def _get_header_path(self, spec: SpecFile) -> Path:
        """Get header file path for a spec."""
        ext = self._get_header_ext()
        base = self.config.get_src_path(self.language)
        return base / spec.category / f"{spec.name}{ext}"

    def _get_test_path(self, spec: SpecFile) -> Path:
        """Get test file path for a spec."""
        ext = self._get_file_ext()
        base = self.config.get_tests_path(self.language)
        return base / spec.category / f"test_{spec.name}{ext}"

    def detect_header_changes(
        self,
        specs: list[SpecFile],
        force: bool = False,
    ) -> dict[str, RebuildInfo]:
        """Phase 1: Detect specs that need header regeneration.

        Args:
            specs: List of spec files to check.
            force: Force all headers to regenerate.

        Returns:
            Map of spec_id to RebuildInfo for specs needing header regen.
        """
        manifest = self.load_manifest()
        result: dict[str, RebuildInfo] = {}

        for spec in specs:
            info = RebuildInfo(spec_id=spec.spec_id)

            if force:
                info.needs_header = True
                info.reasons.append(RebuildReason.FORCED)
                result[spec.spec_id] = info
                continue

            state = manifest.get_state(spec.spec_id)

            # No previous build
            if state is None:
                info.needs_header = True
                info.reasons.append(RebuildReason.NO_MANIFEST)
                result[spec.spec_id] = info
                continue

            # Check if spec file changed
            current_spec_hash = compute_file_hash(spec.path)
            if current_spec_hash != state.spec_hash:
                info.needs_header = True
                info.reasons.append(RebuildReason.SPEC_CHANGED)
                result[spec.spec_id] = info

        return result

    def detect_impl_changes(
        self,
        specs: list[SpecFile],
        graph: DependencyGraph,
        header_changes: dict[str, RebuildInfo],
        force: bool = False,
    ) -> dict[str, RebuildInfo]:
        """Phase 2: Detect specs that need implementation rebuild.

        Checks:
        - If header was regenerated
        - If impl or test file is missing
        - If any dependency's header changed (transitive)

        Args:
            specs: List of spec files to check.
            graph: Dependency graph for the specs.
            header_changes: Results from Phase 1.
            force: Force all impls to rebuild.

        Returns:
            Map of spec_id to RebuildInfo for specs needing impl rebuild.
        """
        manifest = self.load_manifest()
        result: dict[str, RebuildInfo] = {}

        # Start with header changes - all of those need impl rebuild too
        for spec_id, header_info in header_changes.items():
            info = RebuildInfo(
                spec_id=spec_id,
                needs_header=header_info.needs_header,
                needs_impl=True,
                reasons=list(header_info.reasons),
                triggering_deps=list(header_info.triggering_deps),
            )
            if RebuildReason.HEADER_CHANGED not in info.reasons:
                info.reasons.append(RebuildReason.HEADER_CHANGED)
            result[spec_id] = info

        # Build lookup for specs
        specs_by_id = {s.spec_id: s for s in specs}

        # Check remaining specs
        for spec in specs:
            if spec.spec_id in result:
                continue

            info = RebuildInfo(spec_id=spec.spec_id)

            if force:
                info.needs_impl = True
                info.reasons.append(RebuildReason.FORCED)
                result[spec.spec_id] = info
                continue

            state = manifest.get_state(spec.spec_id)

            # No previous build
            if state is None:
                info.needs_impl = True
                info.reasons.append(RebuildReason.NO_MANIFEST)
                result[spec.spec_id] = info
                continue

            # Check if implementation file exists
            impl_path = self._get_impl_path(spec)
            if not impl_path.exists():
                info.needs_impl = True
                info.reasons.append(RebuildReason.OUTPUT_MISSING)
                result[spec.spec_id] = info
                continue

            # Only check test file if spec has test cases defined
            if spec.tests.items:
                test_path = self._get_test_path(spec)
                if not test_path.exists():
                    info.needs_impl = True
                    info.reasons.append(RebuildReason.OUTPUT_MISSING)
                    result[spec.spec_id] = info
                    continue

        # Propagate dependency changes transitively
        changed_headers = set(header_changes.keys())
        self._propagate_dependency_changes(specs_by_id, graph, changed_headers, result, manifest)

        return result

    def _propagate_dependency_changes(
        self,
        specs_by_id: dict[str, SpecFile],
        graph: DependencyGraph,
        changed_headers: set[str],
        result: dict[str, RebuildInfo],
        manifest: BuildManifest,
    ) -> None:
        """Propagate header changes to dependents transitively.

        Args:
            specs_by_id: Map of spec_id to SpecFile.
            graph: Dependency graph.
            changed_headers: Set of spec_ids whose headers changed.
            result: Result dict to update.
            manifest: Build manifest.
        """
        # Queue of specs that might need rebuild due to dependency changes
        queue = list(changed_headers)
        processed: set[str] = set()

        while queue:
            changed_spec_id = queue.pop(0)
            if changed_spec_id in processed:
                continue
            processed.add(changed_spec_id)

            # Find all dependents
            dependents = graph.get_dependents(changed_spec_id)

            for dep_id in dependents:
                if dep_id not in specs_by_id:
                    continue

                # Check if this dependent needs rebuild
                if dep_id in result and result[dep_id].needs_impl:
                    # Already marked for rebuild, but add triggering dep
                    if changed_spec_id not in result[dep_id].triggering_deps:
                        result[dep_id].triggering_deps.append(changed_spec_id)
                    continue

                # Check manifest for this dependent
                dep_state = manifest.get_state(dep_id)
                if dep_state is None:
                    # No previous state means it will be caught elsewhere
                    continue

                # This dependent needs rebuild due to changed dependency
                info = result.get(dep_id, RebuildInfo(spec_id=dep_id))
                info.needs_impl = True
                if RebuildReason.DEPENDENCY_HEADER_CHANGED not in info.reasons:
                    info.reasons.append(RebuildReason.DEPENDENCY_HEADER_CHANGED)
                info.triggering_deps.append(changed_spec_id)
                result[dep_id] = info

                # Add to queue for further propagation
                queue.append(dep_id)

    def get_rebuild_order(
        self,
        rebuild_info: dict[str, RebuildInfo],
        graph: DependencyGraph,
    ) -> list[str]:
        """Get specs to rebuild in topological order.

        Args:
            rebuild_info: Map of spec_id to rebuild info.
            graph: Dependency graph.

        Returns:
            List of spec_ids in order they should be rebuilt.
        """
        # Simple topological sort using Kahn's algorithm
        specs_to_rebuild = set(rebuild_info.keys())

        if not specs_to_rebuild:
            return []

        # Build in-degree count for specs needing rebuild
        in_degree: dict[str, int] = {s: 0 for s in specs_to_rebuild}

        for spec_id in specs_to_rebuild:
            for dep in graph.get_dependencies(spec_id):
                if dep in specs_to_rebuild:
                    in_degree[spec_id] += 1

        # Start with specs that have no dependencies in the rebuild set
        queue = [s for s, d in in_degree.items() if d == 0]
        result: list[str] = []

        while queue:
            # Sort for deterministic ordering
            queue.sort()
            spec_id = queue.pop(0)
            result.append(spec_id)

            # Decrease in-degree for dependents
            for dep_id in graph.get_dependents(spec_id):
                if dep_id in in_degree:
                    in_degree[dep_id] -= 1
                    if in_degree[dep_id] == 0:
                        queue.append(dep_id)

        # Handle cycles - add remaining specs
        remaining = specs_to_rebuild - set(result)
        result.extend(sorted(remaining))

        return result

    def detect_all(
        self,
        specs: list[SpecFile],
        graph: DependencyGraph,
        force: bool = False,
    ) -> DetectionResult:
        """Run full two-phase detection.

        Args:
            specs: List of spec files to check.
            graph: Dependency graph for specs.
            force: Force full rebuild.

        Returns:
            Complete detection result.
        """
        # Phase 1: Header detection
        header_changes = self.detect_header_changes(specs, force=force)
        header_specs = list(header_changes.keys())

        # Phase 2: Impl detection
        impl_changes = self.detect_impl_changes(specs, graph, header_changes, force=force)
        impl_specs = self.get_rebuild_order(impl_changes, graph)

        return DetectionResult(
            rebuild_info=impl_changes,
            header_specs=header_specs,
            impl_specs=impl_specs,
            total_specs=len(specs),
        )

    def update_manifest_after_header(
        self,
        spec: SpecFile,
        header_path: Path,
    ) -> None:
        """Update manifest after header generation.

        Args:
            spec: The spec that was compiled.
            header_path: Path to generated header.
        """
        manifest = self.load_manifest()
        state = manifest.get_state(spec.spec_id) or SpecBuildState(
            spec_hash="",
            header_hash="",
            impl_hash="",
            test_hash="",
            mentions=[],
            built_at="",
        )

        state.spec_hash = compute_file_hash(spec.path)
        state.header_hash = compute_file_hash(header_path)
        state.mentions = list(spec.mentions)
        state.built_at = get_timestamp()

        manifest.update_spec(spec.spec_id, state)

    def update_manifest_after_compile(
        self,
        spec: SpecFile,
        impl_path: Path,
        test_path: Path | None = None,
    ) -> None:
        """Update manifest after successful compilation.

        Args:
            spec: The spec that was compiled.
            impl_path: Path to implementation file.
            test_path: Path to test file, or None if no tests were generated.
        """
        manifest = self.load_manifest()
        state = manifest.get_state(spec.spec_id) or SpecBuildState(
            spec_hash="",
            header_hash="",
            impl_hash="",
            test_hash="",
            mentions=[],
            built_at="",
        )

        state.spec_hash = compute_file_hash(spec.path)
        state.impl_hash = compute_file_hash(impl_path)
        state.test_hash = compute_file_hash(test_path) if test_path else ""
        state.mentions = list(spec.mentions)
        state.built_at = get_timestamp()

        manifest.update_spec(spec.spec_id, state)
