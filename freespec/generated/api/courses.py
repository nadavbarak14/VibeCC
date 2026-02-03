"""
Courses API module.

The courses API provides REST endpoints for managing course records.
Reading courses is available to all authenticated users, but modifications
require admin privileges.

Endpoints:
- GET /courses - List all courses with optional filtering
- GET /courses/:id - Get a specific course with full details
- POST /courses - Create a new course (admin only)
- PATCH /courses/:id - Update a course (admin only)
- DELETE /courses/:id - Close a course to registration (admin only)
- POST /courses/:id/prerequisites - Add a prerequisite (admin only)
- DELETE /courses/:id/prerequisites/:prereqId - Remove a prerequisite (admin only)

All endpoints accept and return JSON. Error responses include a message
field explaining what went wrong. Authentication is required for all
endpoints via Bearer token in the Authorization header.
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from entities.course import (
    Course,
    CourseRepository,
    DuplicateCodeError,
    NotFoundError,
    CycleError,
)
from services.auth import AuthService


@dataclass
class CreateCourseRequest:
    """Request body for POST /courses."""

    code: str
    title: str
    capacity: int
    description: Optional[str] = None


@dataclass
class UpdateCourseRequest:
    """Request body for PATCH /courses/:id."""

    title: Optional[str] = None
    description: Optional[str] = None
    capacity: Optional[int] = None
    is_open: Optional[bool] = None


@dataclass
class AddPrerequisiteRequest:
    """Request body for POST /courses/:id/prerequisites."""

    prerequisite_id: str


@dataclass
class CourseResponse:
    """Response body containing course data."""

    id: str
    code: str
    title: str
    capacity: int
    description: Optional[str]
    is_open: bool
    enrollment_count: int
    available_seats: int


@dataclass
class CourseDetailResponse:
    """Response body containing full course details including prerequisites."""

    id: str
    code: str
    title: str
    capacity: int
    description: Optional[str]
    is_open: bool
    enrollment_count: int
    available_seats: int
    prerequisites: list[str]


@dataclass
class CourseListResponse:
    """Response body for GET /courses."""

    courses: list[CourseResponse]


@dataclass
class ErrorResponse:
    """Response body for error responses."""

    message: str


class CoursesAPI:
    """
    REST API handlers for course management.

    Uses CourseRepository for data access and AuthService for authentication
    and authorization. All methods return appropriate HTTP status codes and
    JSON responses.
    """

    def __init__(
        self,
        course_repository: CourseRepository,
        auth_service: AuthService,
    ) -> None:
        """
        Initialize the courses API.

        Args:
            course_repository: Repository for course operations.
            auth_service: Service for authentication and authorization.
        """
        self._course_repository = course_repository
        self._auth_service = auth_service

    def list_courses(
        self,
        authorization: Optional[str],
        is_open: Optional[bool] = None,
    ) -> tuple[int, CourseListResponse | ErrorResponse]:
        """
        GET /courses - List all courses.

        Requires authentication. Supports optional filtering by open status.

        Args:
            authorization: The Authorization header value (e.g., "Bearer <token>").
            is_open: Optional filter for open (True) or closed (False) courses.

        Returns:
            Tuple of (status_code, response_body):
            - 200 with CourseListResponse containing array of courses with
              enrollment count and available seats
            - 401 with ErrorResponse if not authenticated
        """
        raise NotImplementedError()

    def get_course(
        self,
        authorization: Optional[str],
        course_id: str,
    ) -> tuple[int, CourseDetailResponse | ErrorResponse]:
        """
        GET /courses/:id - Get a specific course.

        Requires authentication. Returns full course details including
        prerequisites.

        Args:
            authorization: The Authorization header value (e.g., "Bearer <token>").
            course_id: The unique identifier of the course.

        Returns:
            Tuple of (status_code, response_body):
            - 200 with CourseDetailResponse containing full course details
            - 401 with ErrorResponse if not authenticated
            - 404 with ErrorResponse if course not found
        """
        raise NotImplementedError()

    def create_course(
        self,
        authorization: Optional[str],
        request: CreateCourseRequest,
    ) -> tuple[int, CourseDetailResponse | ErrorResponse]:
        """
        POST /courses - Create a new course.

        Requires admin privileges.

        Args:
            authorization: The Authorization header value (e.g., "Bearer <token>").
            request: Course data containing code, title, capacity, and
                optional description.

        Returns:
            Tuple of (status_code, response_body):
            - 201 with CourseDetailResponse on success
            - 400 with ErrorResponse for validation errors (e.g., invalid capacity)
            - 401 with ErrorResponse if not authenticated
            - 403 with ErrorResponse if not admin
            - 409 with ErrorResponse if code already exists
        """
        raise NotImplementedError()

    def update_course(
        self,
        authorization: Optional[str],
        course_id: str,
        request: UpdateCourseRequest,
    ) -> tuple[int, CourseDetailResponse | ErrorResponse]:
        """
        PATCH /courses/:id - Update a course.

        Requires admin privileges. Can update title, description, capacity,
        and open/closed status.

        Args:
            authorization: The Authorization header value (e.g., "Bearer <token>").
            course_id: The unique identifier of the course to update.
            request: Update data containing optional title, description,
                capacity, and is_open fields.

        Returns:
            Tuple of (status_code, response_body):
            - 200 with CourseDetailResponse on success
            - 400 with ErrorResponse if reducing capacity below enrollment
            - 401 with ErrorResponse if not authenticated
            - 403 with ErrorResponse if not admin
            - 404 with ErrorResponse if course not found
        """
        raise NotImplementedError()

    def close_course(
        self,
        authorization: Optional[str],
        course_id: str,
    ) -> tuple[int, None | ErrorResponse]:
        """
        DELETE /courses/:id - Close a course to new registrations.

        Requires admin privileges. Does not delete the course or affect
        existing enrollments.

        Args:
            authorization: The Authorization header value (e.g., "Bearer <token>").
            course_id: The unique identifier of the course to close.

        Returns:
            Tuple of (status_code, response_body):
            - 204 with None on success
            - 401 with ErrorResponse if not authenticated
            - 403 with ErrorResponse if not admin
            - 404 with ErrorResponse if course not found
        """
        raise NotImplementedError()

    def add_prerequisite(
        self,
        authorization: Optional[str],
        course_id: str,
        request: AddPrerequisiteRequest,
    ) -> tuple[int, None | ErrorResponse]:
        """
        POST /courses/:id/prerequisites - Add a prerequisite to a course.

        Requires admin privileges.

        Args:
            authorization: The Authorization header value (e.g., "Bearer <token>").
            course_id: The course to add the prerequisite to.
            request: Request containing the prerequisite course ID.

        Returns:
            Tuple of (status_code, response_body):
            - 204 with None on success
            - 400 with ErrorResponse if it would create a cycle
            - 401 with ErrorResponse if not authenticated
            - 403 with ErrorResponse if not admin
            - 404 with ErrorResponse if either course not found
        """
        raise NotImplementedError()

    def remove_prerequisite(
        self,
        authorization: Optional[str],
        course_id: str,
        prerequisite_id: str,
    ) -> tuple[int, None | ErrorResponse]:
        """
        DELETE /courses/:id/prerequisites/:prereqId - Remove a prerequisite.

        Requires admin privileges.

        Args:
            authorization: The Authorization header value (e.g., "Bearer <token>").
            course_id: The course to remove the prerequisite from.
            prerequisite_id: The prerequisite course ID to remove.

        Returns:
            Tuple of (status_code, response_body):
            - 204 with None on success
            - 401 with ErrorResponse if not authenticated
            - 403 with ErrorResponse if not admin
            - 404 with ErrorResponse if course not found
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

    def _is_admin(self, token: str) -> bool:
        """
        Check if the authenticated user has admin privileges.

        Args:
            token: The session token.

        Returns:
            True if the user is an admin, False otherwise.
        """
        raise NotImplementedError()
