"""
Students API module.

REST endpoints for managing student records. All endpoints require
authentication via the auth service and most require admin privileges.
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from entities.student import Student, StudentRepository
from services.auth import AuthService


class UnauthorizedError(Exception):
    """Raised when request lacks valid authentication."""

    pass


class ForbiddenError(Exception):
    """Raised when user lacks required privileges."""

    pass


class NotFoundError(Exception):
    """Raised when requested resource does not exist."""

    pass


class ValidationError(Exception):
    """Raised when request data fails validation."""

    pass


@dataclass
class PaginationParams:
    """Pagination parameters from query string."""

    page: int = 1
    limit: int = 20


@dataclass
class PaginationMeta:
    """Pagination metadata included in list responses."""

    page: int
    limit: int
    total: int
    total_pages: int


@dataclass
class StudentResponse:
    """Student data returned in API responses."""

    id: UUID
    email: str
    name: str
    is_active: bool


@dataclass
class StudentListResponse:
    """Response for GET /students endpoint."""

    students: list[StudentResponse]
    pagination: PaginationMeta


@dataclass
class UpdateStudentRequest:
    """Request body for PATCH /students/:id endpoint."""

    name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None


class StudentsAPI:
    """
    REST API handlers for student management.

    All endpoints require authentication. Most operations require admin
    privileges unless the user is accessing their own record.
    """

    def __init__(
        self,
        student_repository: StudentRepository,
        auth_service: AuthService,
    ) -> None:
        """
        Initialize the students API.

        Args:
            student_repository: Repository for student operations.
            auth_service: Service for authentication verification.
        """
        self._student_repository = student_repository
        self._auth_service = auth_service

    def list_students(
        self,
        token: str,
        is_active: Optional[bool] = None,
        pagination: Optional[PaginationParams] = None,
    ) -> StudentListResponse:
        """
        GET /students - List all students.

        Requires admin privileges. Supports optional filtering by active
        status and pagination.

        Args:
            token: Authentication token.
            is_active: Optional filter for active status.
            pagination: Optional pagination parameters (defaults to page=1, limit=20).

        Returns:
            StudentListResponse with list of students and pagination metadata.

        Raises:
            UnauthorizedError: If token is invalid (401).
            ForbiddenError: If user is not an admin (403).
        """
        raise NotImplementedError()

    def get_student(self, token: str, student_id: UUID) -> StudentResponse:
        """
        GET /students/:id - Get a specific student.

        Students can access their own record. Accessing other students
        requires admin privileges.

        Args:
            token: Authentication token.
            student_id: The ID of the student to retrieve.

        Returns:
            StudentResponse with student data.

        Raises:
            UnauthorizedError: If token is invalid (401).
            ForbiddenError: If accessing another student without admin privileges (403).
            NotFoundError: If student does not exist (404).
        """
        raise NotImplementedError()

    def update_student(
        self,
        token: str,
        student_id: UUID,
        data: UpdateStudentRequest,
    ) -> StudentResponse:
        """
        PATCH /students/:id - Update a student.

        Students can update their own name and password. Admins can update
        any field including active status.

        Args:
            token: Authentication token.
            student_id: The ID of the student to update.
            data: The fields to update.

        Returns:
            StudentResponse with updated student data.

        Raises:
            UnauthorizedError: If token is invalid (401).
            ValidationError: If password doesn't meet requirements (400).
            ForbiddenError: If not authorized to update this student or field (403).
            NotFoundError: If student does not exist (404).
        """
        raise NotImplementedError()

    def delete_student(self, token: str, student_id: UUID) -> None:
        """
        DELETE /students/:id - Deactivate a student.

        Requires admin privileges. This does not delete the student but
        marks them as inactive.

        Args:
            token: Authentication token.
            student_id: The ID of the student to deactivate.

        Raises:
            UnauthorizedError: If token is invalid (401).
            ForbiddenError: If user is not an admin (403).
            NotFoundError: If student does not exist (404).
        """
        raise NotImplementedError()
