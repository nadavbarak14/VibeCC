"""Custom exceptions for State Store."""


class StateStoreError(Exception):
    """Base exception for State Store errors."""


class ProjectNotFoundError(StateStoreError):
    """Project with given ID does not exist."""


class ProjectExistsError(StateStoreError):
    """Project with given repo already exists."""


class ProjectHasActivePipelinesError(StateStoreError):
    """Cannot delete project with active pipelines."""


class PipelineNotFoundError(StateStoreError):
    """Pipeline with given ID does not exist."""


class PipelineExistsError(StateStoreError):
    """Pipeline for this ticket already exists."""
