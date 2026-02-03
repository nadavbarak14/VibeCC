"""
Student entity module.

A student is a user who can authenticate and register for courses. Each student
has an email address which serves as their unique identifier and login credential.
Email addresses are case-insensitive.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass
class Student:
    """
    Represents a student who can authenticate and register for courses.

    Attributes:
        id: Unique identifier for the student.
        email: Email address (case-insensitive), serves as login credential.
        name: Display name for the student.
        password_hash: Secure hash of the student's password (never plain text).
        is_active: Whether the student can log in and register for courses.
        created_at: Timestamp when the student was created.
        updated_at: Timestamp when the student was last updated.
    """

    id: UUID
    email: str
    name: str
    password_hash: str
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class StudentRepository:
    """Repository for student persistence operations."""

    def create(self, email: str, name: str, password: str) -> Student:
        """
        Create a new student with email, name, and password.

        Args:
            email: The student's email address (must be unique, case-insensitive).
            name: The student's display name.
            password: The student's password (minimum 8 characters).

        Returns:
            The newly created Student.

        Raises:
            ValueError: If email is invalid format or already exists (case-insensitive).
            ValueError: If password is shorter than 8 characters.
        """
        raise NotImplementedError()

    def find_by_email(self, email: str) -> Optional[Student]:
        """
        Find a student by their email address (case-insensitive).

        Args:
            email: The email address to search for.

        Returns:
            The Student if found, None otherwise.
        """
        raise NotImplementedError()

    def find_by_id(self, student_id: UUID) -> Optional[Student]:
        """
        Find a student by their unique ID.

        Args:
            student_id: The unique identifier of the student.

        Returns:
            The Student if found, None otherwise.
        """
        raise NotImplementedError()

    def update_name(self, student_id: UUID, name: str) -> Student:
        """
        Update a student's name.

        Args:
            student_id: The unique identifier of the student.
            name: The new display name.

        Returns:
            The updated Student.

        Raises:
            ValueError: If student not found.
        """
        raise NotImplementedError()

    def update_password(self, student_id: UUID, password: str) -> Student:
        """
        Update a student's password.

        Args:
            student_id: The unique identifier of the student.
            password: The new password (minimum 8 characters).

        Returns:
            The updated Student.

        Raises:
            ValueError: If student not found.
            ValueError: If password is shorter than 8 characters.
        """
        raise NotImplementedError()

    def deactivate(self, student_id: UUID) -> Student:
        """
        Deactivate a student. Inactive students cannot log in or register for courses.
        Deactivating an already inactive student succeeds without error.

        Args:
            student_id: The unique identifier of the student.

        Returns:
            The updated Student.

        Raises:
            ValueError: If student not found.
        """
        raise NotImplementedError()

    def reactivate(self, student_id: UUID) -> Student:
        """
        Reactivate a student, allowing them to log in and register for courses.

        Args:
            student_id: The unique identifier of the student.

        Returns:
            The updated Student.

        Raises:
            ValueError: If student not found.
        """
        raise NotImplementedError()

    def list_all(self, is_active: Optional[bool] = None) -> list[Student]:
        """
        List all students with optional filters for active status.

        Args:
            is_active: If provided, filter by active status. None returns all students.

        Returns:
            List of students matching the filter criteria.
        """
        raise NotImplementedError()

    def verify_password(self, student_id: UUID, password: str) -> bool:
        """
        Verify a password matches for a given student.

        Args:
            student_id: The unique identifier of the student.
            password: The password to verify.

        Returns:
            True if password matches, False otherwise.

        Raises:
            ValueError: If student not found.
            ValueError: If student is inactive.
        """
        raise NotImplementedError()
