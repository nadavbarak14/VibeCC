"""
Registration entity module.

A registration links a student to a course, representing enrollment.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID


class RegistrationStatus(Enum):
    """Status of a registration."""

    ENROLLED = "enrolled"
    COMPLETED = "completed"
    DROPPED = "dropped"


@dataclass
class Registration:
    """
    A registration links a student to a course, representing enrollment.

    Each registration tracks when the student enrolled and their current status.
    A registration can be enrolled, completed, or dropped. Students start as
    enrolled when they register.

    Attributes:
        id: Unique identifier for the registration.
        student_id: The ID of the enrolled student.
        course_id: The ID of the course the student is registered in.
        status: Current status (enrolled, completed, or dropped).
        enrolled_at: Timestamp when the student enrolled.
        completed_at: Timestamp when the registration was marked completed (if applicable).
        dropped_at: Timestamp when the registration was dropped (if applicable).
    """

    id: UUID
    student_id: UUID
    course_id: UUID
    status: RegistrationStatus = RegistrationStatus.ENROLLED
    enrolled_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    dropped_at: Optional[datetime] = None


class RegistrationRepository:
    """Repository for registration persistence operations."""

    def create(self, student_id: UUID, course_id: UUID) -> Registration:
        """
        Create a registration for a student in a course.

        A student can only have one active (enrolled) registration per course.
        If they previously dropped the course, they can register again.
        If they previously completed the course, they cannot register again.

        Args:
            student_id: The unique identifier of the student.
            course_id: The unique identifier of the course.

        Returns:
            The newly created registration.

        Raises:
            StudentNotFoundError: If the student does not exist.
            CourseNotFoundError: If the course does not exist.
            DuplicateRegistrationError: If the student already has an active
                (enrolled) registration for this course.
            AlreadyCompletedError: If the student has already completed this course.
        """
        raise NotImplementedError()

    def find_by_student_and_course(
        self, student_id: UUID, course_id: UUID
    ) -> Optional[Registration]:
        """
        Find a registration by student and course.

        Returns the most recent registration if multiple exist (e.g., after
        dropping and re-registering).

        Args:
            student_id: The unique identifier of the student.
            course_id: The unique identifier of the course.

        Returns:
            The registration if found, None otherwise.
        """
        raise NotImplementedError()

    def find_by_student(self, student_id: UUID) -> list[Registration]:
        """
        Find all registrations for a student.

        Returns registrations of all statuses (enrolled, completed, dropped).

        Args:
            student_id: The unique identifier of the student.

        Returns:
            List of all registrations for the student.
        """
        raise NotImplementedError()

    def find_by_course(self, course_id: UUID) -> list[Registration]:
        """
        Find all registrations for a course.

        Returns registrations of all statuses (enrolled, completed, dropped).

        Args:
            course_id: The unique identifier of the course.

        Returns:
            List of all registrations for the course.
        """
        raise NotImplementedError()

    def mark_completed(self, registration_id: UUID) -> Registration:
        """
        Mark a registration as completed.

        Only enrolled registrations can be marked as completed.

        Args:
            registration_id: The unique identifier of the registration.

        Returns:
            The updated registration.

        Raises:
            RegistrationNotFoundError: If the registration does not exist.
            InvalidStatusTransitionError: If the registration is not enrolled
                (e.g., already dropped or completed).
        """
        raise NotImplementedError()

    def mark_dropped(self, registration_id: UUID) -> Registration:
        """
        Mark a registration as dropped.

        Only enrolled registrations can be dropped. Completed registrations
        cannot be dropped.

        Args:
            registration_id: The unique identifier of the registration.

        Returns:
            The updated registration.

        Raises:
            RegistrationNotFoundError: If the registration does not exist.
            InvalidStatusTransitionError: If the registration is not enrolled
                (e.g., already dropped or completed).
        """
        raise NotImplementedError()

    def has_completed_course(self, student_id: UUID, course_id: UUID) -> bool:
        """
        Check if a student has completed a specific course.

        Completed registrations count toward prerequisite requirements for
        other courses.

        Args:
            student_id: The unique identifier of the student.
            course_id: The unique identifier of the course.

        Returns:
            True if the student has a completed registration for the course,
            False otherwise (including if enrolled or dropped).
        """
        raise NotImplementedError()


class StudentNotFoundError(Exception):
    """Raised when the specified student does not exist."""

    pass


class CourseNotFoundError(Exception):
    """Raised when the specified course does not exist."""

    pass


class RegistrationNotFoundError(Exception):
    """Raised when the specified registration does not exist."""

    pass


class DuplicateRegistrationError(Exception):
    """Raised when a student already has an active registration for a course."""

    pass


class AlreadyCompletedError(Exception):
    """Raised when a student tries to register for a course they already completed."""

    pass


class InvalidStatusTransitionError(Exception):
    """Raised when an invalid status transition is attempted."""

    pass
