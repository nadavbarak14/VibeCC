"""
Session entity module.

A session represents an authenticated login for a student. When a student
successfully logs in, a session is created with a unique token they use for
subsequent requests.

Sessions have an expiration time, after which they are no longer valid. The
default session duration is 24 hours. Sessions can also be explicitly
invalidated when the student logs out.

Each session token is a cryptographically random string that cannot be guessed.
Tokens are unique across all sessions.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from .student import Student


# Default session duration
DEFAULT_SESSION_DURATION = timedelta(hours=24)


@dataclass
class Session:
    """
    Represents an authenticated login session for a student.

    Attributes:
        id: Unique identifier for the session.
        student_id: The ID of the student who owns this session.
        token: Cryptographically random unique token for authentication.
        created_at: Timestamp when the session was created.
        expires_at: Timestamp when the session expires.
        invalidated_at: Timestamp when the session was explicitly invalidated, if any.
    """

    id: UUID
    student_id: UUID
    token: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(
        default_factory=lambda: datetime.utcnow() + DEFAULT_SESSION_DURATION
    )
    invalidated_at: Optional[datetime] = None


class SessionRepository:
    """Repository for session persistence operations."""

    def create(self, student_id: UUID) -> Session:
        """
        Create a new session for a student.

        Generates a cryptographically random unique token for the session.
        The session expires after the default duration (24 hours).

        Args:
            student_id: The unique identifier of the student.

        Returns:
            The newly created Session with a unique token.

        Raises:
            ValueError: If student not found.
        """
        raise NotImplementedError()

    def find_by_token(self, token: str) -> Optional[Session]:
        """
        Find a session by its token.

        Args:
            token: The session token to search for.

        Returns:
            The Session if found, None otherwise.
        """
        raise NotImplementedError()

    def is_valid(self, token: str) -> bool:
        """
        Check if a session is still valid.

        A session is valid if:
        - It exists
        - It has not been explicitly invalidated
        - Its expiration time has not passed

        Args:
            token: The session token to check.

        Returns:
            True if the session is valid, False otherwise.
        """
        raise NotImplementedError()

    def invalidate(self, token: str) -> Session:
        """
        Invalidate a session.

        Args:
            token: The session token to invalidate.

        Returns:
            The invalidated Session.

        Raises:
            ValueError: If session not found.
        """
        raise NotImplementedError()

    def invalidate_all_for_student(self, student_id: UUID) -> list[Session]:
        """
        Invalidate all sessions for a student.

        Args:
            student_id: The unique identifier of the student.

        Returns:
            List of invalidated Sessions.
        """
        raise NotImplementedError()

    def extend(self, token: str, duration: Optional[timedelta] = None) -> Session:
        """
        Extend a session's expiration time.

        Args:
            token: The session token to extend.
            duration: How long to extend the session. Defaults to DEFAULT_SESSION_DURATION.

        Returns:
            The updated Session with new expiration time.

        Raises:
            ValueError: If session not found.
            ValueError: If session is already invalid (expired or invalidated).
        """
        raise NotImplementedError()
