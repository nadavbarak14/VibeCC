"""
Auth service module.

The auth service handles student authentication. It coordinates between
student entities for credential verification and session entities for
session management.

Login accepts an email and password. If the credentials are valid and the
student is active, a new session is created and the token is returned.
Failed login attempts should not reveal whether the email exists or the
password was wrong; the error message is the same either way.

Logout invalidates the current session. It requires a valid session token.

Registration creates a new student account. It requires email, name, and
password. After successful registration, the student can immediately log in.

The service enforces rate limiting on login attempts. After 5 failed attempts
for the same email within 15 minutes, further attempts are temporarily blocked
for that email.
"""

from dataclasses import dataclass
from typing import Optional

from entities.student import Student, StudentRepository
from entities.session import Session, SessionRepository


# Rate limiting constants
MAX_FAILED_ATTEMPTS = 5
RATE_LIMIT_WINDOW_MINUTES = 15


class AuthenticationError(Exception):
    """
    Raised when authentication fails.

    The error message is intentionally generic to avoid revealing
    whether the email exists or the password was wrong.
    """

    pass


class RateLimitError(Exception):
    """Raised when an email is rate-limited due to too many failed login attempts."""

    pass


class InvalidTokenError(Exception):
    """Raised when a session token is invalid or expired."""

    pass


class RegistrationError(Exception):
    """Raised when student registration fails."""

    pass


@dataclass
class LoginResult:
    """Result of a successful login."""

    token: str
    student: Student


class AuthService:
    """
    Service for handling student authentication.

    Coordinates between StudentRepository for credential verification
    and SessionRepository for session management.
    """

    def __init__(
        self,
        student_repository: StudentRepository,
        session_repository: SessionRepository,
    ) -> None:
        """
        Initialize the auth service.

        Args:
            student_repository: Repository for student operations.
            session_repository: Repository for session operations.
        """
        self._student_repository = student_repository
        self._session_repository = session_repository

    def login(self, email: str, password: str) -> LoginResult:
        """
        Login with email and password, returning a session token.

        If the credentials are valid and the student is active, a new
        session is created and the token is returned. Failed login
        attempts do not reveal whether the email exists or the password
        was wrong.

        A successful login resets the failure count for that email.

        Args:
            email: The student's email address.
            password: The student's password.

        Returns:
            LoginResult containing the session token and student.

        Raises:
            RateLimitError: If the email is rate-limited due to too many
                failed attempts (5 within 15 minutes).
            AuthenticationError: If credentials are invalid or student
                is inactive. Error message is intentionally generic.
        """
        raise NotImplementedError()

    def logout(self, token: str) -> None:
        """
        Logout using a session token.

        Invalidates the current session.

        Args:
            token: The session token to invalidate.

        Raises:
            InvalidTokenError: If the token is invalid or expired.
        """
        raise NotImplementedError()

    def register(self, email: str, name: str, password: str) -> Student:
        """
        Register a new student account.

        After successful registration, the student can immediately log in.

        Args:
            email: The student's email address (must be unique, case-insensitive).
            name: The student's display name.
            password: The student's password (minimum 8 characters).

        Returns:
            The newly created Student.

        Raises:
            RegistrationError: If email already exists or validation fails.
        """
        raise NotImplementedError()

    def is_rate_limited(self, email: str) -> bool:
        """
        Check if an email is rate-limited.

        An email is rate-limited after 5 failed login attempts within
        15 minutes. The rate limit resets after 15 minutes from the
        first failed attempt in the window.

        Args:
            email: The email address to check.

        Returns:
            True if the email is currently rate-limited, False otherwise.
        """
        raise NotImplementedError()
