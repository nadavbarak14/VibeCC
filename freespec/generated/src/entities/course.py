"""
Course entity module.

A course represents a class that students can register for.
"""

from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID


@dataclass
class Course:
    """
    A course represents a class that students can register for.

    Each course has a unique code like "CS101" that identifies it, a title
    for display, and an optional description. Courses have a maximum capacity
    indicating how many students can enroll.

    A course can be open for registration or closed. Only open courses accept
    new registrations. Courses start as closed when created.

    Courses may have prerequisites, which are other courses a student must
    have completed before registering. Prerequisites form a directed acyclic
    graph; circular prerequisites are not allowed.
    """

    id: UUID
    code: str
    title: str
    capacity: int
    description: Optional[str] = None
    is_open: bool = False
    prerequisites: set[UUID] = field(default_factory=set)


class CourseRepository:
    """Repository for course persistence operations."""

    def create(
        self,
        code: str,
        title: str,
        capacity: int,
        description: Optional[str] = None,
    ) -> Course:
        """
        Create a new course with code, title, capacity, and optional description.

        Args:
            code: Unique course code (e.g., "CS101"). Case-sensitive.
            title: Display title for the course.
            capacity: Maximum number of students that can enroll. Must be >= 1.
            description: Optional course description.

        Returns:
            The newly created course.

        Raises:
            ValueError: If capacity is less than 1.
            DuplicateCodeError: If a course with this code already exists.
        """
        raise NotImplementedError()

    def find_by_code(self, code: str) -> Optional[Course]:
        """
        Find a course by its code.

        Args:
            code: The course code to search for. Case-sensitive.

        Returns:
            The course if found, None otherwise.
        """
        raise NotImplementedError()

    def find_by_id(self, course_id: UUID) -> Optional[Course]:
        """
        Find a course by its unique ID.

        Args:
            course_id: The unique identifier of the course.

        Returns:
            The course if found, None otherwise.
        """
        raise NotImplementedError()

    def update(
        self,
        course_id: UUID,
        title: Optional[str] = None,
        description: Optional[str] = None,
        capacity: Optional[int] = None,
    ) -> Course:
        """
        Update a course's title, description, or capacity.

        Args:
            course_id: The unique identifier of the course to update.
            title: New title, if provided.
            description: New description, if provided.
            capacity: New capacity, if provided. Cannot be reduced below
                      current enrollment count.

        Returns:
            The updated course.

        Raises:
            NotFoundError: If the course does not exist.
            ValueError: If capacity is less than 1 or below current enrollment.
        """
        raise NotImplementedError()

    def open_for_registration(self, course_id: UUID) -> Course:
        """
        Open a course for registration.

        Opening an already open course succeeds without error.

        Args:
            course_id: The unique identifier of the course.

        Returns:
            The updated course.

        Raises:
            NotFoundError: If the course does not exist.
        """
        raise NotImplementedError()

    def close_registration(self, course_id: UUID) -> Course:
        """
        Close a course to registration.

        Args:
            course_id: The unique identifier of the course.

        Returns:
            The updated course.

        Raises:
            NotFoundError: If the course does not exist.
        """
        raise NotImplementedError()

    def add_prerequisite(self, course_id: UUID, prerequisite_id: UUID) -> Course:
        """
        Add a prerequisite to a course.

        Adding the same prerequisite twice succeeds without creating duplicates.

        Args:
            course_id: The course to add the prerequisite to.
            prerequisite_id: The course that must be completed first.

        Returns:
            The updated course.

        Raises:
            NotFoundError: If either course does not exist.
            CycleError: If adding this prerequisite would create a cycle.
        """
        raise NotImplementedError()

    def remove_prerequisite(self, course_id: UUID, prerequisite_id: UUID) -> Course:
        """
        Remove a prerequisite from a course.

        Removing a prerequisite that doesn't exist succeeds without error.

        Args:
            course_id: The course to remove the prerequisite from.
            prerequisite_id: The prerequisite course to remove.

        Returns:
            The updated course.

        Raises:
            NotFoundError: If the course does not exist.
        """
        raise NotImplementedError()

    def list_courses(self, is_open: Optional[bool] = None) -> list[Course]:
        """
        List all courses with optional filters for open status.

        Args:
            is_open: If provided, filter to only open (True) or closed (False) courses.

        Returns:
            List of courses matching the filter criteria.
        """
        raise NotImplementedError()

    def get_enrollment_count(self, course_id: UUID) -> int:
        """
        Get the current enrollment count for a course.

        Args:
            course_id: The unique identifier of the course.

        Returns:
            The number of students currently enrolled.

        Raises:
            NotFoundError: If the course does not exist.
        """
        raise NotImplementedError()

    def has_available_seats(self, course_id: UUID) -> bool:
        """
        Check if a course has available seats.

        Args:
            course_id: The unique identifier of the course.

        Returns:
            True if enrollment count is less than capacity, False otherwise.

        Raises:
            NotFoundError: If the course does not exist.
        """
        raise NotImplementedError()


class DuplicateCodeError(Exception):
    """Raised when attempting to create a course with a code that already exists."""

    pass


class NotFoundError(Exception):
    """Raised when a requested course does not exist."""

    pass


class CycleError(Exception):
    """Raised when adding a prerequisite would create a circular dependency."""

    pass
