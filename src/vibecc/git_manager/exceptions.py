"""Custom exceptions for Git Manager."""


class GitManagerError(Exception):
    """Base exception for Git Manager errors."""


class BranchError(GitManagerError):
    """Error creating or managing branches."""


class PushError(GitManagerError):
    """Error pushing to remote."""


class PRError(GitManagerError):
    """Error creating or managing pull requests."""


class MergeError(GitManagerError):
    """Error merging pull request."""
