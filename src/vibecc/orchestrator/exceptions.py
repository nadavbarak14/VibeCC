"""Exceptions for the Orchestrator module."""


class OrchestratorError(Exception):
    """Base exception for orchestrator errors."""

    pass


class PipelineProcessingError(OrchestratorError):
    """Error during pipeline processing."""

    pass
