"""Tests for the enrollment service."""

import pytest
from uuid import UUID


class TestEnrollmentService:
    """Test cases for EnrollmentService."""

    @pytest.mark.skip(reason="Test skeleton - not yet implemented")
    def test_registering_for_an_open_course_with_available_seats_succeeds(self):
        """Verify that a student can successfully register for a course that is open and has seats available."""
        pass

    @pytest.mark.skip(reason="Test skeleton - not yet implemented")
    def test_registering_for_a_closed_course_fails(self):
        """Verify that attempting to register for a course that is not open raises CourseClosedError."""
        pass

    @pytest.mark.skip(reason="Test skeleton - not yet implemented")
    def test_registering_for_a_full_course_fails(self):
        """Verify that attempting to register for a course with no available seats raises CourseFullError."""
        pass

    @pytest.mark.skip(reason="Test skeleton - not yet implemented")
    def test_registering_without_meeting_prerequisites_fails(self):
        """Verify that attempting to register without completing prerequisite courses raises PrerequisitesNotMetError."""
        pass

    @pytest.mark.skip(reason="Test skeleton - not yet implemented")
    def test_registering_for_a_course_already_enrolled_in_fails(self):
        """Verify that attempting to register for a course the student is already enrolled in raises DuplicateRegistrationError."""
        pass

    @pytest.mark.skip(reason="Test skeleton - not yet implemented")
    def test_dropping_an_enrolled_course_succeeds_and_frees_a_seat(self):
        """Verify that dropping a course updates registration status to dropped and increases available seats."""
        pass

    @pytest.mark.skip(reason="Test skeleton - not yet implemented")
    def test_dropping_a_course_not_enrolled_in_fails(self):
        """Verify that attempting to drop a course the student is not enrolled in raises NotEnrolledError."""
        pass

    @pytest.mark.skip(reason="Test skeleton - not yet implemented")
    def test_dropping_a_completed_course_fails(self):
        """Verify that attempting to drop a course that has been completed raises CannotDropCompletedError."""
        pass

    @pytest.mark.skip(reason="Test skeleton - not yet implemented")
    def test_completing_a_course_marks_the_registration_as_completed(self):
        """Verify that completing a course updates the registration status to completed."""
        pass

    @pytest.mark.skip(reason="Test skeleton - not yet implemented")
    def test_completed_courses_count_toward_prerequisites(self):
        """Verify that after completing a prerequisite course, the student can register for courses requiring it."""
        pass

    @pytest.mark.skip(reason="Test skeleton - not yet implemented")
    def test_schedule_shows_only_currently_enrolled_courses(self):
        """Verify that get_schedule returns only courses with enrolled status, excluding completed and dropped."""
        pass

    @pytest.mark.skip(reason="Test skeleton - not yet implemented")
    def test_history_shows_enrolled_completed_and_dropped_registrations(self):
        """Verify that get_registration_history returns all registrations regardless of status."""
        pass

    @pytest.mark.skip(reason="Test skeleton - not yet implemented")
    def test_prerequisite_check_returns_true_when_all_prerequisites_are_completed(self):
        """Verify that check_prerequisites returns True when the student has completed all required courses."""
        pass

    @pytest.mark.skip(reason="Test skeleton - not yet implemented")
    def test_prerequisite_check_returns_false_when_any_prerequisite_is_missing(self):
        """Verify that check_prerequisites returns False when the student is missing any prerequisite course."""
        pass
