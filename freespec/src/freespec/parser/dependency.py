"""Dependency resolution for spec files.

With the two-pass compilation architecture, circular @mentions are allowed
since Pass 1 (headers) generates all interfaces independently, and Pass 2
(implementations) uses all headers as context.
"""

from __future__ import annotations

from freespec.parser.models import DependencyGraph, SpecFile


class CycleError(Exception):
    """Raised when a dependency cycle is detected.

    Note: With two-pass compilation, cycles are allowed. This exception
    is kept for backwards compatibility and optional strict validation.
    """

    def __init__(self, cycle: list[str]) -> None:
        """Initialize with the cycle path.

        Args:
            cycle: List of spec IDs forming the cycle.
        """
        self.cycle = cycle
        cycle_str = " -> ".join(cycle)
        super().__init__(f"Dependency cycle detected: {cycle_str}")


class MissingDependencyError(Exception):
    """Raised when a referenced dependency doesn't exist."""

    def __init__(self, spec_id: str, missing: str) -> None:
        """Initialize with the spec and missing dependency.

        Args:
            spec_id: The spec that has the missing dependency.
            missing: The missing dependency ID.
        """
        self.spec_id = spec_id
        self.missing = missing
        super().__init__(f"Spec '{spec_id}' references missing dependency '@{missing}'")


class DependencyResolver:
    """Resolves dependencies between spec files.

    With two-pass compilation, topological ordering is optional since:
    - Pass 1 (headers) generates all interfaces independently
    - Pass 2 (implementations) has access to all headers

    Circular @mentions are allowed and will not raise CycleError by default.
    """

    def build_graph(self, specs: list[SpecFile]) -> DependencyGraph:
        """Build a dependency graph from spec files.

        Args:
            specs: List of parsed spec files.

        Returns:
            Populated dependency graph.
        """
        graph = DependencyGraph()

        for spec in specs:
            graph.add_spec(spec)

        return graph

    def validate_dependencies(self, graph: DependencyGraph) -> list[MissingDependencyError]:
        """Check for missing dependencies.

        Args:
            graph: The dependency graph to validate.

        Returns:
            List of errors for any missing dependencies.
        """
        errors = []
        all_ids = set(graph.all_spec_ids())

        for spec_id in graph.all_spec_ids():
            for dep in graph.get_dependencies(spec_id):
                if dep not in all_ids:
                    errors.append(MissingDependencyError(spec_id, dep))

        return errors

    def topological_sort(self, graph: DependencyGraph) -> list[str]:
        """Sort specs in dependency order.

        Returns specs ordered so that dependencies come before dependents.
        Uses Kahn's algorithm.

        Args:
            graph: The dependency graph to sort.

        Returns:
            List of spec IDs in topological order.

        Raises:
            CycleError: If a dependency cycle is detected.
        """
        all_ids = graph.all_spec_ids()

        # Calculate in-degree (number of dependencies) for each spec
        # Only count dependencies that exist in the graph
        valid_ids = set(all_ids)
        in_degree: dict[str, int] = {}
        for spec_id in all_ids:
            deps = [d for d in graph.get_dependencies(spec_id) if d in valid_ids]
            in_degree[spec_id] = len(deps)

        # Start with specs that have no dependencies
        queue = [spec_id for spec_id in all_ids if in_degree[spec_id] == 0]
        result = []

        while queue:
            # Sort queue to ensure deterministic ordering
            queue.sort()
            current = queue.pop(0)
            result.append(current)

            # Reduce in-degree for all dependents
            for dependent in graph.get_dependents(current):
                if dependent in valid_ids:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)

        # If we couldn't process all specs, there's a cycle
        if len(result) != len(all_ids):
            cycle = self._find_cycle(graph)
            raise CycleError(cycle)

        return result

    def _find_cycle(self, graph: DependencyGraph) -> list[str]:
        """Find a cycle in the dependency graph using DFS.

        Args:
            graph: The dependency graph with a known cycle.

        Returns:
            List of spec IDs forming a cycle.
        """
        valid_ids = set(graph.all_spec_ids())

        # Track visited and currently in recursion stack
        visited: set[str] = set()
        rec_stack: set[str] = set()
        parent: dict[str, str | None] = {}

        def dfs(spec_id: str) -> list[str] | None:
            visited.add(spec_id)
            rec_stack.add(spec_id)

            for dep in graph.get_dependencies(spec_id):
                if dep not in valid_ids:
                    continue

                if dep not in visited:
                    parent[dep] = spec_id
                    cycle = dfs(dep)
                    if cycle:
                        return cycle
                elif dep in rec_stack:
                    # Found a cycle - reconstruct it
                    cycle = [dep]
                    current = spec_id
                    while current != dep:
                        cycle.append(current)
                        current = parent.get(current, dep)
                    cycle.append(dep)
                    cycle.reverse()
                    return cycle

            rec_stack.remove(spec_id)
            return None

        for spec_id in graph.all_spec_ids():
            if spec_id not in visited:
                parent[spec_id] = None
                cycle = dfs(spec_id)
                if cycle:
                    return cycle

        # Shouldn't reach here if there's definitely a cycle
        return ["unknown cycle"]

    def get_build_order(
        self,
        specs: list[SpecFile],
        validate: bool = True,
        allow_cycles: bool = False,
    ) -> tuple[list[SpecFile], list[MissingDependencyError]]:
        """Get specs in build order with validation.

        Convenience method that builds graph, validates, and optionally sorts.

        Args:
            specs: List of parsed spec files.
            validate: Whether to check for missing dependencies.
            allow_cycles: If True, return specs in original order when cycles exist.
                         If False, raise CycleError on cycles.

        Returns:
            Tuple of (ordered specs, validation errors).

        Raises:
            CycleError: If a dependency cycle is detected and allow_cycles=False.
        """
        graph = self.build_graph(specs)

        errors = []
        if validate:
            errors = self.validate_dependencies(graph)

        try:
            order = self.topological_sort(graph)
            ordered_specs = []
            for spec_id in order:
                spec = graph.get_spec(spec_id)
                if spec:
                    ordered_specs.append(spec)
        except CycleError:
            if allow_cycles:
                # Return specs in original order when cycles exist
                ordered_specs = list(specs)
            else:
                raise

        return ordered_specs, errors

    def get_all_specs(
        self,
        specs: list[SpecFile],
        validate: bool = True,
    ) -> tuple[list[SpecFile], list[MissingDependencyError]]:
        """Get all specs with validation but no ordering requirement.

        Use this for two-pass compilation where order doesn't matter.

        Args:
            specs: List of parsed spec files.
            validate: Whether to check for missing dependencies.

        Returns:
            Tuple of (specs in original order, validation errors).
        """
        graph = self.build_graph(specs)

        errors = []
        if validate:
            errors = self.validate_dependencies(graph)

        return list(specs), errors

    def find_cycles(self, specs: list[SpecFile]) -> list[list[str]]:
        """Find all cycles in the dependency graph.

        Useful for warnings or informational purposes.

        Args:
            specs: List of parsed spec files.

        Returns:
            List of cycles, where each cycle is a list of spec_ids.
        """
        graph = self.build_graph(specs)
        cycles = []

        try:
            self.topological_sort(graph)
        except CycleError as e:
            cycles.append(e.cycle)

        return cycles
