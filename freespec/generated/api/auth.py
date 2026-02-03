"""
Auth API module.

The auth API provides REST endpoints for student authentication, using
the AuthService for business logic.

Endpoints:
- POST /auth/register - Create a new student account
- POST /auth/login - Authenticate and get a session token
- POST /auth/logout - Invalidate the current session
- GET /auth/me - Get current student information

All endpoints accept and return JSON. Error responses include a message
field explaining what went wrong.
"""

from dataclasses import dataclass
from typing import Optional

from services.auth import (
    AuthService,
    AuthenticationError,
    RateLimitError,
    InvalidTokenError,
    RegistrationError,
)
from entities.student import Student


@dataclass
class RegisterRequest:
    """Request body for POST /auth/register."""

    email: str
    name: str
    password: str


@dataclass
class LoginRequest:
    """Request body for POST /auth/login."""

    email: str
    password: str


@dataclass
class LoginResponse:
    """Response body for successful POST /auth/login."""

    token: str


@dataclass
class StudentResponse:
    """Response body containing student data."""

    id: str
    email: str
    name: str


@dataclass
class ErrorResponse:
    """Response body for error responses."""

    message: str


class AuthAPI:
    """
    REST API handlers for student authentication.

    Uses AuthService for business logic. All methods return appropriate
    HTTP status codes and JSON responses.
    """

    def __init__(self, auth_service: AuthService) -> None:
        """
        Initialize the auth API.

        Args:
            auth_service: The authentication service for business logic.
        """
        self._auth_service = auth_service

    def register(self, request: RegisterRequest) -> tuple[int, StudentResponse | ErrorResponse]:
        """
        POST /auth/register - Create a new student account.

        Args:
            request: Registration data containing email, name, and password.

        Returns:
            Tuple of (status_code, response_body):
            - 201 with StudentResponse on success
            - 400 with ErrorResponse for validation errors (missing fields,
              invalid email format, short password)
            - 409 with ErrorResponse if email is already taken
        """
        raise NotImplementedError()

    def login(self, request: LoginRequest) -> tuple[int, LoginResponse | ErrorResponse]:
        """
        POST /auth/login - Authenticate a student.

        Args:
            request: Login data containing email and password.

        Returns:
            Tuple of (status_code, response_body):
            - 200 with LoginResponse containing session token on success
            - 401 with ErrorResponse for invalid credentials
            - 429 with ErrorResponse if rate-limited
        """
        raise NotImplementedError()

    def logout(self, authorization: Optional[str]) -> tuple[int, None | ErrorResponse]:
        """
        POST /auth/logout - Invalidate the current session.

        Requires authentication via Bearer token in Authorization header.

        Args:
            authorization: The Authorization header value (e.g., "Bearer <token>").

        Returns:
            Tuple of (status_code, response_body):
            - 204 with None on success
            - 401 with ErrorResponse if not authenticated or token invalid
        """
        raise NotImplementedError()

    def get_me(self, authorization: Optional[str]) -> tuple[int, StudentResponse | ErrorResponse]:
        """
        GET /auth/me - Get current student information.

        Requires authentication via Bearer token in Authorization header.

        Args:
            authorization: The Authorization header value (e.g., "Bearer <token>").

        Returns:
            Tuple of (status_code, response_body):
            - 200 with StudentResponse on success
            - 401 with ErrorResponse if not authenticated or token expired
        """
        raise NotImplementedError()

    def _extract_token(self, authorization: Optional[str]) -> Optional[str]:
        """
        Extract the Bearer token from an Authorization header.

        Args:
            authorization: The Authorization header value.

        Returns:
            The token string, or None if not present or invalid format.
        """
        raise NotImplementedError()
