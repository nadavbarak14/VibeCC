"""
Registrations API module.

Provides REST endpoints for course registration, using the enrollment service
for business logic. Handles student enrollment, dropping courses, and
registration management.
"""

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from services.enrollment import EnrollmentService, Registration


class RegistrationStatus(str, Enum):
    """Status filter for registration queries."""

    ENROLLED = "enrolled"
    COMPLETED = "completed"
    DROPPED = "dropped"


@dataclass
class CreateRegistrationRequest:
    """Request body for POST /registrations."""

    course_id: UUID


@dataclass
class UpdateRegistrationRequest:
    """Request body for PATCH /registrations/:id."""

    status: RegistrationStatus


@dataclass
class RegistrationResponse:
    """Response data for a registration."""

    id: UUID
    student_id: UUID
    course_id: UUID
    status: RegistrationStatus
    course_name: str | None = None
    course_code: str | None = None


@dataclass
class RegistrationListResponse:
    """Response data for listing registrations."""

    registrations: list[RegistrationResponse]


class RegistrationsAPI:
    """
    REST API for course registration management.

    All endpoints require authentication. Students can only access their own
    registrations unless they have admin privileges.
    """

    def __init__(self, enrollment_service: EnrollmentService) -> None:
        """
        Initialize the registrations API.

        Args:
            enrollment_service: The enrollment service for business logic.
        """
        self._enrollment_service = enrollment_service

    def create_registration(
        self,
        request: CreateRegistrationRequest,
        authenticated_user_id: UUID,
    ) -> RegistrationResponse:
        """
        POST /registrations - Enroll the authenticated student in a course.

        Args:
            request: The registration request containing the course ID.
            authenticated_user_id: The ID of the authenticated student.

        Returns:
            201: The created registration data.

        Raises:
            401: If not authenticated.
            400: If prerequisites not met or already enrolled.
            404: If course not found.
            409: If course is full or closed.
        """
        raise NotImplementedError()

    def list_registrations(
        self,
        authenticated_user_id: UUID,
        status: RegistrationStatus | None = None,
    ) -> RegistrationListResponse:
        """
        GET /registrations - List the authenticated student's registrations.

        Args:
            authenticated_user_id: The ID of the authenticated student.
            status: Optional status filter.

        Returns:
            200: Array of registration data including course information.

        Raises:
            401: If not authenticated.
        """
        raise NotImplementedError()

    def get_registration(
        self,
        registration_id: UUID,
        authenticated_user_id: UUID,
        is_admin: bool = False,
    ) -> RegistrationResponse:
        """
        GET /registrations/:id - Retrieve a specific registration.

        Students can only access their own registrations; admins can access any.

        Args:
            registration_id: The ID of the registration to retrieve.
            authenticated_user_id: The ID of the authenticated user.
            is_admin: Whether the authenticated user is an admin.

        Returns:
            200: The registration data.

        Raises:
            401: If not authenticated.
            403: If not authorized to access this registration.
            404: If registration not found.
        """
        raise NotImplementedError()

    def delete_registration(
        self,
        registration_id: UUID,
        authenticated_user_id: UUID,
        is_admin: bool = False,
    ) -> None:
        """
        DELETE /registrations/:id - Drop the student from the course.

        Students can only drop their own active enrollments; admins can drop any.

        Args:
            registration_id: The ID of the registration to drop.
            authenticated_user_id: The ID of the authenticated user.
            is_admin: Whether the authenticated user is an admin.

        Returns:
            204: On success (no content).

        Raises:
            401: If not authenticated.
            400: If already completed or dropped.
            403: If not authorized to drop this registration.
            404: If registration not found.
        """
        raise NotImplementedError()

    def update_registration(
        self,
        registration_id: UUID,
        request: UpdateRegistrationRequest,
        authenticated_user_id: UUID,
        is_admin: bool = False,
    ) -> RegistrationResponse:
        """
        PATCH /registrations/:id - Update registration status.

        Only admins can use this endpoint, typically to mark a registration
        as completed.

        Args:
            registration_id: The ID of the registration to update.
            request: The update request containing the new status.
            authenticated_user_id: The ID of the authenticated user.
            is_admin: Whether the authenticated user is an admin.

        Returns:
            200: The updated registration data.

        Raises:
            401: If not authenticated.
            400: For invalid status transition.
            403: If not admin.
            404: If registration not found.
        """
        raise NotImplementedError()

    def list_student_registrations(
        self,
        student_id: UUID,
        authenticated_user_id: UUID,
        is_admin: bool = False,
        status: RegistrationStatus | None = None,
    ) -> RegistrationListResponse:
        """
        GET /students/:id/registrations - List registrations for a specific student.

        Requires admin privileges unless accessing own registrations.

        Args:
            student_id: The ID of the student whose registrations to list.
            authenticated_user_id: The ID of the authenticated user.
            is_admin: Whether the authenticated user is an admin.
            status: Optional status filter.

        Returns:
            200: Array of registration data.

        Raises:
            401: If not authenticated.
            403: If not authorized to access this student's registrations.
            404: If student not found.
        """
        raise NotImplementedError()
