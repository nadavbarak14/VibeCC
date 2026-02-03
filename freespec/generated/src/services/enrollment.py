"""
Enrollment service module.

The enrollment service manages student course registration, coordinating between
student, course, and registration entities to handle the business logic of
enrolling in courses.
"""

from dataclasses import dataclass
from uuid import UUID

from entities.course import Course, CourseRepository
from entities.registration import (
    Registration,
    RegistrationRepository,
    RegistrationStatus,
)
from entities.student import Student, StudentRepository


class CourseClosedError(Exception):
    """Raised when attempting to register for a course that is not open."""

    pass


class CourseFullError(Exception):
    """Raised when attempting to register for a course with no available seats."""

    pass


class PrerequisitesNotMetError(Exception):
    """Raised when a student has not completed required prerequisites."""

    pass


class NotEnrolledError(Exception):
    """Raised when attempting to drop a course the student is not enrolled in."""

    pass


class CannotDropCompletedError(Exception):
    """Raised when attempting to drop a course that has been completed."""

    pass


@dataclass
class Schedule:
    """A student's current schedule of enrolled courses."""

    student: Student
    courses: list[Course]


@dataclass
class RegistrationHistory:
    """A student's full registration history."""

    student: Student
    registrations: list[Registration]


class EnrollmentService:
    """
    Service for managing student course registration.

    Coordinates between student, course, and registration repositories to
    handle enrollment business logic including prerequisite checking,
    capacity management, and status transitions.
    """

    def __init__(
        self,
        student_repository: StudentRepository,
        course_repository: CourseRepository,
        registration_repository: RegistrationRepository,
    ) -> None:
        """
        Initialize the enrollment service with required repositories.

        Args:
            student_repository: Repository for student operations.
            course_repository: Repository for course operations.
            registration_repository: Repository for registration operations.
        """
        self._student_repo = student_repository
        self._course_repo = course_repository
        self._registration_repo = registration_repository

    def register_student(self, student_id: UUID, course_id: UUID) -> Registration:
        """
        Register a student for a course.

        Checks that the course is open, has available seats, the student
        meets all prerequisites, and is not already enrolled.

        Args:
            student_id: The unique identifier of the student.
            course_id: The unique identifier of the course.

        Returns:
            The newly created registration.

        Raises:
            StudentNotFoundError: If the student does not exist.
            CourseNotFoundError: If the course does not exist.
            CourseClosedError: If the course is not open for registration.
            CourseFullError: If the course has no available seats.
            PrerequisitesNotMetError: If the student has not completed all prerequisites.
            DuplicateRegistrationError: If the student is already enrolled.
            AlreadyCompletedError: If the student has already completed this course.
        """
        raise NotImplementedError()

    def drop_student(self, student_id: UUID, course_id: UUID) -> Registration:
        """
        Drop a student from a course.

        The student must be currently enrolled (not completed or already dropped).
        Dropping frees up a seat for other students.

        Args:
            student_id: The unique identifier of the student.
            course_id: The unique identifier of the course.

        Returns:
            The updated registration with dropped status.

        Raises:
            StudentNotFoundError: If the student does not exist.
            CourseNotFoundError: If the course does not exist.
            NotEnrolledError: If the student is not currently enrolled in the course.
            CannotDropCompletedError: If the student has completed the course.
        """
        raise NotImplementedError()

    def complete_course(self, student_id: UUID, course_id: UUID) -> Registration:
        """
        Mark a student as having completed a course.

        Typically done by an administrator. The completed registration then
        counts toward prerequisites for other courses.

        Args:
            student_id: The unique identifier of the student.
            course_id: The unique identifier of the course.

        Returns:
            The updated registration with completed status.

        Raises:
            StudentNotFoundError: If the student does not exist.
            CourseNotFoundError: If the course does not exist.
            NotEnrolledError: If the student is not currently enrolled in the course.
        """
        raise NotImplementedError()

    def get_schedule(self, student_id: UUID) -> Schedule:
        """
        Get a student's current schedule.

        Returns only courses the student is currently enrolled in (not
        completed or dropped).

        Args:
            student_id: The unique identifier of the student.

        Returns:
            The student's schedule with currently enrolled courses.

        Raises:
            StudentNotFoundError: If the student does not exist.
        """
        raise NotImplementedError()

    def get_registration_history(self, student_id: UUID) -> RegistrationHistory:
        """
        Get a student's full registration history.

        Includes all registrations: enrolled, completed, and dropped.

        Args:
            student_id: The unique identifier of the student.

        Returns:
            The student's complete registration history.

        Raises:
            StudentNotFoundError: If the student does not exist.
        """
        raise NotImplementedError()

    def check_prerequisites(self, student_id: UUID, course_id: UUID) -> bool:
        """
        Check if a student meets all prerequisites for a course.

        A student meets prerequisites if they have completed all courses
        listed as prerequisites for the target course.

        Args:
            student_id: The unique identifier of the student.
            course_id: The unique identifier of the course.

        Returns:
            True if the student has completed all prerequisites, False if
            any prerequisite is missing.

        Raises:
            StudentNotFoundError: If the student does not exist.
            CourseNotFoundError: If the course does not exist.
        """
        raise NotImplementedError()
