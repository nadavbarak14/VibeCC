"""Data models for Git Manager."""

from dataclasses import dataclass
from enum import Enum


class CIStatus(str, Enum):
    """CI check status."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass
class PR:
    """Pull request data."""

    id: int
    url: str
    number: int
